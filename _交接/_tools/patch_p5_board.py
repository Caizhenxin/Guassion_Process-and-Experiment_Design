"""P5：待办板切总工作台（全机唯一落点 + 每行带项目标签）。

为什么要改：插件原来把待办写 `_交接/待办板.md`，而那个文件 2026-10-28 起已作废、只剩指针；
再加上总工作台自己的体检器只认 `【项目id】` 标签的机器行 —— 插件不改，两套待办永远打架。

三条规矩落在代码里：
  1. 总工作台有 `boards/待办板.md` 就用它，没有才退回项目内的（单项目用法照样能用）。
  2. 读：只取本项目标签的行（以及历史无标签行）。
  3. 写：只替换本项目标签的行，别人的行与人写的说明**原样保留**（surgical merge）。
"""
import io
import os

WB = r'D:\GitHub_programe\GitHub\dsh-my-project-workbench'


def read(p):
    return io.open(p, encoding='utf-8').read()


def write(p, s):
    io.open(p, 'w', encoding='utf-8', newline='\r\n' if '\r\n' in s else '\n').write(s)


cache = {}
edits = []


def edit(rel, old, new, label):
    edits.append((rel, old, new, label))


# ================================================================= index.js
edit('dsh/index.js',
     "import { WORKBENCH_ROOT, appendHealthTodos, inspectProject } from './health.js'",
     "import { BOARD_DATE, BOARD_HEADER, BOARD_LINE, adoptLegacy, boardText, dateOnly, filterByTag, mergeTagBlock, normalizeTodoList, parseBoard } from './board.js'\n"
     "import { WORKBENCH_ROOT, appendHealthTodos, inspectProject } from './health.js'",
     'index imports')

edit('dsh/index.js',
     """//   共享层 = _交接/待办板.md，「该做什么」的唯一落点，体检的 ⛔ 项也追加到这里。
const HANDOVER_REL = join('_交接', '当前交接.md')
const BOARD_REL = join('_交接', '待办板.md')
const HANDOVER_MAX = 4096
// 判据只写在这一个地方：客户端与自测脚本都读它。两处各判一次 = 两份结论，早晚打架。
const HANDOVER_REQUIRED = ['上次进度', '下一步', '卡点']
const BOARD_HEADER = [
  '# 待办板（全机唯一落点）',
  '',
  '> 「该做什么」只在**这一处**记；一行一件：`- [ ] YYYY-MM-DD 事项`。',
  '> 做完打勾或删行；体检的 ⛔ 项会自动追加到这里，同一件只许一行。',
  '',
  '',
].join('\\n')
const BOARD_LINE = /^\\s*-\\s*\\[( |x|X)\\]\\s*(.+?)\\s*$/
const BOARD_DATE = /^(\\d{4}-\\d{2}-\\d{2})\\s+/
""",
     """//   共享层 = 待办板，「该做什么」的唯一落点，体检的 ⛔ 项也追加到这里。
//            2026-10-28 起唯一落点是总工作台的 boards/待办板.md（行首带【项目id】）；
//            项目内 _交接/待办板.md 只作废指针，仅当总工作台没有待办板时兜底。
const HANDOVER_REL = join('_交接', '当前交接.md')
const BOARD_REL = join('_交接', '待办板.md')
const HUB_BOARD_REL = join('boards', '待办板.md')
const HANDOVER_MAX = 4096
// 判据只写在这一个地方：客户端与自测脚本都读它。两处各判一次 = 两份结论，早晚打架。
const HANDOVER_REQUIRED = ['上次进度', '下一步', '卡点']
""",
     'index constants')

