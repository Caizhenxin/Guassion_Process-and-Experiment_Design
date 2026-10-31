/**
 * 真实落盘探针：不动任何文件，只把 handover / todos 两条路由对着真项目跑一遍，
 * 确认「§〇 判据看的是项目里那份文件」「待办读的是项目内待办板」。
 *
 * 跑法：E:\Node\node.exe _交接\_tools\probe_handover.mjs
 */
import { mkdtemp } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const mod = await import('file:///D:/GitHub_programe/GitHub/dsh-my-project-workbench/dsh/index.js')
const routes = []
const ctx = { connection: { fetch: { register: (def) => routes.push(def) } } }

const dataRoot = await mkdtemp(join(tmpdir(), 'mpw-probe-'))
mod.apply(ctx, {
  root: dataRoot,
  projectRoot: 'D:/GitHub_programe/GitHub/Guassion-Process-Experiment-Design',
})

async function get(name) {
  const route = routes.find((item) => item.path.endsWith('/' + name))
  const res = await route.fetch(new Request('http://local/api/my-project-workbench/' + name))
  return res.json()
}

const handover = await get('handover')
console.log('[handover] path     :', handover.path)
console.log('[handover] exists   :', handover.exists)
console.log('[handover] bytes    :', handover.bytes, '/', handover.limit)
console.log('[handover] ok       :', handover.ok)
console.log('[handover] missing  :', JSON.stringify(handover.missing))
console.log('[handover] over     :', handover.over)
console.log('[handover] 前 3 行  :', String(handover.text).split('\n').slice(0, 3).join(' ⏎ '))

const todos = await get('todos')
console.log('\n[todos] store      :', todos.store)
console.log('[todos] boardPath  :', todos.boardPath)
console.log('[todos] 条数       :', todos.todos.length)
for (const item of todos.todos) console.log('        ', item.done ? '[x]' : '[ ]', item.at, item.text)

const bad = []
if (!handover.ok) bad.push('§〇 判据未通过：' + (handover.empty ? '空文件' : handover.missing.join(',')))
if (todos.store !== 'board') bad.push('待办未落在项目内待办板')
if (!todos.todos.length) bad.push('待办板解析出 0 条')

console.log('\n' + (bad.length ? '⚠ ' + bad.join(' / ') : '✓ 交接层已在真项目上落盘可用'))
process.exit(bad.length ? 1 : 0)
