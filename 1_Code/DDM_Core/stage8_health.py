# -*- coding: utf-8 -*-
"""stage8_health.py — Stage 8 **组级健康判据**的一键报告（D74 / D75 / D76）。

为什么需要它
------------
Stage 8 的正式运行是「4 组 × ~40 人」的批处理，`stage8_run.py` 每组落一个
`stage8_group_<组>.json`。但「这组能不能引用 ELPD / ΔELPD」这个问题，此前只有
**报告正文里的判词行**能回答，且判据散在三处：

* D73：**被试层**（`loo_level="participant"`）的 `p_loo` 量的是 profile 边际在
  超参数抽取间的**离散度**，不是参数个数 ⇒ 该口径**结构性不可估**；
* D74：换到**试次层**也不是充分条件 —— 超参数 Hessian 非正定（`n_flipped > 0`）时
  抽样里混着 `|θ|` 达数百的荒诞尾部值，**两层都会越界**；
* D75：Hessian 的正定性**不是样本量的函数**（N=2…6 扫描非单调、N=4 加试次也不消除）
  ⇒ **不得预先承诺「40 人/组 LOO 就可用」**，只能逐组事后判。且 `λ_min` 的符号不说明
  程度（失败拟合的 `λ_min` 可只到 −0.005），必须与「抽样跑了多远」（`max_abs_theta`）并列。

这个脚本把上述判据**收敛成一个可批量执行的检查器**，输出 Markdown 表 + JSON，
让正式数据到手后「哪组能引用、哪组不能」不再靠人肉翻报告。

判据（三条硬闸 + 两条软告警）
-----------------------------
============  =====================================================  ========
编号          条件                                                    结论
============  =====================================================  ========
H1            `n_flipped > 0`（Hessian 非正定）                        不可引用
H2            `loo_level == "participant"`（被试层口径）                不可引用
H3            `p_loo ∉ [0, n_obs]` / `k_max` 非有限 / 失败率 > 0.2     不可引用
H4            `n_draws < 10`（`loo.psis_one` 不做 GPD 平滑）            不可引用
W1            `max_abs_theta ≥ 20`（D75：正定 ≤ 7.3 vs 非正定 ≥ 33.6）  可疑
W2            `0.7 < k_max ≤ 1.0`（`loo.K_BAD` / `K_UNUSABLE`）         降级提示
============  =====================================================  ========

另：同一份报告里**两种 LOO 口径混用** ⇒ 模型比较不成立，整组标「不可比较」（D73）。

用法
----
    # 扫一个输出目录（找 stage8_group_*.json）或多个目录/文件
    python -X utf8 -u 1_Code\\DDM_Core\\stage8_health.py _scratch\\stage8_n4_576

    # 正式数据：每组一个目录，一次全扫；任一判定不可引用就以非零退出（CI 用）
    python -X utf8 -u 1_Code\\DDM_Core\\stage8_health.py _stage8_out\\*  --strict

    # 同时落一份机器可读的汇总
    python -X utf8 -u 1_Code\\DDM_Core\\stage8_health.py _stage8_out --json health.json
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

# ---- 判据阈值（全部在文档里有出处，不要就地改数字） ----
K_BAD = 0.7           # loo.K_BAD：该观测的 LOO 估计不可靠
K_UNUSABLE = 1.0      # loo.K_UNUSABLE：重要性权重方差无穷
FAIL_RATIO_MAX = 0.2  # PSIS 失败列超过 20% ⇒ 该矩阵不可用
MIN_DRAWS_PSIS = 10   # loo.psis_one：S < 10 不做 GPD 平滑
MAXABS_WARN = 20.0    # D75 实测：正定 ≤ 7.3、非正定 ≥ 33.6 ⇒ 20 是保守分界
PLOO_LO = 0.0         # p_loo < 0 ⇒ 留一比拟合内还准（不可能）
# p_loo 的上界是 n_obs（惩罚不能超过全部信息量），逐组算，不做常数

OK, WARN, BAD = "OK", "WARN", "BAD"
_FLAG = {OK: "✅ **可引用**", WARN: "⚠️ **可疑（可引用，但需人工看一眼）**",
         BAD: "⛔ **不可引用**"}


def _get(d, *keys, default=None):
    """沿键链取值，任一层缺失即返回 default（旧 JSON 可能没有新字段）。"""
    cur = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def assess_mode(mode: str, r: dict) -> dict:
    """对单个 (组, 模型) 块给出数值摘要与最终判词。"""
    lk = r.get("loo") or {}
    hy = r.get("hyper") or {}
    n_obs = int(lk.get("n_obs", 0) or 0)
    ploo = _as_float(lk.get("p_loo"))
    k_max = _as_float(lk.get("k_max"))
    n_failed = int(lk.get("n_failed", 0) or 0)
    n_draws = int(lk.get("n_draws", 0) or 0)
    level = str(r.get("loo_level") or lk.get("level") or "participant")
    eig = hy.get("eigval")
    n_eig = len(eig) if eig is not None else 0
    n_flip = int(hy.get("n_flipped", 0) or 0)
    eig_min = _as_float(min(eig)) if n_eig else None
    eig_max = _as_float(max(eig)) if n_eig else None
    max_abs = _as_float(hy.get("max_abs_theta"))

    reasons: list[str] = []
    warns: list[str] = []

    # H1：Hessian 非正定（D74）——最高优先，因为它同时污染 p_loo
    if hy and n_flip > 0:
        reasons.append(f"超参数 Hessian 非正定（`n_flipped` = {n_flip}/{n_eig}，D74）")
    # H2：被试层口径（D73）
    if level != "trial":
        reasons.append(f"LOO 口径为 `{level}`（被试层 `p_loo` 不可估，D73）")
    # H3：数值健康
    if not (ploo is not None and math.isfinite(ploo)):
        reasons.append("`p_loo` 非有限")
    elif not (PLOO_LO <= ploo <= n_obs):
        reasons.append(f"`p_loo` = {ploo:.3g} 落在健康区间 [0, {n_obs}] 之外")
    if not (k_max is not None and math.isfinite(k_max)):
        reasons.append("`k_max` 非有限（PSIS 未能给出 Pareto k）")
    if n_obs and n_failed / n_obs > FAIL_RATIO_MAX:
        reasons.append(f"PSIS 失败 {n_failed}/{n_obs} = {n_failed / n_obs:.1%} > "
                       f"{FAIL_RATIO_MAX:.0%}")
    # H4：抽取数不足（loo 内部不做平滑，p_loo 会以「失败」形式出现）
    if 0 < n_draws < MIN_DRAWS_PSIS:
        reasons.append(f"`n_draws` = {n_draws} < {MIN_DRAWS_PSIS}（`loo.psis_one` 不做平滑）")
    # W1：抽样跑了多远（D75）
    if not reasons and max_abs is None and n_eig > 0 and n_flip == 0:
        warns.append("缓存里没有 `max_abs_theta`（D75 之后才落盘）⇒ 按「未落盘」处理，"
                     "无法判断抽样跑了多远")
    if not reasons and max_abs is not None and max_abs >= MAXABS_WARN:
        warns.append(f"本次抽样 `max|θ|` = {max_abs:.3g} ≥ {MAXABS_WARN:g}"
                     f"（D75：正定实测 ≤ 7.3）")
    # W2：k 挡位
    if not reasons and k_max is not None and math.isfinite(k_max) \
            and K_BAD < k_max <= K_UNUSABLE:
        warns.append(f"`k_max` = {k_max:.3f} ∈ ({K_BAD}, {K_UNUSABLE}] ⇒ 降级为提示性")

    status = BAD if reasons else (WARN if warns else OK)
    return {
        "mode": mode, "status": status, "level": level, "n_obs": n_obs,
        "n_subjects": int(r.get("n_subjects", 0) or 0),
        "p_loo": ploo, "p_loo_ratio": (ploo / n_obs) if (ploo is not None and n_obs) else None,
        "k_max": k_max, "n_failed": n_failed, "n_draws": n_draws,
        "n_flipped": n_flip, "n_eig": n_eig,
        "eig_min": eig_min, "eig_max": eig_max, "max_abs_theta": max_abs,
        "elpd": _as_float(lk.get("elpd_loo")), "se": _as_float(lk.get("se")),
        "reasons": reasons, "warns": warns,
    }


def _as_float(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f


def assess_group(path: Path) -> dict:
    """读一个 `stage8_group_<组>.json`，给出整组判词。"""
    obj = json.loads(path.read_text(encoding="utf-8"))
    for key in ("tag", "results", "config"):
        if key not in obj:
            raise ValueError(f"{path.name} 缺字段 `{key}`（不是 stage8_run.py 落的组缓存？）")
    modes = {name: assess_mode(name, r) for name, r in obj["results"].items()}
    levels = {m["level"] for m in modes.values()}
    config = obj.get("config") or {}
    return {
        "file": path.name, "dir": path.parent.name, "tag": str(obj["tag"]),
        "n_subjects": next((m["n_subjects"] for m in modes.values() if m["n_subjects"]), 0),
        "levels": sorted(levels),
        "comparable": len(levels) == 1,
        "config": {k: config.get(k) for k in
                   ("n_em", "n_draws", "n_x", "loo_level", "hyper_method", "source")},
        "modes": modes,
        "status": BAD if (any(m["status"] == BAD for m in modes.values())
                          or len(levels) != 1) else
                  (WARN if any(m["status"] == WARN for m in modes.values()) else OK),
    }


def collect(paths: list[str]) -> list[Path]:
    """把目录展开成 `stage8_group_*.json`；直接给的 json 原样保留。"""
    out: list[Path] = []
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            out.extend(sorted(p.glob("stage8_group_*.json")))
        elif p.is_file() and p.suffix == ".json":
            out.append(p)
        elif p.is_file():
            raise ValueError(f"{p} 不是 json")
        else:
            raise FileNotFoundError(f"找不到 {p}")
    if not out:
        raise FileNotFoundError("没有找到任何 stage8_group_*.json")
    return out


def render(rows: list[dict]) -> list[str]:
    """渲染成 Markdown（表 + 逐组明细）。"""
    lines = ["# Stage 8 组级健康报告（D73/D74/D75）", ""]
    n_bad = sum(1 for r in rows if r["status"] == BAD)
    lines.append(f"共 **{len(rows)}** 组；✅ 可引用 **{len(rows) - n_bad}**、"
                 f"⛔ 不可引用 **{n_bad}**。判据见 D74（Hessian 正定）、D75（正定性非样本量函数）。")
    lines += ["", "| 组 | 来源目录 | 人 | 口径 | `p_loo`÷`n_obs` | `k_max` | `n_flipped` | `max\\|θ\\|` | 判定 |",
              "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        p0 = next(iter(r["modes"].values()))          # 概览行取第一个模型
        ratio = p0["p_loo_ratio"]
        ratio_txt = "—" if ratio is None else f"{ratio:.3g}"
        lines.append(
            f"| {r['tag']} | `{r['dir']}` | {r['n_subjects']} | {('、'.join(r['levels']))} | {ratio_txt} | "
            f"{_fmt(p0['k_max'])} | {p0['n_flipped']}/{p0['n_eig']} | "
            f"{_fmt(p0['max_abs_theta'])} | {_FLAG[r['status']]} |")
    for r in rows:
        lines += ["", f"## 组 {r['tag']}（{r['n_subjects']} 人，`{r['dir']}/{r['file']}`）", ""]
        if not r["comparable"]:
            lines.append(f"> ⛔ **同伴本组内 LOO 口径不一致**（{('、'.join(r['levels']))}）"
                         f"⇒ 模型比较不成立（D73）")
        lines.append(f"> 配置：`n_em`={r['config']['n_em']}、`n_draws`={r['config']['n_draws']}、"
                     f"`n_x`={r['config']['n_x']}、`loo_level`={r['config']['loo_level']}、"
                     f"`hyper_method`={r['config']['hyper_method']}")
        for m in r["modes"].values():
            lines.append(
                f"* **{m['mode']}**：ELPD **{_fmt(m['elpd'])} ± {_fmt(m['se'])}**、"
                f"`p_loo` {_fmt(m['p_loo'])}（`n_obs` = {m['n_obs']}）、"
                f"`k_max` {_fmt(m['k_max'])}、失败 {m['n_failed']}/{m['n_obs']}、"
                f"Hessian {m['n_flipped']}/{m['n_eig']}"
                f"（eig [{_fmt(m['eig_min'])}, {_fmt(m['eig_max'])}]）、"
                f"`max|θ|` {_fmt(m['max_abs_theta'])} ⇒ {_FLAG[m['status']]}")
            for s in m["reasons"]:
                lines.append(f"  - ⛔ {s}")
            for s in m["warns"]:
                lines.append(f"  - ⚠️ {s}")
    return lines


def _fmt(v, nd: int = 3) -> str:
    if v is None:
        return "—"
    if isinstance(v, float) and not math.isfinite(v):
        return "nan"
    return f"{v:.{nd}g}" if abs(v) >= 1e4 or (v and abs(v) < 1e-3) else f"{v:.{nd}f}"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Stage 8 组级健康判据（D74/D75）：逐组判「LOO 能不能引用」")
    ap.add_argument("paths", nargs="+", help="输出目录或 stage8_group_*.json")
    ap.add_argument("--json", dest="json_out", default=None, help="汇总落盘路径")
    ap.add_argument("--strict", action="store_true",
                    help="任一组的判定为「不可引用」⇒ 退出码 1（正式数据/CI 用）")
    args = ap.parse_args(argv)

    files = collect(args.paths)
    rows = [assess_group(p) for p in files]
    for line in render(rows):
        print(line)
    if args.json_out:
        out = Path(args.json_out)
        out.write_text(json.dumps({"n_groups": len(rows), "groups": rows},
                                  ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8", newline="\n")
        print(f"\n已落盘：{out}")
    n_bad = sum(1 for r in rows if r["status"] == BAD)
    if args.strict and n_bad:
        print(f"\n[strict] {n_bad} 组判定「不可引用」", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
