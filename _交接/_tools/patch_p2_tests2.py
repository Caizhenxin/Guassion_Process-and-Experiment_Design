import io

p = r'D:\GitHub_programe\GitHub\dsh-my-project-workbench\_evidence\test-health.mjs'
s = io.open(p, encoding='utf-8').read()

old_import = '''import {
  HEALTH_KEY,
  appendHealthTodos,
  buildHealthLine,
  inspectProject,
  readBoardKeys,
} from '../dsh/health.js\''''
assert old_import in s, 'import anchor'
new_import = '''import {
  HEALTH_KEY,
  SIZE_TARGETS,
  appendHealthTodos,
  buildHealthLine,
  inspectProject,
  readBoardKeys,
} from '../dsh/health.js'

// 阈值只有一处出处：反例按 SIZE_TARGETS 现算，改红线时测试自动跟着走。
const CLIENT_TARGET = SIZE_TARGETS.find((target) => target.rel.endsWith('client.js'))'''
s = s.replace(old_import, new_import)

old_big = '''function bigClient() {
  // 只有 size 一条判据该红：面板/数字索引必须自洽，否则追加行数不可预期。
  return clientSource(['面板甲', '面板乙']) + 'x\\n'.repeat(2001)
}'''
assert old_big in s, 'bigClient anchor'
new_big = '''function linesOf(source) {
  return (String(source).match(/\\n/g) || []).length
}

function sizedClient(extraLines) {
  // 只有 size 一条判据该红：面板/数字索引必须自洽，否则追加行数不可预期。
  const head = clientSource(['面板甲', '面板乙'])
  const fill = Math.max(0, extraLines - linesOf(head))
  return head + 'x\\n'.repeat(fill)
}

function bigClient() {
  return sizedClient(CLIENT_TARGET.lines + 1)
}'''
s = s.replace(old_big, new_big)

old_case = '''{
  const root = await fresh({ 'lib/client.js': 'x\\n'.repeat(2000) })
  const { rule } = await ruleOf(root, 'size:lib/client.js')
  check('正好 2000 行 → warn（到线不等于超线）', rule.status === 'warn', rule && rule.status)
}'''
assert old_case in s, 'boundary anchor'
new_case = '''{
  const root = await fresh({ 'lib/client.js': sizedClient(CLIENT_TARGET.lines) })
  const { rule } = await ruleOf(root, 'size:lib/client.js')
  check('正好 ' + CLIENT_TARGET.lines + ' 行 → warn（到线不等于超线）', rule.status === 'warn', rule && rule.status)
  check('实测行数等于上限', rule.actual.lines === CLIENT_TARGET.lines, String(rule.actual.lines))
}'''
s = s.replace(old_case, new_case)

s = s.replace("check('2011 行 → fail', rule.status === 'fail', rule && rule.status)",
              "check('超过上限 1 行 → fail', rule.status === 'fail', rule && rule.status)")
s = s.replace("check('带实测行数', rule.actual.lines > 2000, String(rule.actual.lines))",
              "check('带实测行数', rule.actual.lines === CLIENT_TARGET.lines + 1, String(rule.actual.lines))")

io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('ok')
