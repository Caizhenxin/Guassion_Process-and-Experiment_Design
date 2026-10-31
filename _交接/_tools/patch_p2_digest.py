import io

p = r'D:\GitHub_programe\GitHub\dsh-my-project-workbench\dsh\health.js'
s = io.open(p, encoding='utf-8').read()

old = """  const digest = trouble
    .sort((left, right) => (left.status === right.status ? 0 : left.status === 'fail' ? -1 : 1))
    .slice(0, 5)
    .map((rule) => (rule.status === 'fail' ? '⛔ ' : '⚠ ') + rule.evidence)"""
new = """  // 全绿时 digest 不能是空的：空行会让人以为「没跑」，也违反「收工前只看这几行」。
  const digest = trouble.length
    ? trouble
        .sort((left, right) => (left.status === right.status ? 0 : left.status === 'fail' ? -1 : 1))
        .slice(0, 5)
        .map((rule) => (rule.status === 'fail' ? '⛔ ' : '⚠ ') + rule.evidence)
    : ['全绿：' + rules.length + ' 条判据全部通过 · ' + new Date(now).toISOString().slice(0, 16).replace('T', ' ') +
       '（UTC）· 收工前只读这一行就可以']"""
assert s.count(old) == 1
s = s.replace(old, new)
io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('digest green line added')
