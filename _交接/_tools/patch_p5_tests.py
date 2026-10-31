"""P5 自测改造：test-server 改到临时总工作台，另加 test-board 纯函数测试。"""
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


REL = '_evidence/test-server.mjs'

edit(REL,
     "import { readFileSync, rmSync, writeFileSync } from 'node:fs'\nimport { mkdtemp } from 'node:fs/promises'",
     "import { readFileSync } from 'node:fs'\nimport { mkdir, mkdtemp, writeFile } from 'node:fs/promises'",
     'ts imports')

edit(REL,
     """const PROJECT = 'D:/GitHub_programe/GitHub/Guassion-Process-Experiment-Design'
const BOARD = join(PROJECT, '_交接', '待办板.md')

// 待办现在落在**项目内**的待办板，所以自测的 POST 会写进真项目的数据。
// 跑之前拍快照、退出时无论成败都还原 —— 自测不许改用户的真待办。
const boardSnapshot = (() => {
  try {
    return readFileSync(BOARD, 'utf8')
  } catch {
    return null
  }
})()
process.on('exit', () => {
  try {
    if (boardSnapshot == null) rmSync(BOARD, { force: true })
    else writeFileSync(BOARD, boardSnapshot, 'utf8')
  } catch (error) {
    console.error('待办板还原失败：' + error.message)
  }
})

const dataRoot = await mkdtemp(join(tmpdir(), 'mpw-data-'))
// 归档落总工作台：自测必须指向临时目录，绝不许往真 DSH_Workbench 里写快照。
const hubRoot = await mkdtemp(join(tmpdir(), 'mpw-hub-'))""",
     """const PROJECT = 'D:/GitHub_programe/GitHub/Guassion-Process-Experiment-Design'

// 待办板现在只有一处：总工作台的 boards/待办板.md（每行带【项目id】）。
// 自测必须在**临时总工作台**里跑 —— 否则 POST 会往真板子上写假待办，把机主的活冲掉。
// （上一版靠「拍快照 + 退出还原」兜底，那是在补救「写错了地方」，不如一开始就别写那儿。）
const dataRoot = await mkdtemp(join(tmpdir(), 'mpw-data-'))
const hubRoot = await mkdtemp(join(tmpdir(), 'mpw-hub-'))
const BOARD = join(hubRoot, 'boards', '待办板.md')
const OTHER_LINE = '- [ ] 2026-10-28 【other-project】别人的活，一个字都不许动'
const NOTE_LINE = '> 人写的说明：这段必须原样保留。'
await mkdir(join(hubRoot, 'boards'), { recursive: true })
await writeFile(
  BOARD,
  '# 待办板（夹具）\\n\\n' + NOTE_LINE + '\\n\\n## 进行中\\n\\n' + OTHER_LINE + '\\n\\n## 已做\\n',
  'utf8',
)
await writeFile(
  join(hubRoot, 'projects.json'),
  JSON.stringify({ projects: [{ id: 'gp-experiment', root: PROJECT }] }),
  'utf8',
)""",
     'ts hub fixture')

edit(REL,
     """await post('todos', { todos: [{ id: 't1', text: '整理第三阶段的图表', done: false }] })
const todos = await get('todos')
assert.equal(todos.todos.length, 1)
const toggled = await post('todos', { todos: [{ id: 't1', text: '整理第三阶段的图表', done: true }] })
assert.equal(toggled.todos[0].done, true)
console.log('[todos] 勾选状态已持久化')""",
     """const posted = await post('todos', { todos: [{ id: 't1', text: '整理第三阶段的图表', done: false }] })
assert.equal(posted.store, 'hub', '总工作台有待办板时必须写总板，不许再写项目内那份作废的')
assert.equal(posted.projectId, 'gp-experiment', '项目 id 应从 projects.json 的 root 反查')
assert.equal(posted.todos.length, 1)
assert.equal(posted.todos[0].text, '整理第三阶段的图表', '读回来的正文不该带【id】标签')
const toggled = await post('todos', { todos: [{ id: 't1', text: '整理第三阶段的图表', done: true }] })
assert.equal(toggled.todos[0].done, true)
const boardAfterTodo = readFileSync(BOARD, 'utf8')
assert.ok(
  boardAfterTodo.includes('【gp-experiment】整理第三阶段的图表') && boardAfterTodo.includes('- [x] '),
  '勾选要写回总板、带项目标签、且保留 [x]',
)
assert.ok(boardAfterTodo.includes(OTHER_LINE), '别的项目的行一个字都不许动')
assert.ok(boardAfterTodo.includes(NOTE_LINE), '人写在列表之外的说明不许被吃掉')
assert.equal(
  boardAfterTodo.split(/\\r?\\n/).filter((line) => line.includes('【gp-experiment】')).length,
  1,
  '本项目同一条待办只许有一行（保存不许重复追加）',
)
console.log('[todos] 写总板 + 项目标签 + 别人的行与说明原样保留')""",
     'ts todos')

edit(REL,
     """console.log('[health POST] 首次追加', firstAppend.todo.appended, '行；第二次', secondAppend.todo.appended, '行 · 跳过', secondAppend.todo.skipped.length)""",
     """if (firstAppend.todo.appended > 0) {
  const afterAppend = readFileSync(BOARD, 'utf8')
  assert.ok(
    afterAppend.includes('【gp-experiment】⛔') || afterAppend.includes('【gp-experiment】⚠'),
    '体检追加的机器行必须带项目标签（否则总板上分不清是谁的）',
  )
}
console.log('[health POST] 首次追加', firstAppend.todo.appended, '行；第二次', secondAppend.todo.appended, '行 · 跳过', secondAppend.todo.skipped.length)""",
     'ts health tag')

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
