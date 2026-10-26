from pathlib import Path

P = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design"
         r"\5_Reference\03_论文写作\定编依据_N精度与N区分_20261025.md")
s = P.read_text(encoding="utf-8")
old = "| 前试次也快 | 剔除 3-1 后 0.087（基线 0.010） | 轻微成簇，但 `P(前两试次都快 | 本试次快)` 仅 0.038 ⇒ 不成串 |"
new = "| 前试次也快 | 剔除 3-1 后 0.087（基线 0.010） | 轻微成簇，但「前两试次都快」在「本试次快」中的占比仅 0.038 ⇒ 不成串 |"
assert s.count(old) == 1
P.write_text(s.replace(old, new), encoding="utf-8", newline="\n")
print("fixed L302")
