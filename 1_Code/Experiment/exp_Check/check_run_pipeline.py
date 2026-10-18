# -*- coding: utf-8 -*-
"""`run_pipeline.py` 自测：五条用例，把「LOO 闸门必须自动跑」变成机器判据。

为什么必须自测：D99 暴露的缺陷不是「判据错」，而是「判据没接到报告生成路径上」——
`stage8_health.py` 里早有 D74（超参数 Hessian 正定）与 `p_loo ∈ [0, n_obs]`，
骨架却只印 `k_max`，于是四组「不可引用」的 Δelpd 被排成一张看着正常的模型比较表。
**只接住自己刚加的那条判据**，是这类工具的通病；本文件把「闸门是否真的接了」钉死。

用例：

| 编号 | 场景 | 期望 |
|---|---|---|
| P1 | 健康组 JSON（`n_flipped`=0、`p_loo` 远小于 `n_obs`） | `assess_health` 判 `OK`；骨架**无**「不可引用」横幅 |
| P2 | 病组 JSON（`n_flipped`=2/16，但 `p_loo` 与 `k_max` 都「好看」） | 判 `BAD`；骨架有横幅 + `⛔ 不可引用` + `n_flipped` 列 |
| P3 | `--skip-stage8` | 退出码 0；报告里**没有**「3.5 LOO 健康」行（不拟合就不该判） |
| P4 | `--reuse-stage8` + 健康 JSON | 退出码 0；报告「3.5 LOO 健康」= ✅、可引用 1/1 |
| P5 | `--reuse-stage8` + 病 JSON | 退出码 **1**；报告 3.5 = ❌；`stderr` 点名 3.5 |
| P6 | 组层 2 人 vs 12 人 | 2 人/组 ⇒ 骨架点名「组层样本量不足」；12 人/组 ⇒ 无提示、判词 `OK`（D100） |

P2 是关键：`k_max = 0.000`、`p_loo` = 10（÷`n_obs` = 0.017）都像健康读数，
只有 D74 的 Hessian 正定性会判死它 —— 这正是 D52/D99 说过的「单看任一指标都会误判可报」。

用法：`python -X utf8 1_Code/Experiment/exp_Check/check_run_pipeline.py`
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
EXP = HERE.parent
ROOT = EXP.parent.parent
sys.path.insert(0, str(EXP))
sys.path.insert(0, str(ROOT / "1_Code" / "DDM_Core"))

import run_pipeline as RP                                       # noqa: E402

SYNTH = ROOT / "2_Data" / "Real_Data" / "_SYNTHETIC_DEMO_v1"

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    print(f"{'✅' if ok else '❌'} [{name}] {detail}")


def fake_group_json(gid: int, *, bad: bool, n_s: int = 2) -> dict:
    """造一份 schema 与 `stage8_run.py` 一致的组缓存（数值虚构）。"""
    n_obs = 576
    k = 8

    def loo(offset: float) -> dict:
        elpd_i = [-(0.7 + 0.35 * ((i + gid) % 9)) + offset for i in range(n_obs)]
        return {"elpd_loo": sum(elpd_i), "se": 12.5, "p_loo": 10.0, "n_obs": n_obs,
                "n_draws": 50, "elpd_i": elpd_i, "pareto_k": [0.2] * n_obs,
                "k_max": 0.000, "k_median": 0.2, "n_k_gt_bad": 0,
                "n_k_gt_unusable": 0, "n_failed": 0, "level": "trial",
                "k_diag_ok": True}

    eigval = [0.4, 0.5, 0.9, 1.2, 1.4, 2.0, 2.4, 2.9,
              3.1, 3.4, 4.0, 4.4, 5.0, 6.2, 8.0, 9.5]
    if bad:                              # 两个负特征值 ⇒ D74 判死
        eigval[0], eigval[1] = -0.42, -1.31
    hyper = {"theta": [0.0] * k, "mu": [0.0] * k,
             "log_sigma": [0.0] * k, "sigma": [1.0] * k,
             "cov": [[1e-4 if i == j else 0.0 for j in range(k)] for i in range(k)],
             "eigval": eigval, "theta0": [0.0] * k,
             "n_flipped": 2 if bad else 0, "max_abs_theta": 2.1, "n_evals": 640}

    def fit(offset: float) -> dict:
        modes = [[0.1 * (s + 1)] * k for s in range(n_s)]
        for row in modes:                       # 让两组的数据略有差别
            row[0] += offset
        return {"mu": [0.0] * k, "log_sigma": [0.0] * k, "sigma": [1.0] * k,
                "modes": modes,
                "covs": [[[1e-4 if i == j else 0.0 for j in range(k)] for i in range(k)]
                         for _ in range(n_s)],
                "log_marginal": -500.0, "log_joint_total": -480.0,
                "n_flipped": 0, "n_em_used": 12, "n_fallback": 0,
                "history": [], "k": k, "n_subjects": n_s}

    return {"tag": str(gid), "lines": [],
            "config": {"n_em": 12, "n_draws": 50, "n_x": 81, "n_ppc": 10,
                       "seed": 1, "hyper_method": "analytic", "bruteforce": False,
                       "loo_level": "trial", "source": "self-test"},
            "results": {"M-T1": {"fit": fit(0.0), "hyper": hyper, "loo": loo(0.0),
                                 "loo_stats": {}, "n_subjects": n_s, "k": k,
                                 "hyper_method": "analytic", "loo_level": "trial",
                                 "seconds": 1.0, "rho_free": True},
                        "M-T3": {"fit": fit(0.35), "hyper": hyper, "loo": loo(-0.12),
                                 "loo_stats": {}, "n_subjects": n_s, "k": k,
                                 "hyper_method": "analytic", "loo_level": "trial",
                                 "seconds": 1.0, "rho_free": False}},
            "n_subjects": n_s, "k": k, "hyper_method": "analytic",
            "loo_level": "trial", "seconds": 1.0, "rho_free": True}


def write_out(root: Path, *, bad: bool, with_data: Path | None, n_s: int = 2) -> Path:
    """造一个 `--out` 目录：`stage8/stage8_group_1.json` 就位。"""
    s8 = root / "stage8"
    s8.mkdir(parents=True, exist_ok=True)
    (s8 / "stage8_group_1.json").write_text(
        json.dumps(fake_group_json(1, bad=bad, n_s=n_s), ensure_ascii=False),
        encoding="utf-8", newline="\n")
    return root


def run_cli(argv: list[str]) -> tuple[int, str, str]:
    proc = subprocess.run([sys.executable, "-X", "utf8", str(EXP / "run_pipeline.py"), *argv],
                          capture_output=True, text=True, encoding="utf-8", errors="replace",
                          cwd=str(ROOT))
    return proc.returncode, proc.stdout, proc.stderr


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="pipe_test_"))
    try:
        # ---- P1 / P2：判词与骨架 ----
        ok_out = write_out(tmp / "ok", bad=False, with_data=None)
        bad_out = write_out(tmp / "bad", bad=True, with_data=None)

        h_ok = RP.assess_health(ok_out / "stage8")
        h_bad = RP.assess_health(bad_out / "stage8")
        s_ok = (h_ok.get(1) or {}).get("status")
        s_bad = (h_bad.get(1) or {}).get("status")
        check("P1 健康组判词", s_ok == "OK", f"status = {s_ok}")

        groups_ok = RP.load_groups(ok_out / "stage8")
        groups_bad = RP.load_groups(bad_out / "stage8")
        sk_ok = RP.write_results_skeleton(Path("data"), ok_out, [], groups_ok, None, h_ok)
        sk_bad = RP.write_results_skeleton(Path("data"), bad_out, [], groups_bad, None, h_bad)
        t_ok = sk_ok.read_text(encoding="utf-8")
        t_bad = sk_bad.read_text(encoding="utf-8")
        check("P1 骨架无横幅", "本段数值不可引用" not in t_ok and "✅ 可引用" in t_ok,
              "健康组不应出横幅")

        detail_p2 = f"status = {s_bad}"
        check("P2 病组判词", s_bad == "BAD", detail_p2)
        ok_p2 = ("本段数值不可引用" in t_bad and "⛔ 不可引用" in t_bad
                 and "n_flipped" in t_bad and "2/16" in t_bad)
        check("P2 骨架横幅与原因列", ok_p2,
              "横幅 + ⛔ + n_flipped 列 + 「2/16」原因（k_max/p_loo 都好看仍判死）")

        # ---- P6：组层样本量提示（D100）----
        big_out = write_out(tmp / "big", bad=False, with_data=None, n_s=12)
        h_big = RP.assess_health(big_out / "stage8")
        g_big = RP.load_groups(big_out / "stage8")
        t_big = RP.write_results_skeleton(Path("data"), big_out, [], g_big, None,
                                          h_big).read_text(encoding="utf-8")
        check("P6 小样本出提示", "组层样本量不足" in t_ok and "2 人/组 < 10" in t_ok,
              "n=2 人/组 ⇒ 骨架必须点名「组层样本量」而不是让人以为是配置问题")
        check("P6 大样本不出提示", "组层样本量不足" not in t_big
              and (h_big.get(1) or {}).get("status") == "OK",
              f"n=12 人/组 ⇒ 无提示、status = {(h_big.get(1) or {}).get('status')}")

        # ---- P3：--skip-stage8 不应有 3.5 步 ----
        rc3, out3, _ = run_cli([str(SYNTH), "--skip-stage8", "--out", str(tmp / "skip")])
        rep3 = (tmp / "skip" / "pipeline_report.md")
        t3 = rep3.read_text(encoding="utf-8") if rep3.exists() else ""
        check("P3 skip 无健康步", rc3 == 0 and "3.5 LOO 健康" not in t3,
              f"exit={rc3}、报告含 3.5 = {'3.5 LOO 健康' in t3}")

        # ---- P4 / P5：--reuse-stage8 的闸门与退出码 ----
        rc4, out4, err4 = run_cli([str(SYNTH), "--reuse-stage8", "--out", str(ok_out)])
        t4 = (ok_out / "pipeline_report.md").read_text(encoding="utf-8")
        row4 = [x for x in t4.split("\n") if "3.5 LOO 健康" in x]
        check("P4 健康组放行", rc4 == 0 and row4 and "✅" in row4[0],
              f"exit={rc4}、行 = {row4[0][:60] if row4 else '无'}")

        rc5, out5, err5 = run_cli([str(SYNTH), "--reuse-stage8", "--out", str(bad_out)])
        t5 = (bad_out / "pipeline_report.md").read_text(encoding="utf-8")
        row5 = [x for x in t5.split("\n") if "3.5 LOO 健康" in x]
        check("P5 病组拦截", rc5 == 1 and row5 and "❌" in row5[0] and "3.5" in err5,
              f"exit={rc5}、行 = {row5[0][:60] if row5 else '无'}、stderr 点名 = {'3.5' in err5}")
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)

    n_pass = sum(1 for _, ok, _ in results if ok)
    print(f"\n== 共 {len(results)} 项：通过 {n_pass} / 未通过 {len(results) - n_pass} ==")
    return 0 if n_pass == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