edit('dsh/index.js',
     """  function dateOnly() {
    const now = new Date()
    const pad = (value) => String(value).padStart(2, '0')
    return now.getFullYear() + '-' + pad(now.getMonth() + 1) + '-' + pad(now.getDate())
  }

  function normalizeTodoList(list) {
    if (!Array.isArray(list)) return []
    return list
      .map((item, index) => ({
        id: String((item && item.id) || 'b' + index),
        text: String((item && (item.text || item.title || item.content)) || '').trim(),
        at: String((item && (item.at || item.time)) || ''),
        done: Boolean(item && (item.done || item.completed || item.finished)),
      }))
      .filter((item) => item.text)
  }

  // 待办板是 markdown：人能直接看、能进 git，机器也能逐行判。
  function parseBoard(source) {
    const items = []
    for (const line of String(source || '').split(/\\r?\\n/)) {
      const matched = BOARD_LINE.exec(line)
      if (!matched) continue
      const body = matched[2]
      const dated = BOARD_DATE.exec(body)
      items.push({
        id: 'b' + items.length,
        text: dated ? body.slice(dated[0].length) : body,
        at: dated ? dated[1] : '',
        done: matched[1].toLowerCase() === 'x',
      })
    }
    return items
  }

  function boardText(items, preamble) {
    const rows = items.map((item) => {
      const mark = item.done ? 'x' : ' '
      const day = /^\\d{4}-\\d{2}-\\d{2}/.test(String(item.at || '')) ? item.at : dateOnly()
      return '- [' + mark + '] ' + day + ' ' + item.text
    })
    return (preamble == null ? BOARD_HEADER : preamble) + (rows.length ? rows.join('\\n') + '\\n' : '')
  }

  // 一次性迁移：老版本把待办存在 DSH 数据目录的 todos.json，搬进项目内的待办板（唯一落点）。
  async function migrateBoard() {
    const legacy = normalizeTodoList(await readStore('todos.json', []))
    if (!legacy.length) return 0
    const abs = join(projectRoot, BOARD_REL)
    await mkdir(dirname(abs), { recursive: true })
    await writeFile(abs, boardText(legacy), 'utf8')
    return legacy.length
  }

  async function readBoard() {
    const abs = join(projectRoot, BOARD_REL)
    let source = ''
    try {
      source = await readFile(abs, 'utf8')
    } catch {
      const migrated = await migrateBoard()
      if (migrated) source = await readFile(abs, 'utf8').catch(() => '')
    }
    return { items: parseBoard(source), path: displayPath(abs) }
  }

  async function saveBoard(list) {
    const abs = join(projectRoot, BOARD_REL)
    await mkdir(dirname(abs), { recursive: true })
    // 只在文件不存在时写默认抬头；否则**保留人写在列表之外的行**（说明、分组标题）。
    // 以前这里用 boardText 整篇重写，任何人往待办板加一行说明，下一次保存就会被静默吃掉。
    const existing = await readFile(abs, 'utf8').catch(() => '')
    let preamble = BOARD_HEADER
    if (existing.trim()) {
      const kept = existing.split(/\\r?\\n/).filter((line) => !BOARD_LINE.test(line))
      const head = kept.join('\\n').replace(/\\s+$/, '')
      if (head.trim()) preamble = head + '\\n\\n'
    }
    await writeFile(abs, boardText(normalizeTodoList(list), preamble), 'utf8')
    return readBoard()
  }""",
     """  // 待办板落在哪：总工作台有 boards/待办板.md 就用它（全机唯一落点），否则退回项目内的。
  async function boardTarget() {
    const hubBoard = join(hubRoot, HUB_BOARD_REL)
    const exists = await stat(hubBoard).then((info) => info.isFile()).catch(() => false)
    if (!exists) return { kind: 'project', abs: join(projectRoot, BOARD_REL), id: null }
    const found = await projectIdOf()
    return { kind: 'hub', abs: hubBoard, id: found.id }
  }

  // 一次性迁移：老数据在 DSH 数据目录的 todos.json，以及项目内那份已作废的待办板。
  // 只在「本项目在目标板上还没有任何行」时搬，搬过一次就不会重复（否则每读一次都翻倍）。
  async function migrateBoard(target) {
    const legacy = normalizeTodoList(await readStore('todos.json', []))
    if (target.kind === 'project') {
      if (!legacy.length) return 0
      await mkdir(dirname(target.abs), { recursive: true })
      await writeFile(target.abs, boardText(legacy, BOARD_HEADER), 'utf8')
      return legacy.length
    }
    const oldBoard = await readFile(join(projectRoot, BOARD_REL), 'utf8').catch(() => '')
    const adopted = adoptLegacy(parseBoard(oldBoard), target.id)
    const seen = new Set(adopted.map((item) => item.text))
    const items = adopted.concat(legacy.filter((item) => !seen.has(item.text)))
    if (!items.length) return 0
    const board = await readFile(target.abs, 'utf8').catch(() => BOARD_HEADER)
    await writeFile(target.abs, mergeTagBlock(board, items, { id: target.id, date: dateOnly() }), 'utf8')
    return items.length
  }

  async function readBoard() {
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
  }

  async function saveBoard(list) {
    const target = await boardTarget()
    const items = normalizeTodoList(list)
    await mkdir(dirname(target.abs), { recursive: true })
    if (target.kind === 'hub') {
      // 只换本项目标签的行：别人的项目行、人写的说明与分组标题，一个字都不许动。
      const existing = await readFile(target.abs, 'utf8').catch(() => BOARD_HEADER)
      await writeFile(target.abs, mergeTagBlock(existing, items, { id: target.id, date: dateOnly() }), 'utf8')
      return readBoard()
    }
    // 单项目兜底：只在文件不存在时写默认抬头，否则保留列表之外的行。
    const existing = await readFile(target.abs, 'utf8').catch(() => '')
    let preamble = BOARD_HEADER
    if (existing.trim()) {
      const kept = existing.split(/\\r?\\n/).filter((line) => !BOARD_LINE.test(line))
      const head = kept.join('\\n').replace(/\\s+$/, '')
      if (head.trim()) preamble = head + '\\n\\n'
    }
    await writeFile(target.abs, boardText(items, preamble), 'utf8')
    return readBoard()
  }""",
     'index board impl')

