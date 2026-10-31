"""P5 补丁 4：无标签行不再被任意项目认领 + 总板路径显示为绝对路径。"""
import io

WB = r'D:\GitHub_programe\GitHub\dsh-my-project-workbench'


def grab(rel):
    return io.open(WB + '\\' + rel.replace('/', '\\'), encoding='utf-8').read()


def put(rel, body):
    io.open(WB + '\\' + rel.replace('/', '\\'), 'w', encoding='utf-8', newline='\n').write(body.replace('\r\n', '\n'))
    print('written', rel, len(body), 'chars')


# 1) board.js：加 hasAnyTag
board = grab('dsh/board.js')
if 'export function hasAnyTag' not in board:
    anchor = 'export function filterByTag(items, id) {'
    add = """// 板上有没有任何项目标签：用来区分「还没迁移的老板」和「已按标签分好的板」。
export function hasAnyTag(items) {
  return (Array.isArray(items) ? items : []).some((item) => Boolean(item.tag))
}

"""
    assert anchor in board
    board = board.replace(anchor, add + anchor, 1)
    put('dsh/board.js', board)
else:
    print('board.js already patched')

# 2) index.js：迁移只对无标签老板生效；hub 路径显示绝对路径
idx = grab('dsh/index.js')

old_import = "import { BOARD_DATE, BOARD_HEADER, BOARD_LINE, adoptLegacy, boardText, dateOnly, filterByTag, mergeTagBlock, normalizeTodoList, parseBoard } from './board.js'"
if old_import not in idx:
    raise SystemExit('import anchor miss')
idx = idx.replace(
    old_import,
    "import { BOARD_DATE, BOARD_HEADER, BOARD_LINE, adoptLegacy, boardText, dateOnly, filterByTag, hasAnyTag, mergeTagBlock, normalizeTodoList, parseBoard } from './board.js'",
    1,
)

old_read = """  async function readBoard() {
    const target = await boardTarget()
    let source = await readFile(target.abs, 'utf8').catch(() => '')
    let items = filterByTag(parseBoard(source), target.id)
    if (!items.length) {
      const migrated = await migrateBoard(target).catch(() => 0)
      if (migrated) {
        source = await readFile(target.abs, 'utf8').catch(() => '')
        items = filterByTag(parseBoard(source), target.id)
      }
    }
    return { items, path: displayPath(target.abs), kind: target.kind, id: target.id }
  }"""

new_read = """  async function readBoard() {
    const target = await boardTarget()
    let source = await readFile(target.abs, 'utf8').catch(() => '')
    let all = parseBoard(source)
    let items = filterByTag(all, target.id)
    // 迁移只对「整块板还没有任何项目标签」的老板生效。
    // 已经按标签分好的板上，无标签行属于谁都不属于：谁都不许认领 ——
    // 否则先打开面板的那个项目，会在保存时把别的项目的活改写成自己的标签（已经真实发生过一次）。
    if (!items.length && !hasAnyTag(all)) {
      const migrated = await migrateBoard(target).catch(() => 0)
      if (migrated) {
        source = await readFile(target.abs, 'utf8').catch(() => '')
        all = parseBoard(source)
        items = filterByTag(all, target.id)
      }
    }
    const shown = target.kind === 'hub' ? target.abs : displayPath(target.abs)
    return { items, path: shown, kind: target.kind, id: target.id, untagged: all.filter((item) => !item.tag).length }
  }"""

assert old_read in idx, 'readBoard anchor miss'
idx = idx.replace(old_read, new_read, 1)
put('dsh/index.js', idx)

# 3) test-board：补两条「有标签的板子上，无标签行不归任何人」
tb = grab('_evidence/test-board.mjs')
if 'hasAnyTag' not in tb:
    anchor = "check('过滤：只取本项目的行', () => {"
    add = """check('有标签的板上，无标签行不算任何人的（否则会被先打开面板的项目认领）', () => {
  const items = board.parseBoard(BOARD_FIXTURE + '- [ ] 2026-10-28 谁也没认领的老行\\n')
  assert.equal(board.hasAnyTag(items), true)
  assert.equal(board.filterByTag(items, 'gp').length, 2, '无标签行不该混进 gp')
  assert.equal(board.filterByTag(items, 'other').length, 1, '无标签行也不该混进 other')
})

check('整块板一个标签都没有 → 视为还没迁移的老板', () => {
  const items = board.parseBoard('- [ ] 2026-10-28 老行甲\\n- [x] 2026-10-28 老行乙\\n')
  assert.equal(board.hasAnyTag(items), false)
})

"""
    assert anchor in tb
    tb = tb.replace(anchor, add + anchor, 1)
    put('_evidence/test-board.mjs', tb)
else:
    print('test-board already patched')
