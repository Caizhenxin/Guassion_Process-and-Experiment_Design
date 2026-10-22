"""扫「多少人/组才让 LOO 闸门转绿」——D100 留下的问题（README §9 第 83 项）。

对每个 N 做三件事：① 生成 N 名**合成**被试（指定组，`_make_ddm_pilot.py`）；
② 用 quick 配置跑 `stage8_run.py` 单组拟合；③ 用 `stage8_health.assess_group` 取判词。
结果写 `scan_min_n.json` + `scan_min_n.md`（追加式：重跑同一个 N 会覆盖该 N 的行）。

**这仍是合成数据**：它回答的是「组层回归需要多少人才可辨识」，
不是「真实被试需要多少人」，两者的关系由 `Stage6_Pilot方案.md` §5.3 的锚点决定。

用法：

    python -X utf8 1_Code/Experiment/scan_min_n.py --n-list 4 8 12
    python -X utf8 1_Code/Experiment/scan_min_n.py --n-list 4 --reuse   # 已有 JSON 就不重拟合
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "1_Code" / "DDM_Core"))

import stage8_health as H8                                        # noqa: E402

GEN = ROOT / "1_Code" / "DDM_Core" / "_scratch" / "_make_ddm_pilot.py"
S8 = ROOT / "1_Code" / "DDM_Core" / "stage8_run.py"
QUICK = {"n_em": 3, "n_draws": 12, "n_x": 21, "n_ppc": 1}


def gen_data(out: Path, n: int, group: int, seed: int, n_rep: int) -> Path:
    """生成 N 名合成被试（只写 txt，没有 CSV 快照——`intake` 收 txt-only）。"""
    out.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, "-X", "utf8", str(GEN), str(out),
           "--n-subjects", str(n), "--group", str(group), "--n-rep", str(n_rep),
           "--n-practice", str(max(4, {1: 0, 2: 8, 3: 32, 4: 120}[group])),
           "--rho", "0.8", "--seed", str(seed + 10 * group), "--anticipation", "0.03"]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", cwd=str(ROOT))
    if proc.returncode != 0:
        raise RuntimeError(f"生成失败（exit {proc.returncode}）：{proc.stderr[-400:]}")
    return out


def run_stage8(data: Path, out: Path, group: int, seed: int) -> tuple[int, float]:
    out.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, "-X", "utf8", str(S8), "--data", str(data),
           "--group", str(group), "--n-em", str(QUICK["n_em"]),
           "--n-draws", str(QUICK["n_draws"]), "--n-x", str(QUICK["n_x"]),
           "--n-ppc", str(QUICK["n_ppc"]), "--hyper-method", "analytic",
           "--loo-level", "trial", "--seed", str(seed), "--out", str(out)]
    t0 = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", cwd=str(ROOT))
    dt = time.time() - t0
    js = out / f"stage8_group_{group}.json"
    if not js.exists():
        raise RuntimeError(f"拟合没有产出 JSON（exit {proc.returncode}）：{proc.stderr[-400:]}")
    return proc.returncode, dt


def one(n: int, group: int, root: Path, reuse: bool) -> dict:
    tag = f"n{n}"
    rdir = root / tag
    data_dir = rdir / "data"
    s8_dir = rdir / "stage8"
    js = s8_dir / f"stage8_group_{group}.json"
    t0 = time.time()
    if not (reuse and js.exists()):
        gen_data(data_dir, n, group, seed=200 + n, n_rep=12)
        rc, dt8 = run_stage8(data_dir, s8_dir, group, seed=300 + n)
    else:
        rc, dt8 = 0, 0.0
    h = H8.assess_group(js)
    m = (h.get("modes") or {}).get("M-T1") or {}
    return {"n": n, "group": group, "status": h.get("status"),
            "n_flipped": m.get("n_flipped"), "n_eig": m.get("n_eig"),
            "p_loo_ratio": m.get("p_loo_ratio"), "k_max": m.get("k_max"),
            "max_abs_theta": m.get("max_abs_theta"),
            "elpd": m.get("elpd"), "reasons": m.get("reasons") or [],
            "seconds": round(dt8, 1), "wall": round(time.time() - t0, 1),
            "json": str(js.relative_to(ROOT))}


def write_reports(root: Path, rows: list[dict]) -> None:
    p = root / "scan_min_n.json"
    old: list[dict] = []
    if p.exists():
        try:
            old = json.loads(p.read_text(encoding="utf-8"))
        except ValueError:
            old = []
    merged = {r["n"]: r for r in old}
    merged.update({r["n"]: r for r in rows})
    out = [merged[k] for k in sorted(merged)]
    p.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")

    L = ["# 多少人/组才让 LOO 闸门转绿（D100 后续）", "",
         "> **数据是合成的**（`_make_ddm_pilot.py`，组 1，`--anticipation 0.03`）。",
         "> 配置：quick（`n_em`=3、`n_draws`=12、`n_x`=21、PPC=1）、`--hyper-method analytic`、"
         "`--loo-level trial`。判词来自 `stage8_health.assess_group`（D73/D74/D75）。", "",
         "| N（人/组） | 判词 | `n_flipped` | `p_loo`÷`n_obs` | `k_max` | `max_abs_theta` | "
         "拟合耗时 | 主因 |", "|---|---|---|---|---|---|---|---|"]
    for r in out:
        nf = r["n_flipped"]
        nf = nf if isinstance(nf, str) else f"{nf}/{r['n_eig']}"
        L.append(f"| {r['n']} | {r['status']} | {nf} | "
                 f"{r['p_loo_ratio']:.3f} | {r['k_max']:.3f} | {r['max_abs_theta']:.1f} | "
                 f"{r['seconds'] / 60:.1f} min | "
                 f"{(r['reasons'] or ['—'])[0][:60]} |")
    L += ["", "读法：**N 增大但判词仍 BAD** ⇒ 不是样本量问题，要查判据；"
          "**N 增大后转 OK 的那个 N** 就是「可辨识下限」的粗估。", ""]
    (root / "scan_min_n.md").write_text("\n".join(L), encoding="utf-8", newline="\n")


def main() -> int:
    ap = argparse.ArgumentParser(description="扫最小可辨识组层样本量（合成数据）")
    ap.add_argument("--n-list", type=int, nargs="+", default=[4, 8, 12])
    ap.add_argument("--group", type=int, default=1)
    ap.add_argument("--root", default=str(ROOT / "2_Data" / "Generate_Data" / "_synth_datasets" / "_SYNTHETIC_SCAN"))
    ap.add_argument("--reuse", action="store_true", help="已有 stage8_group_*.json 的 N 跳过拟合")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    for n in args.n_list:
        print(f"[scan] N = {n} 人/组（组 {args.group}）…", flush=True)
        r = one(n, args.group, root, args.reuse)
        rows.append(r)
        print(f"[scan] N = {n} ⇒ {r['status']}（{r['n_flipped']}/{r['n_eig']} flipped、"
              f"耗时 {r['seconds'] / 60:.1f} min）", flush=True)
        write_reports(root, rows)
    print(f"[scan] 报告：{root / 'scan_min_n.md'}")
    return 0 if all(r["status"] != H8.BAD for r in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
