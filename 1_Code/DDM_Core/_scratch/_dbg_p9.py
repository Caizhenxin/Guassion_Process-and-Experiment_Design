# -*- coding: utf-8 -*-
"""调试 P9：模型章草稿为什么没被替换。"""
import sys
from pathlib import Path

ROOT = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
sys.path.insert(0, str(ROOT / "1_Code" / "DDM_Core"))
sys.path.insert(0, str(ROOT / "1_Code" / "Experiment"))

import manuscript as MS

t = MS.load_model_template()
print("template lines", len(t.splitlines()), "markers", len(MS.MARK_RE.findall(t)))
print("has '## 3.11'", "## 3.11" in t)
i = t.find("3.11")
print("context:", repr(t[i - 40:i + 60]))

vals = MS.model_values([], {}, None, {})
print("vals keys", sorted(vals))
text, missed = MS.render_model(t, vals)
print("rendered lines", len(text.splitlines()), "missed", len(missed), missed[:6])
print("pending in head", text.split("## 3.11")[0].count("【待数据："))
