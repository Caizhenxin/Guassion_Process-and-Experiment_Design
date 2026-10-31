import io, sys

p = r'D:\GitHub_programe\GitHub\dsh-my-project-workbench\dsh\health.js'
s = io.open(p, encoding='utf-8').read()

start_mark = '  // ---------- ② 索引：README 面板表 ↔ 客户端 title ----------'
end_mark = '  // ---------- ③ 索引：README 接口表 ↔ 服务端路由 ----------'
i = s.index(start_mark)
j = s.index(end_mark)

new = '''  // ---------- ② 索引：README 面板表 ↔ 客户端注册的面板 ----------
  // 事实侧取 ALL_PANELS（注册表本身就是代码的声明），标题按「字符串字面量是否出现」判，
  // 不做 id ↔ 中文名的配对：客户端 12 个面板的 title 分散在各组件里，硬配对只会制造误报。
  const panelTable = readTable(readme, '能做什么', ['面板', '内容'])
  const readmeTitles = new Set(panelTable.rows.map((row) => row[0]))
  const panelIds = []
  const panelBlock = clientSrc && /const ALL_PANELS = \\[([^\\]]*)\\]/.exec(clientSrc)
  if (panelBlock) {
    for (const hit of panelBlock[1].matchAll(/'([A-Za-z0-9_-]+)'/g)) panelIds.push(hit[1])
  }
  {
    const missingInCode = [...readmeTitles].filter((title) => !String(clientSrc || '').includes("'" + title + "'"))
    const bad = Boolean(panelTable.error) || readmeTitles.size === 0 || panelIds.length === 0
    const differ = readmeTitles.size !== panelIds.length || missingInCode.length > 0
    push({
      id: 'index:panels',
      group: 'index',
      title: 'README 面板表 ↔ ALL_PANELS / 客户端标题',
      status: bad || differ ? 'fail' : 'pass',
      scanned: readmeTitles.size,
      actual: { parsed: readmeTitles.size, expected: panelIds.length, missingInCode, skipped: panelTable.skipped },
      evidence: bad
        ? '解析失败：' + (panelTable.error || '面板表为空，或客户端没有 ALL_PANELS')
        : differ
          ? 'README ' + readmeTitles.size + ' 行 ↔ ALL_PANELS ' + panelIds.length + ' 个' +
            (missingInCode.length ? '；代码里找不到标题：' + missingInCode.join('、') : '')
          : 'README ' + readmeTitles.size + ' 行 ↔ ALL_PANELS ' + panelIds.length + ' 个，标题全部对得上',
    })
  }

  // ---------- ②b 索引：测试便利表 __test.panels ↔ ALL_PANELS ----------
  // 这张表是 test-client 判断「面板都挂上了没」的依据，漏项等于测试少覆盖，必须报出来。
  {
    const block = clientSrc && /__test = \\{[\\s\\S]*?panels: \\{([\\s\\S]*?)\\}/.exec(clientSrc)
    const keys = block ? [...block[1].matchAll(/^\\s+([A-Za-z0-9_]+Panel),$/gm)].length : 0
    const bad = !block || keys === 0
    push({
      id: 'index:testpanels',
      group: 'index',
      title: '__test.panels ↔ ALL_PANELS（测试覆盖的面板）',
      status: bad || keys !== panelIds.length ? 'fail' : 'pass',
      scanned: keys,
      actual: { parsed: keys, expected: panelIds.length },
      evidence: bad
        ? '解析失败：客户端没有 __test.panels'
        : keys === panelIds.length
          ? '__test.panels ' + keys + ' 项 ↔ ALL_PANELS ' + panelIds.length + ' 项'
          : '__test.panels 少 ' + (panelIds.length - keys) + ' 项（' + keys + ' / ' + panelIds.length + '），测试没覆盖全部面板',
    })
  }

'''

s = s[:i] + new + s[j:]

# counts 规则改用 panelIds
s = s.replace("else if (Number(panelCount[1]) !== codeTitles.size) problems.push('写 ' + panelCount[1] + ' 个、实测 ' + codeTitles.size + ' 个')",
              "else if (Number(panelCount[1]) !== panelIds.length) problems.push('写 ' + panelCount[1] + ' 个、实测 ' + panelIds.length + ' 个')")
s = s.replace("actual: { panels: codeTitles.size, routes: codeRoutes.size },",
              "actual: { panels: panelIds.length, routes: codeRoutes.size },")
s = s.replace("evidence: problems.length ? problems.join('；') : '面板 ' + codeTitles.size + '、接口 ' + codeRoutes.size + '，与正文一致',",
              "evidence: problems.length ? problems.join('；') : '面板 ' + panelIds.length + '、接口 ' + codeRoutes.size + '，与正文一致',")

assert 'codeTitles' not in s, 'still references codeTitles'
io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('rewritten; bytes=', len(s.encode('utf-8')))
