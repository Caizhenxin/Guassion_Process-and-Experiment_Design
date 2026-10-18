"""把「Δelpd 的 SE 必须配对」这一条补进 README §8.69 与 D98 行。"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
README = ROOT / "1_Code" / "DDM_Core" / "README.md"

subs = [
    ("- **三个自坑**：", "- **四个自坑**："),
    ("  现改为「被试层众数灰点 + 组均值 ± 被试间 SEM」。",
     "  现改为「被试层众数灰点 + 组均值 ± 被试间 SEM」；④ Δelpd 的 SE 曾按 "
     "`√(se_a² + se_b²)` 相加，把同一批数据的共同变异算了两遍（实测 1.1 → 38.2），"
     "现用配对口径 `√n · sd(elpd_i^A − elpd_i^B)`。"),
]

text = README.read_text(encoding="utf-8")
for old, new in subs:
    assert text.count(old) == 1, (old, text.count(old))
    text = text.replace(old, new)
README.write_text(text, encoding="utf-8", newline="\n")
print("ok README", len(text.splitlines()))
