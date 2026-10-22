"""文件结构三分：图 → 3_Figures，数据 → 2_Data（只在 Generate_Data / Real_Data 下）。

规则（用户 2026-10-24）：
  1_Code 只放代码；所有图进 3_Figures；过程数据进 2_Data。
本脚本只做「搬家」，不改内容；用 git mv 保证历史可追。
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

ROOT = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
GEN = ROOT / "2_Data" / "Generate_Data"
REAL = ROOT / "2_Data" / "Real_Data"
FIGS = ROOT / "3_Figures"
PAPER = ROOT / "5_Reference" / "03_论文写作" / "figures_sim"
SYNTH = GEN / "_synth_datasets"


def tracked(rel: str) -> bool:
    r = subprocess.run(["git", "ls-files", "--error-unmatch", rel],
                       cwd=ROOT, capture_output=True, text=True)
    return r.returncode == 0


def move(src: Path, dst: Path) -> None:
    if not src.exists():
        print(f"  [skip] 源不存在 {src.relative_to(ROOT)}")
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    rel_src = str(src.relative_to(ROOT)).replace("\\", "/")
    rel_dst = str(dst.relative_to(ROOT)).replace("\\", "/")
    if tracked(rel_src):
        r = subprocess.run(["git", "mv", rel_src, rel_dst], cwd=ROOT,
                           capture_output=True, text=True)
        if r.returncode != 0:
            print(f"  [git mv 失败] {rel_src} → {rel_dst}: {r.stderr.strip()[:120]}")
            return
    else:
        shutil.move(str(src), str(dst))
    print(f"  {rel_src}  →  {rel_dst}")


def main() -> int:
    print("[1] 每模型的图 → 3_Figures/<model>/")
    for m in ("M-T1", "M-T2", "M-T3"):
        fdir = GEN / m / "figures"
        if fdir.is_dir():
            for p in sorted(fdir.glob("*")):
                move(p, FIGS / m / p.name)
            try:
                fdir.rmdir()
                print(f"  [rmdir] {fdir.relative_to(ROOT)}")
            except OSError:
                pass

    print("[2] 跨模型对照图 → 3_Figures/_compare/")
    cdir = GEN / "_compare"
    if cdir.is_dir():
        for p in sorted(cdir.glob("*.png")):
            move(p, FIGS / "_compare" / p.name)

    print("[3] 论文级模拟图 → 3_Figures/figures_sim/")
    if PAPER.is_dir():
        for p in sorted(PAPER.glob("*.png")):
            move(p, FIGS / "figures_sim" / p.name)

    print("[4] 合成数据集 → 2_Data/Generate_Data/_synth_datasets/")
    for name in ("_SYNTHETIC_DEMO_v1", "_SYNTHETIC_NOTEBOOK", "_SYNTHETIC_SCAN"):
        src = REAL / name
        if src.is_dir():
            move(src, SYNTH / name)

    print("[5] 目录统计")
    for d in (FIGS, GEN, REAL):
        n = len(list(d.rglob("*"))) if d.exists() else 0
        print(f"  {d.relative_to(ROOT)}：{n} 项")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
