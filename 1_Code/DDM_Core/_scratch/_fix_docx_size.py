# -*- coding: utf-8 -*-
"""_fix_docx_size.py —— 手册 docx 重新生成后体积从 15031 B 变 15032 B，同步 Stage 7 §6.4"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
p = ROOT / "5_Reference/08_工作流/Stage7_数据采集执行与质控方案.md"
t = p.read_text(encoding="utf-8")
old = "`.docx`（15031 B）"
new = "`.docx`（15032 B）"
if new in t:
    print("[跳过] 已是 15032 B")
elif t.count(old) == 1:
    p.write_text(t.replace(old, new), encoding="utf-8", newline="\n")
    print("[替换] Stage7 .docx 体积 → 15032 B")
else:
    raise SystemExit(f"❌ 命中 {t.count(old)} 次")
