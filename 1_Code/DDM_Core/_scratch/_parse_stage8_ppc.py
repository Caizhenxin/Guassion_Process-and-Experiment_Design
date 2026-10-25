import re
from pathlib import Path

rep = Path(r"2_Data\Real_Data\New_Design\_pipeline\stage8\stage8_report.md")
lines = rep.read_text(encoding="utf-8").splitlines()

hdr = re.compile(r"^#### (M-T\d) / 被试 (\d+)")
rows = []
cur = None
for ln in lines:
    m = hdr.match(ln.strip())
    if m:
        cur = {"model": m.group(1), "subj": int(m.group(2))}
        rows.append(cur)
        continue
    if cur is None:
        continue
    s = ln.strip()
    for key in ("omission_rate", "`acc`", "rt_p50", "rt_p50_correct", "rt_p50_error"):
        pass
    mm = re.match(r"^\|\s*`?(acc|omission_rate|rt_p50|rt_p50_correct)`?\s*\|(.*)$", s)
    if mm:
        cells = [c.strip() for c in mm.group(2).split("|")]
        cur[mm.group(1)] = cells

print(f"{'model':6} {'subj':>4} | {'obs_acc':>7} {'pred_acc':>8} | {'obs_p50':>7} {'pred_p50':>8} | {'obs_om':>7} {'pred_om':>7}")
for r in rows:
    def g(k):
        c = r.get(k)
        return (c[0], c[1]) if c else ("-", "-")
    oa, pa = g("acc")
    o5, p5 = g("rt_p50")
    oo, po = g("omission_rate")
    print(f"{r['model']:6} {r['subj']:>4} | {oa:>7} {pa:>8} | {o5:>7} {p5:>8} | {oo:>7} {po:>7}")
