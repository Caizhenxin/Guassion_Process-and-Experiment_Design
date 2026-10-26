from pathlib import Path

P = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design"
         r"\5_Reference\03_论文写作\定编依据_N精度与N区分_20261025.md")
s = P.read_text(encoding="utf-8")
old = "`DEV_MAX = 0.0167`；`\\|stimulus_dur_actual − T\\| > 一帧` ⇒ 刺激期内按键，剔除"
new = "`DEV_MAX = 0.0167`；`stimulus_dur_actual` 与 `T` 的差超过一帧 ⇒ 刺激期内按键，剔除"
assert s.count(old) == 1, s.count(old)
P.write_text(s.replace(old, new), encoding="utf-8", newline="\n")
print("fixed table cell")
