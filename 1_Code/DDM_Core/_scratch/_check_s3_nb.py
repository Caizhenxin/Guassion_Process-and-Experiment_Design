# -*- coding: utf-8 -*-
"""校验 S3 notebook 的 nbformat 结构（不执行，只查 JSON 与单元格式）。"""
import json
from pathlib import Path

p = Path("D:/GitHub_programe/GitHub/Guassion-Process-Experiment-Design/1_Code/Python_for_Generate/S3_两阶段DDM_模拟数据生成.ipynb")
nb = json.loads(p.read_text(encoding="utf-8"))
print("nbformat", nb.get("nbformat"), nb.get("nbformat_minor"))
print("metadata keys", sorted(nb.get("metadata", {})))
cells = nb["cells"]
print("cells", len(cells), "code", sum(c["cell_type"] == "code" for c in cells),
      "md", sum(c["cell_type"] == "markdown" for c in cells))
bad = [i for i, c in enumerate(cells)
       if c["cell_type"] == "code" and not isinstance(c.get("source"), list)]
print("bad source", bad)
print("first md:", "".join(cells[0]["source"]).splitlines()[0])
print("code lines total:", sum(len("".join(c["source"]).splitlines())
                               for c in cells if c["cell_type"] == "code"))
