import io

p = r'D:\GitHub_programe\GitHub\dsh-my-project-workbench\lib\client.js'
s = io.open(p, encoding='utf-8').read()
edits = []

# ① 交接面板挂上体检读数（GET 只读，不写盘）
old1 = '''    function HandoverPanel(props) {
      const store = useApi('handover')'''
new1 = '''    function HandoverPanel(props) {
      const store = useApi('handover')
      const healthStore = useApi('health')'''
edits.append((old1, new1))

# ② 体检按钮：POST 才会写待办板（收工动作）
old2 = '''      const info = store.data || {}'''
new2 = '''      const runHealth = async () => {
        try {
          const result = await postJson('health', {})
          const added = Number(result && result.appended) || 0
          setMsg('体检 ' + (result.status || '') + ' · 新记待办 ' + added + ' 条 · ' + stamp())
          healthStore.reload()
          store.reload()
        } catch (error) {
          setMsg('体检失败：' + errText(error))
        }
      }

      const hdata = healthStore.data || {}
      const hrules = Array.isArray(hdata.rules) ? hdata.rules : []
      const hcounts = hdata.counts || {}
      const healthStatus = hdata.status || (healthStore.loading ? '读' : '未跑')
      const healthCounts = hrules.length
        ? '判据 ' + hrules.length + ' 条 · 通过 ' + (hcounts.pass || 0) +
          ' / 警告 ' + (hcounts.warn || 0) + ' / 失败 ' + (hcounts.fail || 0)
        : healthStore.error
          ? '读取失败：' + healthStore.error
          : '还没有读数'
      const badLines = hrules
        .filter((rule) => rule.status === 'fail' || rule.status === 'warn')
        .map((rule) => (rule.status === 'fail' ? '⛔ ' : '⚠ ') + rule.id + ' — ' + String(rule.detail || ''))
      const healthLines = badLines.length
        ? badLines
        : (Array.isArray(hdata.digest) ? hdata.digest.slice(0, 3) : [])

      const info = store.data || {}'''
edits.append((old2, new2))

# ③ 读数区块放在编辑区下方
old3 = '''            h('span', { className: 'mpw-dim small' }, dirty ? '有未保存改动（Ctrl+Enter 写回）' : '只覆盖这一份，不追加'),
          ),
        ),
      )
    }'''
new3 = '''            h('span', { className: 'mpw-dim small' }, dirty ? '有未保存改动（Ctrl+Enter 写回）' : '只覆盖这一份，不追加'),
          ),
          h(
            'div',
            { className: 'mpw-health' },
            h(
              'div',
              { className: 'mpw-rowacts' },
              h('span', { className: 'mpw-healthchip is-' + healthStatus }, healthStatus + ' · ' + healthCounts),
              h('span', { className: 'mpw-dim small' }, '收工前跑一次：失败判据自动进待办板，同一件只留一行'),
              h('button', { type: 'button', className: 'mpw-chip', onClick: runHealth }, '跑体检并记待办'),
            ),
            healthLines.length
              ? h('ul', { className: 'mpw-healthlist' }, healthLines.map((line, index) => h('li', { key: index }, line)))
              : null,
          ),
        ),
      )
    }'''
edits.append((old3, new3))

# ④ CSS
old4 = "      '.mpw-hint.is-bad{color:var(--mpw-bad)}',"
new4 = """      '.mpw-hint.is-bad{color:var(--mpw-bad)}',
      '.mpw-health{flex:0 0 auto;border-top:1px solid var(--mpw-line);padding-top:6px;margin-top:2px;display:flex;flex-direction:column;gap:4px}',
      '.mpw-healthchip{font-size:11px;font-weight:600;letter-spacing:.02em;color:var(--mpw-dim)}',
      '.mpw-healthchip.is-pass{color:var(--mpw-ok)}',
      '.mpw-healthchip.is-warn{color:var(--mpw-warn)}',
      '.mpw-healthchip.is-fail{color:var(--mpw-bad)}',
      '.mpw-healthlist{margin:0;padding-left:14px;font-size:11px;line-height:1.5;color:var(--mpw-dim);max-height:96px;overflow:auto}',"""
edits.append((old4, new4))

for old, new in edits:
    assert s.count(old) == 1, 'anchor count %d: %s' % (s.count(old), old[:60])
    s = s.replace(old, new)

io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('client health UI applied, lines =', s.count('\n'))
