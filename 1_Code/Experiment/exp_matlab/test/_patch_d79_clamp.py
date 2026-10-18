# -*- coding: utf-8 -*-
"""_patch_d79_clamp.py —— 给练习段与正式段各加一条「反应时必须为正」的兜底（D79 之二）

背景：抢按在注视期被记进 premature_press，但同一按如果没有从队列清掉（或驱动时间戳
早于刺激 onset），会被 kqFirstPressUntil 当成反应，得到负 RT，并让 stimulus_dur_actual
与"按键后下一帧"对不上。纯靠 KbQueueFlush 只堵一种情况，这里再加一道数值兜底。
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]  # test -> exp_matlab -> Experiment -> 1_Code -> 仓库根
F = ROOT / "1_Code" / "Experiment" / "exp_matlab" / "Exp_Design_Formal.m"

CLAMP = """        % ★ v4.5（D79）：反应时必须严格为正。驱动时间戳早于刺激 onset 的按键仍属抢按，
        %   不能算本试次反应（否则 RT 为负，stimulus_dur_actual 也会对不上）。
        if ~isnan(responseTime) && responseTime <= 0
            prematurePress = 1;
            response = NaN;
            responseTime = NaN;
        end
"""

text = F.read_text(encoding="utf-8")
n = 0
for wname in ("W", "Wtrial"):
    anchor = (
        "        % ★ v4 修正 #3：判定 timeout / responded_by_deadline（截止之后的按键不算反应）\n"
        f"        respondedByDeadline = double(~isnan(responseTime) && responseTime <= {wname});"
    )
    if anchor not in text:
        print(f"[缺锚点] {wname}")
        continue
    if "D79）：反应时必须严格为正" in text and f"respondedByDeadline = double(~isnan(responseTime) && responseTime <= {wname});" not in text:
        print(f"[已打补丁] {wname}")
        continue
    new = (
        "        % ★ v4 修正 #3：判定 timeout / responded_by_deadline（截止之后的按键不算反应）\n"
        + CLAMP
        + f"        respondedByDeadline = double(~isnan(responseTime) && responseTime <= {wname});"
    )
    text = text.replace(anchor, new, 1)
    n += 1
    print(f"[patched] {wname}")

F.write_text(text, encoding="utf-8", newline="\n")
print("patched", n)
