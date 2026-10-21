# -*- coding: utf-8 -*-
"""看 stage8_group_*.json 的键结构，判断模型章能填哪些占位符。"""
import json
from pathlib import Path

ROOT = Path(r"D:/GitHub_programe/GitHub/Guassion-Process-Experiment-Design")
cands = sorted((ROOT / "2_Data/Real_Data").glob("*/_stage8_out/stage8_group_*.json"))
cands += sorted((ROOT / "2_Data/Real_Data").glob("*/_pipeline/stage8/stage8_group_*.json"))
print("files:", len(cands))
if not cands:
    raise SystemExit(0)
f = cands[0]
print("sample:", f)
d = json.loads(f.read_text(encoding="utf-8"))
print("top keys:", list(d))
res = d.get("results") or {}
print("results keys:", list(res))
mt1 = res.get("M-T1") or {}
print("M-T1 keys:", list(mt1))
fit = mt1.get("fit") or {}
print("fit keys:", list(fit))
for k, v in fit.items():
    if isinstance(v, list):
        print(f"  fit[{k}] list len={len(v)} head={v[:3]}")
    elif isinstance(v, dict):
        print(f"  fit[{k}] dict keys={list(v)[:8]}")
    else:
        print(f"  fit[{k}] = {v}")
loo = mt1.get("loo") or {}
print("loo keys:", list(loo), "| elpd_loo", loo.get("elpd_loo"), "se", loo.get("se_elpd"))
print("bic present:", "bic" in mt1, mt1.get("bic"))
print("subjects:", len(d.get("subjects") or d.get("sub") or []))
