"""统一 §〇 标题口径：工具接受一级/二级标题，交接文件改成二级 + 第 9 次写。"""
import io

HUB = r'D:\GitHub_programe\GitHub\DSH_Workbench'
P = r'D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design'

tool = HUB + r'\tools\体检.py'
src = io.open(tool, encoding='utf-8').read()
old = 're.match(r"^##\\s*§〇", ln)'
new = 're.match(r"^#{1,2}\\s*§〇", ln)'
if old in src:
    src = src.replace(old, new, 1)
    src = src.replace(
        '找不到 §〇 段（应以 `## §〇` 开头）',
        '找不到 §〇 段（应以 # §〇 或 ## §〇 开头）',
        1,
    )
    io.open(tool, 'w', encoding='utf-8', newline='\n').write(src)
    print('体检.py：标题判据放宽为一级或二级')
else:
    print('体检.py：已放宽或锚点不符', new in src)

hand = P + r'\_交接\当前交接.md'
text = io.open(hand, encoding='utf-8').read()
if text.startswith('# §〇 当前交接\n'):
    text = text.replace('# §〇 当前交接\n', '## §〇 当前交接（覆盖写 · 第 9 次写 · 2026-10-30）\n', 1)
    io.open(hand, 'w', encoding='utf-8', newline='\n').write(text)
    print('交接标题：改成二级 + 第 9 次写')
else:
    print('交接标题：已是新格式')
