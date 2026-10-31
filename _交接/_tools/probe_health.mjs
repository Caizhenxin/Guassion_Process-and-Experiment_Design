// 只读探针：用真项目跑一遍体检报告（不写任何文件）。
// 跑法：E:\Node\node.exe "D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\_交接\_tools\probe_health.mjs"
const MOD = 'file:///D:/GitHub_programe/GitHub/dsh-my-project-workbench/dsh/'
const { inspectProject } = await import(MOD + 'health.js')
const { inspectHandover } = await import(MOD + 'index.js')

const root = 'D:/GitHub_programe/GitHub/Guassion-Process-Experiment-Design'
const report = await inspectProject({ root, inspectHandover })

console.log('[status] ' + report.status + ' · ' + report.summary)
console.log('[counts] ' + JSON.stringify(report.counts))
console.log('\n一)、逐条：')
for (const rule of report.rules) {
  const mark = rule.status === 'fail' ? 'FAIL' : rule.status === 'warn' ? 'WARN' : 'ok  '
  console.log('  ' + mark + ' ' + rule.id.padEnd(26) + ' scanned=' + String(rule.scanned).padEnd(3) + ' ' + rule.evidence)
}
console.log('\n二)、digest（收工前只看这 5 行）：')
for (const line of report.digest) console.log('  ' + line)
