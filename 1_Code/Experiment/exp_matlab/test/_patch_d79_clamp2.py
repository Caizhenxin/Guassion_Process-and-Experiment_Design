# -*- coding: utf-8 -*-
"""_patch_d79_clamp2.py —— 给正式段（缩进多一级）补同一条「反应时必须为正」兜底。"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
F = ROOT / "1_Code" / "Experiment" / "exp_matlab" / "Exp_Design_Formal.m"

lines = F.read_text(encoding="utf-8").split("\n")
out, inserted = [], 0
for i, line in enumerate(lines):
    if "respondedByDeadline = double(" in line:
        prev = "\n".join(lines[max(0, i - 4):i])
        if "D79）：反应时必须严格为正" in prev:
            out.append(line)
            print(f"[跳过 已打] L{i+1}")
            continue
        indent = line[: len(line) - len(line.lstrip())]
        block = [
            f"{indent}% ★ v4.5（D79）：反应时必须严格为正。驱动时间戳早于刺激 onset 的按键仍属抢按，",
            f"{indent}%   不能算本试次反应（否则 RT 为负，stimulus_dur_actual 也会对不上）。",
            f"{indent}if ~isnan(responseTime) && responseTime <= 0",
            f"{indent}    prematurePress = 1;",
            f"{indent}    response = NaN;",
            f"{indent}    responseTime = NaN;",
            f"{indent}end",
        ]
        out.extend(block)
        inserted += 1
        print(f"[插桩] L{i+1} 缩进 {len(indent)}")
    out.append(line)

F.write_text("\n".join(out), encoding="utf-8", newline="\n")
print("inserted", inserted)
