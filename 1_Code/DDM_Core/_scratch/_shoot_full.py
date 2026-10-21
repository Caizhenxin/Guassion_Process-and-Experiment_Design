# -*- coding: utf-8 -*-
"""整页截图（高窗口）+ Pillow 裁成 3 段，便于检查版式。"""
import subprocess
from pathlib import Path

from PIL import Image

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
ROOT = Path(r"D:/GitHub_programe/GitHub/Guassion-Process-Experiment-Design")
HTML = ROOT / "5_Reference/06_进展与汇报/项目全景预览_v1.html"
SHOT = ROOT / "1_Code/DDM_Core/_scratch"
PROF = SHOT / "_edgeprof"
full = SHOT / "_preview_full.png"

cmd = [EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars",
       f"--user-data-dir={PROF}", "--window-size=1200,9000",
       f"--screenshot={full}", HTML.as_uri()]
subprocess.run(cmd, capture_output=True, text=True, timeout=180)
im = Image.open(full)
print("full size", im.size)
W, H = im.size
step = 2200
for i in range(0, H, step):
    box = (0, i, W, min(i + step, H))
    out = SHOT / f"_seg_{i//step:02d}.png"
    im.crop(box).save(out)
    print(out.name, out.stat().st_size)
