# -*- coding: utf-8 -*-
"""复现 check_run_pipeline 的 P4/P5 失败：直接看 rc / stderr / 报告是否存在。"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
EXP = ROOT / "1_Code" / "Experiment"
sys.path.insert(0, str(EXP))
sys.path.insert(0, str(ROOT / "1_Code" / "DDM_Core"))
sys.path.insert(0, str(EXP / "exp_Check"))

import check_run_pipeline as C  # noqa: E402

tmp = Path(tempfile.mkdtemp(prefix="repro_p4_"))
print("tmp =", tmp)
ok_out = C.write_out(tmp / "ok", bad=False, with_data=None)
print("ok_out =", ok_out, "exists =", ok_out.exists())
print("files:", sorted(p.name for p in ok_out.iterdir()))

argv = [sys.executable, "-X", "utf8", str(EXP / "run_pipeline.py"),
        str(C.SYNTH), "--reuse-stage8", "--out", str(ok_out)]
proc = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8",
                      errors="replace", cwd=str(ROOT))
print("rc =", proc.returncode)
print("--- stdout tail ---")
print("\n".join(proc.stdout.splitlines()[-15:]))
print("--- stderr tail ---")
print("\n".join(proc.stderr.splitlines()[-25:]))
rep = ok_out / "pipeline_report.md"
print("report exists =", rep.exists())
if rep.exists():
    print("report lines =", len(rep.read_text(encoding="utf-8").splitlines()))
