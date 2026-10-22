"""搬迁后统一改文档与 docstring 里的旧路径。"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")

SUBS = [
    ("2_Data/Real_Data/_SYNTHETIC_", "2_Data/Generate_Data/_synth_datasets/_SYNTHETIC_"),
    ("2_Data/Generate_Data/_compare/fig8_spe_locus.png", "3_Figures/_compare/fig8_spe_locus.png"),
    ("2_Data/Generate_Data/_compare/fig7_model_compare.png", "3_Figures/_compare/fig7_model_compare.png"),
    ("2_Data/Generate_Data/M-T1/figures/", "3_Figures/M-T1/"),
    ("2_Data/Generate_Data/M-T2/figures/", "3_Figures/M-T2/"),
    ("2_Data/Generate_Data/M-T3/figures/", "3_Figures/M-T3/"),
    ("5_Reference/03_论文写作/figures_sim/fig_sim_", "3_Figures/figures_sim/fig_sim_"),
    ("`<model>/figures/fig1..fig6.png`", "`3_Figures/<model>/fig1..fig6.png`"),
    ("`figures/fig1..fig6.png`", "`3_Figures/<model>/fig1..fig6.png`"),
]

TARGETS = [
    ROOT / "5_Reference" / "08_工作流" / "工作流_主计划.md",
    ROOT / "5_Reference" / "08_工作流" / "Stage9_设计空间优化与论文整合方案.md",
    ROOT / "5_Reference" / "08_工作流" / "全流程一键跑通_使用说明.md",
    ROOT / "1_Code" / "DDM_Core" / "README.md",
    ROOT / "2_Data" / "Generate_Data" / "README.md",
    ROOT / "1_Code" / "Experiment" / "gen_model_data.py",
    ROOT / "1_Code" / "Experiment" / "gen_viz.py",
    ROOT / "1_Code" / "Experiment" / "spe_locus.py",
    ROOT / "1_Code" / "Experiment" / "make_sim_figures.py",
    ROOT / "1_Code" / "Experiment" / "scan_min_n.py",
]


def main() -> int:
    total = 0
    for p in TARGETS:
        if not p.exists():
            print(f"[skip] 缺文件 {p.name}")
            continue
        s = p.read_text(encoding="utf-8")
        n = 0
        for a, b in SUBS:
            c = s.count(a)
            if c:
                s = s.replace(a, b)
                n += c
        if n:
            p.write_text(s, encoding="utf-8", newline="\n")
            print(f"[ok] {p.relative_to(ROOT)}：改 {n} 处")
            total += n
    print(f"合计 {total} 处")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
