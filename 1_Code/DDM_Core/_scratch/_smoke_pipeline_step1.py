"""冒烟：只跑 run_pipeline 的第 1 步（入库判定），确认与 intake 口径一致、不崩。"""
import sys
from pathlib import Path

ROOT = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
sys.path.insert(0, str(ROOT / "1_Code" / "Experiment"))

import run_pipeline as RP  # noqa: E402

out = ROOT / "1_Code" / "DDM_Core" / "_scratch" / "_repro" / "pipeline_step1"
out.mkdir(parents=True, exist_ok=True)
ok, rows, p = RP.step_intake(ROOT / "2_Data" / "Real_Data" / "New_Design", out)
n = {k: sum(1 for r in rows if r["verdict"] == k) for k in ("KEEP", "REVIEW", "EXCLUDE")}
print(f"ok={ok} 场次={len(rows)} KEEP={n['KEEP']} REVIEW={n['REVIEW']} EXCLUDE={n['EXCLUDE']}")
print(f"报告：{p}（{len(p.read_text(encoding='utf-8').splitlines())} 行）")
head = p.read_text(encoding="utf-8").splitlines()
print("\n".join(head[:6]))
print("...")
print("\n".join(head[-2:]))
