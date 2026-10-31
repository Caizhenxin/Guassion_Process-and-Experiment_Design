"""按行替换 test-handover 里过期的待办断言（该文件中文是 \\u 转义写的，按行改最稳）。"""
import io

p = r'D:\GitHub_programe\GitHub\dsh-my-project-workbench\_evidence\test-handover.mjs'
lines = io.open(p, encoding='utf-8').read().split('\n')

start = None
for i in range(len(lines)):
    if "'function parseBoard'" in lines[i]:
        j = i
        while j > 0 and not lines[j].startswith('check('):
            j -= 1
        start = j
        break
if start is None:
    raise SystemExit('没找到待办断言块（check 开头行）')

end = start
while end < len(lines) and lines[end].rstrip() != '})':
    end += 1

block = [
    "check('待办收成一处：写总工作台总板，合并规则在 board.js', () => {",
    "  assert.ok(serverSource.includes(\"store: 'hub'\"), '缺总板分支')",
    "  assert.ok(serverSource.includes('board.js'), '合并规则应来自 board.js')",
    "  assert.ok(!/writeStore\\\\('todos\\.json'/.test(serverSource), 'todos 不该再写 DSH 数据目录')",
    "  const boardSource = readFileSync(join(root, 'dsh', 'board.js'), 'utf8')",
    "  assert.ok(boardSource.includes('export function parseBoard'), 'board.js 缺 parseBoard')",
    "  assert.ok(boardSource.includes('export function mergeTagBlock'), 'board.js 缺 mergeTagBlock')",
    "  assert.ok(boardSource.includes('【'), 'board.js 应负责拼项目标签')",
    '})',
]

out = lines[:start] + block + lines[end + 1:]
src = '\n'.join(out)
if "import { readFileSync } from 'node:fs'" not in src:
    src = src.replace("import assert from 'node:assert/strict'",
                      "import assert from 'node:assert/strict'\nimport { readFileSync } from 'node:fs'", 1)
io.open(p, 'w', encoding='utf-8', newline='\n').write(src)
print('replaced lines', start + 1, '-', end + 1)
