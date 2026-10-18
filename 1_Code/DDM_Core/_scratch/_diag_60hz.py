# -*- coding: utf-8 -*-
"""临时诊断：检查 60 Hz 实机数据的 5 个「刺激提前结束」行。"""
import csv
import statistics

p = r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\1_Code\Experiment\exp_matlab\EXP_data_group1_1.csv"
rows = list(csv.DictReader(open(p, encoding="utf-8-sig")))
print("行数", len(rows))
zero = [i + 2 for i, r in enumerate(rows) if float(r["stimulus_frames"]) == 0]
print("stimulus_frames == 0 的行号:", zero, "（共 %d 行）" % len(zero))
flip = statistics.median(
    float(r["stimulus_dur_actual"]) / float(r["stimulus_frames"])
    for r in rows if float(r["stimulus_frames"]) > 0
)
print("反推 FlipIntv = %.4f ms (%.3f Hz)" % (flip * 1000, 1 / flip))
print("T 档:", sorted({round(float(r["T"]), 3) for r in rows}))
print("W 档:", sorted({round(float(r["W"]), 6) for r in rows}))
print("帧数:", sorted({int(r["stimulus_frames"]) for r in rows}))
print("block:", sorted({r["block"] for r in rows}), "stage:", sorted({r["stage"] for r in rows}))
print("premature_press 计数:", sum(1 for r in rows if r["premature_press"] == "1"))
print("timeout 计数:", sum(1 for r in rows if r["timeout"] == "1"))

print("\n--- 刺激提前结束的行（无刺激期按键且 dev < -0.5 帧）---")
for i, r in enumerate(rows):
    dur, T = float(r["stimulus_dur_actual"]), float(r["T"])
    dev = (dur - T) / flip
    resp = r["Response"]
    rt = float(r["RT"]) if r["RT"] not in ("NA", "") else float("nan")
    has_in_stim = (resp not in ("NA", "")) and (rt < T)
    if not has_in_stim and dev < -0.5:
        print(
            "L%d: T=%.2f dur=%.2fms dev=%+.2f帧 Resp=%s RT=%s prem=%s to=%s rbd=%s frames=%s W=%.3f"
            % (i + 2, T, dur * 1000, dev, resp, r["RT"], r["premature_press"], r["timeout"],
               r["responded_by_deadline"], r["stimulus_frames"], float(r["W"]))
        )

print("\n--- 正常行的 dev 分布（无刺激期按键）---")
devs = []
for r in rows:
    dur, T = float(r["stimulus_dur_actual"]), float(r["T"])
    resp = r["Response"]
    rt = float(r["RT"]) if r["RT"] not in ("NA", "") else float("nan")
    if (resp not in ("NA", "")) and (rt < T):
        continue
    devs.append((dur - T) / flip)
devs.sort()
n = len(devs)
print("n=%d  min=%.2f  p1=%.2f  p50=%.2f  p99=%.2f  max=%.2f" % (
    n, devs[0], devs[int(0.01 * n)], devs[n // 2], devs[int(0.99 * n)], devs[-1]))
from collections import Counter
print("取整分布:", Counter(round(d) for d in devs).most_common(8))
