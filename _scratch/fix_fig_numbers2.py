# -*- coding: utf-8 -*-
"""临时：用正则收尾图号统一，并检查残留。"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "5_Reference" / "终版论文格式及要求"

FILES = [
    DOC / "图表与指标说明书_面向同门_20260912.md",
    DOC / "必须补的表清单_20260912.md",
    DOC / "规则5与规则7_Methods与Results段落_20260912.md",
    DOC / "_v3_正文.md",
]

RULES = [
    (r"图\s*5-3", "图6-1"),
    (r"图\s*7-6（左）", "图7-3（左）"),
    (r"图\s*7-3\s*[~～]\s*7-5", "图7-4~7-6"),
    (r"图\s*8-3", "图8-2"),
    (r"图\s*6-1\s*\(曲线", "图6-4（曲线"),
    (r"图\s*6-3（曲线", "图6-4（曲线"),
    (r"`F5-3_omission_delta\.png`", "`F6-1_omission_delta.png`"),
    (r"`F7-3_ppc_interval\.png`", "`F7-4_ppc_interval.png`"),
    (r"`F7-4_ppc_coverage\.png`", "`F7-5_ppc_coverage.png`"),
    (r"`F7-5_ppc_qp\.png`", "`F7-6_ppc_qp.png`"),
    (r"`F7-6_model_comparison\.png`", "`F7-3_model_comparison.png`"),
    (r"`F8-3_stimcoding_crf\.png`", "`F8-2_stimcoding_crf.png`"),
]

for path in FILES:
    s = path.read_text(encoding="utf-8")
    orig = s
    hits = []
    for pat, rep in RULES:
        s, n = re.subn(pat, rep, s)
        if n:
            hits.append(f"{pat}×{n}")
    if s != orig:
        path.write_text(s, encoding="utf-8")
    print(f"[{path.name}] 修改: {', '.join(hits) if hits else '无'}")

print("\n=== 残留检查（应为空或仅合理项）===")
for path in FILES + [DOC / "_v3_front_摘要.md", DOC / "_build_docx_v3.py"]:
    s = path.read_text(encoding="utf-8")
    bad = re.findall(r"图\s*(?:5-3|8-3|7-6(?!\s*[（(]?[^\d])|7-2\s*\|)", s)
    print(f"  {path.name}: {sorted(set(bad)) if bad else 'OK'}")
