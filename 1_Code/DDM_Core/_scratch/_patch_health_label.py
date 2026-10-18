# -*- coding: utf-8 -*-
"""给 stage8_health.py 的组标识补上「来源目录」，避免同 tag 的两个组在概览表里分不清。"""
from pathlib import Path

p = Path(__file__).resolve().parents[1] / "stage8_health.py"
t = p.read_text(encoding="utf-8")

old1 = '''    return {
        "file": path.name, "tag": str(obj["tag"]),'''
new1 = '''    return {
        "file": path.name, "dir": path.parent.name, "tag": str(obj["tag"]),'''
assert old1 in t, "锚点 1 未命中"
t = t.replace(old1, new1)

old2 = ('    lines += ["", "| 组 | 人 | 口径 | `p_loo`÷`n_obs` | `k_max` | `n_flipped` | '
        '`max\\\\|θ\\\\|` | 判定 |",\n'
        '              "|---|---|---|---|---|---|---|---|"]')
new2 = ('    lines += ["", "| 组 | 来源目录 | 人 | 口径 | `p_loo`÷`n_obs` | `k_max` | '
        '`n_flipped` | `max\\\\|θ\\\\|` | 判定 |",\n'
        '              "|---|---|---|---|---|---|---|---|---|"]')
assert old2 in t, "锚点 2 未命中"
t = t.replace(old2, new2)

old3 = """            f"| {r['tag']} | {r['n_subjects']} | {('、'.join(r['levels']))} | {ratio_txt} | \""""
new3 = """            f"| {r['tag']} | `{r['dir']}` | {r['n_subjects']} | {('、'.join(r['levels']))} | {ratio_txt} | \""""
assert old3 in t, "锚点 3 未命中"
t = t.replace(old3, new3)

old4 = '''        lines += ["", f"## 组 {r['tag']}（{r['n_subjects']} 人，`{r['file']}`）", ""]'''
new4 = '''        lines += ["", f"## 组 {r['tag']}（{r['n_subjects']} 人，`{r['dir']}/{r['file']}`）", ""]'''
assert old4 in t, "锚点 4 未命中"
t = t.replace(old4, new4)
t = t.replace('''        "label": f"{obj['tag']}@{path.parent.name}",\n''', "")

p.write_text(t, encoding="utf-8", newline="\n")
import ast

ast.parse(t)
print("patched stage8_health.py: 4 处锚点全部命中，ast OK")
