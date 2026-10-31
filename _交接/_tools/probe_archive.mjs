// 真项目探针（阶段 A）：手动存一次快照，确认归档真的落到总工作台。
// 只读项目交接文件 + 往 archive 里写一份快照，不改 当前交接.md 本体。
import assert from 'node:assert/strict'
import { readdir, readFile, stat } from 'node:fs/promises'
import { join } from 'node:path'

const PROJECT = 'D:/GitHub_programe/GitHub/Guassion-Process-Experiment-Design'
const HUB = 'D:/GitHub_programe/GitHub/DSH_Workbench'

const routes = []
const ctx = { connection: { fetch: { register: (def) => routes.push(def) } } }
const mod = await import('file:///D:/GitHub_programe/GitHub/dsh-my-project-workbench/dsh/index.js')
mod.apply(ctx, { hubRoot: HUB, root: join(HUB, '.probe-data'), projectRoot: PROJECT })

const call = async (name, payload) => {
  const found = routes.find((r) => r.path.endsWith('/' + name))
  assert.ok(found, '缺路由 ' + name)
  const res = await found.fetch(
    new Request('http://local/api/my-project-workbench/' + name, payload === undefined
      ? {}
      : { method: 'POST', body: JSON.stringify(payload), headers: { 'content-type': 'application/json' } }),
  )
  const body = await res.json()
  if (body.error) throw new Error(name + ' -> ' + body.error)
  return body
}

const before = await call('handover')
console.log('[before] 归档', before.archive.count, '份 · id=' + before.archive.id, '(' + before.archive.idSource + ')')
console.log('[before] 目录', before.archive.dir)
const handoverBefore = await readFile(join(PROJECT, '_交接', '当前交接.md'), 'utf8')
const stampBefore = (await stat(join(PROJECT, '_交接', '当前交接.md'))).mtimeMs

const saved = await call('snapshot', {})
console.log('[snapshot]', saved.written ? '已存 ' + saved.name : '跳过：' + saved.reason, '· 现有', saved.archive.count, '份')
assert.equal(saved.written, true, '应该有可归档的内容')
assert.match(String(saved.name), /^交接-\d{8}-\d{6}(-\d+)?\.md$/, '快照命名不对：' + saved.name)
const after = await call('handover')
assert.equal(after.archive.count, saved.archive.count, '归档计数应一致')

const files = (await readdir(join(HUB, 'archive', before.archive.id))).filter((n) => n.endsWith('.md'))
const target = join(HUB, 'archive', before.archive.id, saved.name)
const body = await readFile(target, 'utf8')
console.log('[archive] 目录里', files.length, '份快照；最新一份', saved.name, body.length, '字节')
assert.ok(body.includes('§〇'), '快照内容应含 §〇')
assert.equal(body, handoverBefore, '快照内容应当与当前交接逐字一致')

const handoverAfter = await readFile(join(PROJECT, '_交接', '当前交接.md'), 'utf8')
assert.equal(handoverAfter, handoverBefore, '存快照不许改动 当前交接.md')
assert.equal((await stat(join(PROJECT, '_交接', '当前交接.md'))).mtimeMs, stampBefore, '当前交接.md 修改时间不许变')

const health = await call('health')
const archiveRule = health.rules.find((rule) => rule.id === 'handover:archive')
console.log('[health]', health.status, '· ' + health.counts.pass + ' 通过 / ' + health.counts.warn + ' 警告 / ' + health.counts.fail + ' 失败')
console.log('[health] handover:archive =', archiveRule.status, '·', archiveRule.evidence)
assert.equal(archiveRule.status, 'pass', '真实项目归档判据应为 pass')
console.log('\n探针通过：快照落盘、内容一致、原文件未动、体检读到归档。')
