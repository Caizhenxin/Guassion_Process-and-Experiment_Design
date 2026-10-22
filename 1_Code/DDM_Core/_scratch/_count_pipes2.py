import sys
from pathlib import Path

sys.path.insert(0, r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\1_Code\DDM_Core\_scratch")
import _apply_d117_docs as m  # noqa: E402

combined = m.DECISION.rstrip() + m.DECISION_REASON + m.DECISION_ARTIFACT
for name in ("DECISION", "DECISION_REASON", "DECISION_ARTIFACT", "PROGRESS",
             "CHANGELOG", "EVIDENCE", "README_ROW", "FIG_ROW"):
    s = getattr(m, name)
    print(f"{name}: pipes={s.count('|')} len={len(s)}")
print("combined:", combined.count("|"))
for i, ch in enumerate(combined):
    if ch == "|":
        print(i, combined[max(0, i - 30):i + 5].replace("\n", " "))
