// 真项目 + 真总工作台只读探针（P5）：确认插件读的是总板、归档读到、体检读数。
// 只读，不写：不 POST，不改 当前交接.md，不往真板上加行。
import assert from 'node:assert/strict'

const PROJECT = 'D:/GitHub_programe/GitHub/Guassion-Process-Experiment-Design'
const HUB = 'D:/GitHub_programe/GitHub/DSH_Workbench'

const routes = []
const ctx = { connection: { fetch: { register: (def) => routes.push(def) } } }
const mod = await import('file:///D:/GitHub_programe/GitHub/dsh-my-project-workbench/dsh/index.js')
mod.apply(ctx, { hubRoot: HUB, root: 'D:/GitHub_programe/GitHub/DSH_Workbench/.probe-data', projectRoot: PROJECT })

const get = async (name) => {
  const found = routes.find((r) => r.path.endsWith('/' + name))
  assert.ok(found, '缺路由 ' + name)
  const res = await found.fetch(new Request('http://local/api/my-project-workbench/' + name))
  const body = await res.json()
  if (body.error) throw new Error(name + ' -> ' + body.error)
  return body
}

const todos = await get('todos')
console.log('[todos] store=' + todos.store + ' projectId=' + todos.projectId)
console.log('[todos] boardPath=' + todos.boardPath)
console.log('[todos] 本项目 ' + todos.todos.length + ' 条：' + todos.todos.map((t) => (t.done ? '[x] ' : '[ ] ') + t.text.slice(0, 24)).join(' | '))
assert.equal(todos.store, 'hub', '待办必须读总板')
assert.equal(todos.projectId, 'gp-experiment', '项目 id 应从 projects.json 反查')
assert.ok(/DSH_Workbench[\\/]boards/i.test(todos.boardPath), 'boardPath 应指向总工作台 boards')
assert.ok(todos.todos.every((t) => !t.text.includes('【')), '正文里不该带项目标签')

const handover = await get('handover')
console.log('[handover] ' + handover.bytes + '/' + handover.limit + ' 字节 · ok=' + handover.ok + ' · 归档 ' + handover.archive.count + ' 份')
assert.ok(handover.archive.count >= 1, '归档应有快照')

const health = await get('health')
console.log('[health] ' + health.status + ' · ' + health.rules.length + ' 条判据：' +
  health.counts.pass + ' 通过 / ' + health.counts.warn + ' 警告 / ' + health.counts.fail + ' 失败')
for (const rule of health.rules) {
  if (rule.status !== 'pass') console.log('   ' + rule.status.padEnd(5) + rule.id + ' — ' + rule.evidence)
}
const boardRule = health.rules.find((r) => r.id === 'board:keys')
assert.ok(boardRule && boardRule.status === 'pass', '待办板键判据应通过（说明新旧键格式都能读）')
console.log('\n探针通过：待办读总板、正文无标签、归档可读、体检键判据 pass。')
