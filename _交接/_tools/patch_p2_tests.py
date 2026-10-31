import io

p = r'D:\GitHub_programe\GitHub\dsh-my-project-workbench\_evidence\test-health.mjs'
s = io.open(p, encoding='utf-8').read()

old_client = '''function clientSource(titles) {
  const ids = titles.map((_, index) => "'p" + (index + 1) + "'")
  const rows = ['const ALL_PANELS = [' + ids.join(', ') + ']', '']
  for (const title of titles) rows.push("  title: '" + title + "',")
  return rows.join('\\n') + '\\n'
}'''
assert old_client in s, 'clientSource anchor'

new_client = '''function clientSource(titles, testKeys) {
  const ids = titles.map((_, index) => "'p" + (index + 1) + "'")
  const rows = ['const ALL_PANELS = [' + ids.join(', ') + ']', '']
  for (const title of titles) rows.push("  title: '" + title + "',")
  const keys = testKeys || titles.map((_, index) => 'P' + (index + 1) + 'Panel')
  rows.push('', 'const __test = {', '  panels: {')
  for (const key of keys) rows.push('    ' + key + ',')
  rows.push('  },', '}', '')
  return rows.join('\\n')
}'''
s = s.replace(old_client, new_client)

s = s.replace("check('diff 指向 README 多余项', rule.actual.diff.onlyLeft.includes('面板乙'), JSON.stringify(rule.actual.diff))",
              "check('报出「代码里找不到」的标题', rule.actual.missingInCode.includes('面板乙'), JSON.stringify(rule.actual.missingInCode))")
s = s.replace("check('diff 指向代码多余项', rule.actual.diff.onlyRight.includes('面板丙'), JSON.stringify(rule.actual.diff))",
              "check('ALL_PANELS 比 README 多一个', rule.actual.expected === 3 && rule.actual.parsed === 2, JSON.stringify(rule.actual))")

anchor = "// ---------- ③ 索引：接口表 ----------"
extra = '''// ---------- ②b 测试便利表 ----------
console.log('\\n[索引-测试面板] __test.panels 漏项必须红')
{
  const root = await fresh({ 'lib/client.js': clientSource(['面板甲', '面板乙'], ['P1Panel']) })
  const { rule } = await ruleOf(root, 'index:testpanels')
  check('__test.panels 少一项 → fail', rule.status === 'fail', rule && rule.evidence)
  check('报出少几项', rule.evidence.includes('少 1 项'), rule && rule.evidence)
}

// ---------- ③ 索引：接口表 ----------'''
assert anchor in s
s = s.replace(anchor, extra)

io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('ok bytes=', len(s.encode('utf-8')))
