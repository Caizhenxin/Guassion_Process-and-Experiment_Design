"""scan_min_n.py 的脚手架冒烟：只验「生成数据 / 写报告」两段，不做拟合（拟合要几十分钟）。"""
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
sys.path.insert(0, str(ROOT / "1_Code" / "Experiment"))

import scan_min_n as SC

tmp = Path(tempfile.mkdtemp(prefix="scan_smoke_"))
print("tmp =", tmp)

# 1) 生成 1 名合成被试（组 1 ⇒ 4 个兜底练习 + 576 正式）
d = SC.gen_data(tmp / "data", n=1, group=1, seed=901, n_rep=12)
txt = sorted(d.glob("exp_group1_subject*.txt"))
print("txt 文件 =", [p.name for p in txt])
rows = txt[0].read_text(encoding="utf-8").splitlines()
print("行数 =", len(rows), "（应为 1 + 580）")
hdr = rows[0].split("\t")
print("列数 =", len(hdr), "前 5 列 =", hdr[:5])
assert len(rows) == 581, len(rows)
assert len(hdr) == 25, len(hdr)

# 2) 造两条假判词写报告，检查 Markdown 表格与 JSON 追加
fake = [
    {"n": 4, "group": 1, "status": "BAD", "n_flipped": 2, "n_eig": 16,
     "p_loo_ratio": 1.234, "k_max": 0.0, "max_abs_theta": 71.5, "elpd": -500.0,
     "reasons": ["超参数 Hessian 非正定（`n_flipped` = 2/16，D74）"],
     "seconds": 6000.0, "wall": 6100.0, "json": "x/stage8_group_1.json"},
    {"n": 8, "group": 1, "status": "OK", "n_flipped": 0, "n_eig": 16,
     "p_loo_ratio": 0.05, "k_max": 0.4, "max_abs_theta": 5.0, "elpd": -1200.0,
     "reasons": [], "seconds": 12000.0, "wall": 12200.0, "json": "y/stage8_group_1.json"},
]
SC.write_reports(tmp, fake)
md = (tmp / "scan_min_n.md").read_text(encoding="utf-8")
print("--- scan_min_n.md ---")
print(md)
js = json.loads((tmp / "scan_min_n.json").read_text(encoding="utf-8"))
print("json 条数 =", len(js), [r["n"] for r in js])
assert len(js) == 2 and md.count("| 4 |") == 1 and md.count("| 8 |") == 1
assert "n_flipped` = 2/16" in md

# 3) 追加语义：再写一条 n=4 应覆盖而不是新增
SC.write_reports(tmp, [dict(fake[0], status="WARN", n_flipped="1/16")])
md2 = (tmp / "scan_min_n.md").read_text(encoding="utf-8")
js2 = json.loads((tmp / "scan_min_n.json").read_text(encoding="utf-8"))
assert len(js2) == 2 and any(r["status"] == "WARN" for r in js2), js2
print("追加语义 OK：n=4 被覆盖为 WARN，条数仍 2")
print("SMOKE OK")