edit('dsh/index.js',
     """        if (request.method === 'GET') {
          const board = await readBoard()
          return ok({ ok: true, todos: board.items, boardPath: board.path, store: 'board' })
        }
        const body = await request.json()
        const board = await saveBoard(Array.isArray(body && body.todos) ? body.todos : [])
        return ok({ ok: true, todos: board.items, boardPath: board.path, store: 'board' })""",
     """        if (request.method === 'GET') {
          const board = await readBoard()
          return ok({ ok: true, todos: board.items, boardPath: board.path, store: board.kind, projectId: board.id })
        }
        const body = await request.json()
        const board = await saveBoard(Array.isArray(body && body.todos) ? body.todos : [])
        return ok({ ok: true, todos: board.items, boardPath: board.path, store: board.kind, projectId: board.id })""",
     'index todos route')

edit('dsh/index.js',
     """        const report = await inspectProject({ root: projectRoot, inspectHandover, hub: hubRoot, archiveId: (await projectIdOf()).id })
        const boardAbs = join(projectRoot, BOARD_REL)""",
     """        const target = await boardTarget()
        const report = await inspectProject({
          root: projectRoot,
          inspectHandover,
          hub: hubRoot,
          archiveId: (await projectIdOf()).id,
          board: { path: target.abs, id: target.id },
        })
        const boardAbs = target.abs""",
     'index health route')

edit('dsh/index.js',
     "            todo = await appendHealthTodos({ boardPath: boardAbs, report, date: dateOnly() })",
     "            todo = await appendHealthTodos({ boardPath: boardAbs, report, date: dateOnly(), id: target.id })",
     'index health append')

# ================================================================= health.js
edit('dsh/health.js',
     'function vector(a, b) {',
     "import { BOARD_DATE, BOARD_LINE, BOARD_TAG } from './board.js'\n\nfunction vector(a, b) {",
     'health import')

edit('dsh/health.js',
     'export async function inspectProject({ root, selfRoot, inspectHandover, hub, archiveId, now = Date.now() }) {',
     'export async function inspectProject({ root, selfRoot, inspectHandover, hub, archiveId, board = null, now = Date.now() }) {',
     'health signature')

