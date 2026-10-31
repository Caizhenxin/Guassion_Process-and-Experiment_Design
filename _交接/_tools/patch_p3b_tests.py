import io

p = r'D:\GitHub_programe\GitHub\dsh-my-project-workbench\_evidence\test-health.mjs'
s = io.open(p, encoding='utf-8').read()

def sub(s, old, new, label):
    assert s.count(old) == 1, 'anchor %s: %d' % (label, s.count(old))
    return s.replace(old, new)

# ① readmeSource 支持场景表
s = sub(s, "  const tests = opts.tests || ['test-one.mjs']",
        "  const tests = opts.tests || ['test-one.mjs']\n"
        "  const scenes = opts.scenes || ['项目总览', '文件与产物', '写作与汇报']", 'readmeSource opt')

s = sub(s, "  rows.push('', '## 服务端接口（`/api/fixture/`）', '', '| 接口 | 说明 |', '| --- | --- |')",
        "  rows.push('', '## V2：场景化面板 + 弹性分栏', '', '| 场景 | 面板与版式 | 适合什么时候用 |', '| --- | --- | --- |')\n"
        "  for (const scene of scenes) rows.push('| ' + scene + ' | 示例 | 示例 |')\n"
        "  rows.push('', '## 服务端接口（`/api/fixture/`）', '', '| 接口 | 说明 |', '| --- | --- |')", 'readmeSource table')

# ② 两条反例：README 场景表和生效配置必须互相对得上
anchor = "check('写「3 个面板」实际 2 个 → fail'"
cases = '''{
  const root = await fresh({ 'README.md': readmeSource({ scenes: ['甲场景'] }) })
  const { rule } = await ruleOf(root, 'config:scenes-readme')
  check('README 写了配置里没有的场景 → fail', rule.status === 'fail', rule && rule.status)
}
{
  const root = await fresh({ 'README.md': readmeSource({ scenes: ['项目总览', '文件与产物', '写作与汇报'] }) })
  const { rule } = await ruleOf(root, 'config:scenes-readme')
  check('README 场景表与内置默认一致 → pass', rule.status === 'pass', rule && rule.status)
}
{
  const root = await fresh({ 'README.md': readmeSource({ scenes: ['项目总览'] }) })
  const { rule } = await ruleOf(root, 'config:scenes-readme')
  check('README 少写两个场景 → fail（漏更新要被抓）', rule.status === 'fail', rule && rule.status)
}
'''
s = sub(s, anchor, cases + anchor, 'readme cases')

io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('ok')
