"""修正行数（180 → 179）并给 README §8.70 补一条自测说明。"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MAIN = ROOT / "5_Reference" / "08_工作流" / "工作流_主计划.md"
README = ROOT / "1_Code" / "DDM_Core" / "README.md"

OLD_MAIN = "`check_run_pipeline.py`（180 行，**7/7**）"
NEW_MAIN = "`check_run_pipeline.py`（179 行，**7/7**）"

OLD_RE = ("- 口径：quick（`n_draws=12`）**只验证机制**；要出结论必须 `--profile formal`"
          "（`n_draws=50` ≥ 25 才有 Pareto-k 诊断）")
NEW_RE = ("- 自测：`1_Code/Experiment/exp_Check/check_run_pipeline.py`（179 行，**7/7**）—— "
          "P1/P2 钉死「判词 + 骨架横幅」（P2 的假 JSON `n_flipped` = 2/16，而 `k_max` = 0.000、"
          "`p_loo` = 10 都好看），P3 钉死「不拟合就不判」，P4/P5 钉死健康组放行（退出码 0）"
          "与病组拦截（退出码 1）。\n" + OLD_RE)


def main() -> None:
    t = MAIN.read_text(encoding="utf-8")
    n = t.count(OLD_MAIN)
    MAIN.write_text(t.replace(OLD_MAIN, NEW_MAIN), encoding="utf-8", newline="\n")
    print(f"主计划：行数改正 {n} 处")

    r = README.read_text(encoding="utf-8")
    if "check_run_pipeline.py`（179 行" in r:
        print("README：已含自测说明，跳过")
    else:
        m = r.count(OLD_RE)
        README.write_text(r.replace(OLD_RE, NEW_RE), encoding="utf-8", newline="\n")
        print(f"README：插入自测说明 {m} 处")


if __name__ == "__main__":
    main()