edit('dsh/health.js',
     """    const boardText = (await read(vector('_交接', '待办板.md'))) || ''
    const boardLines = boardText.split(/\\r?\\n/).filter((line) => /^\\s*-\\s*\\[( |x|X)\\]/.test(line))""",
     """    // 待办板现在是全机一个文件：只判属于本项目标签的行（历史无标签行也认，免得迁移期报假警）。
    const rawBoard = board && board.path
      ? (await readFile(board.path, 'utf8').catch(() => '')) || ''
      : (await read(vector('_交接', '待办板.md'))) || ''
    const boardLines = rawBoard
      .split(/\\r?\\n/)
      .filter((line) => /^\\s*-\\s*\\[( |x|X)\\]/.test(line))
      .filter((line) => {
        if (!board || !board.id) return true
        const hit = BOARD_LINE.exec(line)
        const tag = hit ? BOARD_TAG.exec(hit[2].replace(BOARD_DATE, '')) : null
        return !tag || tag[1] === board.id
      })""",
     'health board judge')

edit('dsh/health.js',
     """/** 机器追加的一行：人能读、机器能全等比对。测量值只进正文，绝不进键。 */
export function buildHealthLine(rule, date) {
  const mark = rule.status === 'fail' ? '⛔' : '⚠'
  const body = String(rule.evidence || rule.title).replace(/\\s+/g, ' ').trim()
  return '- [ ] ' + date + ' ' + mark + ' ' + body + ' ⟦health:' + rule.id + '⟧'
}

export async function readBoardKeys(absolutePath) {""",
     """/** 机器追加的一行：人能读、机器能全等比对。测量值只进正文，绝不进键。 */
export function buildHealthLine(rule, date, id = null) {
  const mark = rule.status === 'fail' ? '⛔' : '⚠'
  const body = String(rule.evidence || rule.title).replace(/\\s+/g, ' ').trim()
  const tag = id ? '【' + id + '】' : ''
  return '- [ ] ' + date + ' ' + tag + mark + ' ' + body + ' ⟦health:' + rule.id + '⟧'
}

// 只认本项目标签的机器行：别的项目的 ⛔ 不许把自己这一项挤成「已存在」。
export async function readBoardKeys(absolutePath, id = null) {""",
     'health build line')

edit('dsh/health.js',
     """  for (const line of String(source).split(/\\r?\\n/)) {
    const hit = HEALTH_KEY.exec(line)
    if (!hit) continue
    map.set(hit[1], { done: /^\\s*-\\s*\\[[xX]\\]/.test(line), line })
  }""",
     """  for (const line of String(source).split(/\\r?\\n/)) {
    const hit = HEALTH_KEY.exec(line)
    if (!hit) continue
    if (id) {
      const listLine = BOARD_LINE.exec(line)
      const tag = listLine ? BOARD_TAG.exec(listLine[2].replace(BOARD_DATE, '')) : null
      if (tag && tag[1] !== id) continue
    }
    map.set(hit[1], { done: /^\\s*-\\s*\\[[xX]\\]/.test(line), line })
  }""",
     'health read keys')

edit('dsh/health.js',
     """export async function appendHealthTodos({ boardPath, report, date }) {""",
     """export async function appendHealthTodos({ boardPath, report, date, id = null }) {""",
     'health append signature')

edit('dsh/health.js',
     """    const existing = await readBoardKeys(boardPath)""",
     """    const existing = await readBoardKeys(boardPath, id)""",
     'health append keys')

edit('dsh/health.js',
     """      lines.push(buildHealthLine(rule, date))""",
     """      lines.push(buildHealthLine(rule, date, id))""",
     'health append line')

# ================================================================= 应用
for rel, old, new, label in edits:
    if rel not in cache:
        cache[rel] = read(os.path.join(WB, rel))
    src = cache[rel]
    if old in src:
        cache[rel] = src.replace(old, new, 1)
        print('  patch', label)
    elif new in src:
        print('  skip (already)', label)
    else:
        raise SystemExit('ANCHOR MISS: ' + label)

for rel, body in cache.items():
    write(os.path.join(WB, rel), body)
    print('written', rel)
print('done')
