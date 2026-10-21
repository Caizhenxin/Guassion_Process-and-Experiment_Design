# -*- coding: utf-8 -*-
"""截图 preview HTML 的若干段落（用 Edge headless），便于肉眼检查版式。"""
import subprocess
import sys
from pathlib import Path

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
ROOT = Path(r"D:/GitHub_programe/GitHub/Guassion-Process-Experiment-Design")
HTML = ROOT / "5_Reference/06_进展与汇报/项目全景预览_v1.html"
SHOT = ROOT / "1_Code/DDM_Core/_scratch"
PROF = SHOT / "_edgeprof"


def shot(name, size, anchor=None):
    uri = HTML.as_uri()
    if anchor:
        uri += "#" + anchor
    out = SHOT / name
    cmd = [EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars",
           f"--user-data-dir={PROF}", f"--window-size={size}",
           f"--screenshot={out}", uri]
    subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    print(name, out.stat().st_size if out.exists() else "FAILED")


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("all", "mid"):
        shot("_shot_mid.png", "1200,2400", "s4-3-计算模型")
    if which in ("all", "figs"):
        shot("_shot_figs.png", "1200,2400", "s111-4-4-三条必须写进论文的结论")
