# -*- coding: utf-8 -*-
"""§7 标题改为「已结清」，与 2026-10-18 签批一致。"""
from pathlib import Path

p = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\5_Reference\08_工作流\正式采集_候选设计_v2_定稿.md")
a = p.read_text(encoding="utf-8").split("\n")
old = "## 7. 待确认事项（需用户 / 导师拍板）"
new = "## 7. 待确认事项（**已全部结清**：①②③⑦ 随 2026-10-18 签批定案；④⑤⑥⑧⑨⑩ 已裁定或已判决）"
i = [k for k, l in enumerate(a) if l == old]
assert len(i) == 1, i
a[i[0]] = new
p.write_text("\n".join(a), encoding="utf-8", newline="\n")
print("[ok]", a[i[0]])
