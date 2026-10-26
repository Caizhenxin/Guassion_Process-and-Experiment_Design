"""从 Stage 8 报告里抽 PPC 的全局统计量（rt_p50 / acc / omission），逐被试一行。"""
import re
import pathlib

P = pathlib.Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design"
                 r"\2_Data\Real_Data\New_Design\_pipeline\stage8_d123\stage8_report.md")
lines = P.read_text(encoding="utf-8").splitlines()

cur_model = cur_sub = None
rows = []
i = 0
while i < len(lines):
    ln = lines[i]
    m = re.match(r"#### (M-T\d) / 被试 (\d+)", ln)
    if m:
        cur_model, cur_sub = m.group(1), int(m.group(2))
    if ln.strip() == "### 全局统计量" and cur_model:
        # 表头 2 行后是数据行，直到空行
        j = i + 3
        got = {}
        while j < len(lines) and lines[j].startswith("|`"):
            cells = [c.strip() for c in lines[j].strip().strip("|").split("|")]
            name = cells[0].strip("`")
            if name in ("rt_p50", "acc", "omission_rate"):
                got[name] = (float(cells[1]), float(cells[2]))
            j += 1
        if "rt_p50" in got:
            rows.append((cur_model, cur_sub, got))
        i = j
        continue
    i += 1

print(f"{'模型':6s}{'被试':>4s}{'RT中位观测':>10s}{'预测':>8s}{'差ms':>7s}"
      f"{'acc观测':>8s}{'acc预测':>8s}{'漏答差':>7s}")
for model, sub, g in rows:
    o_rt, p_rt = g["rt_p50"]
    o_ac, p_ac = g.get("acc", (float("nan"),) * 2)
    o_om, p_om = g.get("omission_rate", (float("nan"),) * 2)
    print(f"{model:6s}{sub:>4d}{o_rt * 1000:>10.0f}{p_rt * 1000:>8.0f}"
          f"{(p_rt - o_rt) * 1000:>7.0f}{o_ac:>8.3f}{p_ac:>8.3f}"
          f"{(p_om - o_om) * 100:>7.1f}")

for model in ("M-T1", "M-T3"):
    sub_rows = [r for r in rows if r[0] == model]
    if not sub_rows:
        continue
    d = [(r[2]["rt_p50"][1] - r[2]["rt_p50"][0]) * 1000 for r in sub_rows]
    d.sort()
    med = d[len(d) // 2]
    print(f"\n{model}：n={len(d)}；RT 中位预测−观测 中位 {med:+.0f} ms"
          f"、范围 {d[0]:+.0f} … {d[-1]:+.0f}、"
          f"偏短 {sum(1 for x in d if x < -20)}/{len(d)}、偏长 {sum(1 for x in d if x > 20)}/{len(d)}")
