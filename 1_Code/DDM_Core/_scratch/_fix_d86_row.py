from pathlib import Path
p = Path(r"5_Reference\08_工作流\工作流_主计划.md")
s = p.read_text(encoding="utf-8")
lines = s.split("\n")
row = lines[511]
assert row.startswith("| **D86** |"), row[:40]
import re
# 把含竖线的正则代码段整段换成不含竖线的说法
new_row = re.sub(r"⇒ 判据改 `[^`]*D\(\\d\+\)[^`]*`。", "⇒ 判据放宽为「表格行 + 可选加粗/删除线标记的 D 编号」。", row, count=1)
assert new_row != row, "未命中正则段"
lines[511] = new_row
p.write_text("\n".join(lines), encoding="utf-8", newline="\n")
print("pipes=", new_row.count("|"))
