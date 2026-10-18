# -*- coding: utf-8 -*-
"""check_stage8_health.py — `stage8_health.py` 的自测（D74/D75 判据收敛件）。

判据分三层：`assess_mode`（单块）、`assess_group`/`render`（成组与渲染）、
`main`（端到端 + `--strict` + `--json`）。全部用**手写的小 dict**，
不依赖任何一次真实拟合，因此可以在秒级跑完。

用法：
    python -X utf8 -u 1_Code\\DDM_Core\\_scratch\\check_stage8_health.py
"""

from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import stage8_health as H  # noqa: E402

PASS = 0
FAIL = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  ✅ {name}" + (f"：{detail}" if detail else ""))
    else:
        FAIL += 1
        print(f"  ❌ {name}" + (f"：{detail}" if detail else ""))


def mk(n_obs=100, p_loo=5.0, k_max=0.30, n_failed=0, n_draws=30,
       level="trial", n_eig=16, n_flip=0, eigmin=0.02, eigmax=3.0,
       max_abs=7.0, n_subjects=4, elpd=-123.0, se=4.0, hyper=None, loo=None):
    """造一个 (组, 模型) 块；字段名与 `stage8_run.fit_group` 落盘的一致。"""
    if hyper is None:
        hyper = {"eigval": [eigmin] + [0.5] * (n_eig - 2) + [eigmax][: 1 if n_eig > 1 else 0],
                 "n_flipped": n_flip}
        if max_abs is not None:
            hyper["max_abs_theta"] = max_abs
    if loo is None:
        loo = {"n_obs": n_obs, "p_loo": p_loo, "k_max": k_max, "n_failed": n_failed,
               "n_draws": n_draws, "elpd_loo": elpd, "se": se, "level": level}
    return {"loo": loo, "hyper": hyper, "loo_level": level, "n_subjects": n_subjects,
            "seconds": 10.0}


