# -*- coding: utf-8 -*-
"""一次性修复：删掉主计划里重复插入的 D66 行（连续重复且含 D66）。"""
from pathlib import Path

p = Path('5_Reference/08_工作流/工作流_主计划.md')
ls = p.read_text(encoding='utf-8').split('\n')
out, dropped = [], []
for ln in ls:
    if out and ln == out[-1] and 'D66' in ln:
        dropped.append(ln[:60])
        continue
    out.append(ln)
text = '\n'.join(out)
if not text.endswith('\n'):
    text += '\n'
p.write_text(text, encoding='utf-8', newline='\n')
print('dropped', len(dropped), '-> now', len(out), 'lines')
for d in dropped:
    print('  -', d)
