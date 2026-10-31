"""修 test-handover 里过期的待办断言（V7 后待办落总板、合并规则在 board.js）。"""
import io

p = r'D:\GitHub_programe\GitHub\dsh-my-project-workbench\_evidence\test-handover.mjs'
src = io.open(p, encoding='utf-8').read()

old_import = "import assert from 'node:assert/strict'\nimport { readFile } from 'node:fs/promises'"
new_import = "import assert from 'node:assert/strict'\nimport { readFileSync } from 'node:fs'\nimport { readFile } from 'node:fs/promises'"

old = """check('待办落在项目内的待办板，并带老数据迁移', () => {
  assert.ok(serverSource.includes('BOARD_REL'), '缺 BOARD_REL')
  assert.ok(serverSource.includes('function parseBoard'), '缺 parseBoard')
  assert.ok(serverSource.includes('migrateBoard'), '缺老数据迁移')
  assert.ok(!/writeStore\\('todos\\.json'/.test(serverSource), 'todos 不该再写 DSH 数据目录')
})"""

new = """check('待办收成一处：写总工作台总板，合并规则在 board.js', () => {
  assert.ok(serverSource.includes("store: 'hub'"), '缺总板分支')
  assert.ok(serverSource.includes('board.js'), '合并规则应来自 board.js')
  assert.ok(!/writeStore\\('todos\\.json'/.test(serverSource), 'todos 不该再写 DSH 数据目录')
  const boardSource = readFileSync(join(root, 'dsh', 'board.js'), 'utf8')
  assert.ok(boardSource.includes('export function parseBoard'), 'board.js 缺 parseBoard')
  assert.ok(boardSource.includes('export function mergeTagBlock'), 'board.js 缺 mergeTagBlock')
  assert.ok(boardSource.includes('\\u3010'), 'board.js 应负责拼项目标签')
})"""

changed = False
if old_import in src:
    src = src.replace(old_import, new_import, 1)
    changed = True
if old in src:
    src = src.replace(old, new, 1)
    changed = True
elif new in src:
    print('board check already patched')
else:
    raise SystemExit('ANCHOR MISS: board check')

io.open(p, 'w', encoding='utf-8', newline='\n').write(src)
print('patched', changed)