def main() -> int:
    print("== A. assess_mode：三条硬闸 + 两条软告警 ==")
    r = H.assess_mode("M-T1", mk())
    check("A1 健康块 ⇒ OK", r["status"] == H.OK, f"status={r['status']} warns={r['warns']}")

    r = H.assess_mode("M-T1", mk(n_flip=2))
    check("A2 Hessian 非正定 ⇒ BAD 且理由含「非正定」（D74）",
          r["status"] == H.BAD and any("非正定" in s for s in r["reasons"]),
          f"reasons={r['reasons']}")

    r = H.assess_mode("M-T1", mk(level="participant", n_obs=4, p_loo=2.0))
    check("A3 被试层口径 ⇒ BAD 且理由含「被试层」（D73）",
          r["status"] == H.BAD and any("被试层" in s for s in r["reasons"]),
          f"reasons={r['reasons']}")
    check("A3b 被试层即便数值都在健康区间也必须 BAD（口径是硬闸）",
          r["p_loo"] == 2.0 and r["k_max"] == 0.30 and r["status"] == H.BAD)

    r = H.assess_mode("M-T1", mk(p_loo=-1.0))
    check("A4 p_loo < 0 ⇒ BAD", r["status"] == H.BAD,
          f"reasons={r['reasons']}")

    r = H.assess_mode("M-T1", mk(n_obs=93, p_loo=800.0))
    check("A5 p_loo > n_obs ⇒ BAD（唯一上界是 n_obs，不是常数）",
          r["status"] == H.BAD and any("之外" in s for s in r["reasons"]),
          f"reasons={r['reasons']}")

    r = H.assess_mode("M-T1", mk(k_max=float("nan")))
    check("A6 k_max 非有限 ⇒ BAD 且理由写「非有限」", r["status"] == H.BAD
          and any("非有限" in s for s in r["reasons"]), f"reasons={r['reasons']}")

    r = H.assess_mode("M-T1", mk(n_failed=30, n_obs=93))
    check("A7 PSIS 失败率 32% > 20% ⇒ BAD", r["status"] == H.BAD,
          f"reasons={r['reasons']}")

    r = H.assess_mode("M-T1", mk(n_draws=6))
    check("A8 n_draws=6 < 10 ⇒ BAD（loo 内部不做 GPD 平滑）",
          r["status"] == H.BAD and any("n_draws" in s for s in r["reasons"]),
          f"reasons={r['reasons']}")

    r = H.assess_mode("M-T1", mk(max_abs=60.0))
    check("A9 max|θ| 60 ≥ 20 ⇒ WARN（D75：正定实测 ≤ 7.3）",
          r["status"] == H.WARN and any("max|θ|" in s for s in r["warns"]),
          f"warns={r['warns']}")

    r = H.assess_mode("M-T1", mk(max_abs=None))
    check("A10 缺 max_abs_theta（D75 前的旧缓存）⇒ WARN 且写明「未落盘」，不得静默",
          r["status"] == H.WARN and any("未落盘" in s for s in r["warns"]),
          f"warns={r['warns']}")

    r = H.assess_mode("M-T1", mk(k_max=0.85))
    check("A11 0.7 < k_max ≤ 1.0 ⇒ WARN 且理由含「降级」",
          r["status"] == H.WARN and any("降级" in s for s in r["warns"]),
          f"warns={r['warns']}")

    r = H.assess_mode("M-T1", {"loo_level": "trial"})
    check("A12 缺 loo/hyper ⇒ BAD（不得把「读不到」当健康）", r["status"] == H.BAD,
          f"reasons={r['reasons']}")

    print("\n== B. assess_group / render ==")
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        good = {"tag": "1", "results": {"M-T1": mk(), "M-T3": mk()},
                "config": {"n_em": 4, "n_draws": 30, "n_x": 25, "loo_level": "trial",
                           "hyper_method": "analytic", "source": "data:x"}}
        mixed = {"tag": "2", "results": {"M-T1": mk(), "M-T3": mk(level="participant",
                                                                n_obs=40)},
                 "config": {"n_em": 4, "n_draws": 30, "n_x": 25, "loo_level": "trial",
                            "hyper_method": "analytic", "source": "data:y"}}
        bad = {"tag": "3", "results": {"M-T1": mk(n_flip=2)}, "config": {}}
        for name, obj in [("stage8_group_1.json", good), ("stage8_group_2.json", mixed),
                          ("stage8_group_3.json", bad)]:
            (d / name).write_text(json.dumps(obj), encoding="utf-8")

        g1 = H.assess_group(d / "stage8_group_1.json")
        check("B1 两块都 trial 且健康 ⇒ 组 status OK、comparable True",
              g1["status"] == H.OK and g1["comparable"],
              f"status={g1['status']} levels={g1['levels']}")
        check("B1b 组记录带来源目录（同 tag 不同目录时概览表才不会撞名）",
              g1["dir"] == d.name, f"dir={g1['dir']}")

        g2 = H.assess_group(d / "stage8_group_2.json")
        check("B2 同组混用两种口径 ⇒ comparable False 且组 status BAD（D73）",
              g2["comparable"] is False and g2["status"] == H.BAD,
              f"levels={g2['levels']} status={g2['status']}")

        g3 = H.assess_group(d / "stage8_group_3.json")
        check("B3 缺 config 也能读（config 只用于展示，不参与判据）",
              g3["status"] == H.BAD and g3["config"]["n_em"] is None)

        lines = H.render([g1, g2, g3])
        txt = "\n".join(lines)
        check("B4 概览表头含「来源目录」（避免同 tag 两组分不清）", "来源目录" in txt)
        check("B5 渲染含两组「不可引用」与一组「可引用」",
              txt.count("⛔ **不可引用**") >= 2 and "✅ **可引用**" in txt,
              f"BAD={txt.count('⛔ **不可引用**')}")
        check("B6 混合口径在明细里显式写出「模型比较不成立」", "模型比较不成立" in txt)

        print("\n== C. main：端到端 + --strict + --json ==")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = H.main([str(d)])
        out = buf.getvalue()
        check("C1 main 扫目录 ⇒ 找到 3 组并渲染", rc == 0 and "共 **3** 组" in out,
              f"rc={rc}")
        check("C1b 默认（非 strict）即便有不可引用也返回 0", rc == 0)

        with contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()):
            rc_strict = H.main([str(d), "--strict"])
        check("C2 --strict 且有不可引用 ⇒ 返回 1", rc_strict == 1, f"rc={rc_strict}")

        js = d / "health.json"
        with contextlib.redirect_stdout(io.StringIO()):
            H.main([str(d), "--json", str(js)])
        obj = json.loads(js.read_text(encoding="utf-8"))
        check("C3 --json 落盘：n_groups 与逐组 status 都在",
              obj["n_groups"] == 3
              and [g["status"] for g in obj["groups"]] == [H.OK, H.BAD, H.BAD],
              f"statuses={[g['status'] for g in obj['groups']]}")
        check("C4 --json 里每块都留了 p_loo/k_max/n_flipped 原始值（可复核）",
              all("p_loo" in m and "k_max" in m and "n_flipped" in m
                  for g in obj["groups"] for m in g["modes"].values()))

        print("\n== D. 输入错误必须响亮 ==")
        try:
            H.assess_group(d / "nope.json")
            check("D1 不存在的文件 ⇒ 抛异常", False)
        except FileNotFoundError:
            check("D1 不存在的文件 ⇒ FileNotFoundError", True)
        (d / "bad.json").write_text('{"tag": "9"}', encoding="utf-8")
        try:
            H.assess_group(d / "bad.json")
            check("D2 缺 results/config 的 json ⇒ 抛 ValueError（不当空组通过）", False)
        except ValueError as e:
            check("D2 缺字段 ⇒ ValueError", "缺字段" in str(e), str(e))

    print("\n" + "=" * 60)
    print(f"共 {PASS + FAIL} 项，未通过 {FAIL} 项。")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
