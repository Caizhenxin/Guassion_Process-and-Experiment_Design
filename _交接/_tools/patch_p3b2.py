import io, os

p = r'D:\GitHub_programe\GitHub\dsh-my-project-workbench\dsh\health.js'
s = io.open(p, encoding='utf-8').read()

old = """    const readmeText = (await read('README.md')) || ''
    const names = []
    let inTable = false
    for (const line of String(readmeText).split(/\\r?\\n/)) {
      const isRow = /^\\|\\s*\\S/.test(line)
      if (/^\\|\\s*场景\\s*\\|/.test(line)) {
        inTable = true
        continue
      }
      if (!inTable) continue
      if (!isRow) {
        inTable = false
        continue
      }
      if (/^\\|\\s*-{2,}/.test(line)) continue
      const name = line.split('|')[1].trim()
      if (name) names.push(name)
    }"""

new = """    // 复用同一条表格解析：手写解析会漏掉「表头换写法」这类漂移。
    const readmeText = (await readBase('README.md')) || ''
    const sceneTable = readTable(readmeText, 'V2：', ['场景'])
    const names = sceneTable.rows.map((row) => row[0]).filter(Boolean)"""

assert s.count(old) == 1, 'anchor %d' % s.count(old)
s = s.replace(old, new)
io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('rule simplified')
