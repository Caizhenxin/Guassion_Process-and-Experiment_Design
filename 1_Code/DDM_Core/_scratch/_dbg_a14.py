# -*- coding: utf-8 -*-
from pathlib import Path

p = Path("1_Code/Experiment/exp_matlab/Exp_Design_Formal.m")
prog = p.read_text(encoding="utf-8")
code = "\n".join(l for l in prog.splitlines() if not l.strip().startswith("%"))
print("v4.8 header:", "★★ v4.8 本次修正" in prog)
print("progDir line:", "progDir = fileparts(mfilename('fullpath'));" in code)
print("fullfile count:", code.count("fullfile(progDir, f)"))
print("assert:", "assert(isempty(missingMask)" in code)
bare = "selfMaskImages = {" + "'self10-1.png'"
print("bare:", bare in code)
print("progDir idx:", code.find("progDir = fileparts"), "screenXpixels idx:", code.find("screenXpixels"))
