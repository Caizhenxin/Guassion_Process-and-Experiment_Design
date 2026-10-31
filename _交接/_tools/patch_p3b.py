import io, json, os

WB = r'D:\GitHub_programe\GitHub\dsh-my-project-workbench'

def read(p):
    return io.open(p, encoding='utf-8').read()

def write(p, s):
    io.open(p, 'w', encoding='utf-8', newline='\n').write(s)

def sub(s, old, new, label):
    assert s.count(old) == 1, 'anchor %s: %d' % (label, s.count(old))
    return s.replace(old, new)

# ---------------- ① scenes.json 加第 4 个场景：只改配置，不改代码 ----------------
p = os.path.join(WB, 'scenes.json')
config = json.loads(read(p))
if not any(scene['id'] == 'wrap' for scene in config['scenes']):
    config['scenes'].append({
        "id": "wrap",
        "name": "收工",
        "icon": "✓",
        "rows": [{
            "g": 1,
            "columns": [
                {"w": 7, "panels": [{"id": "handover", "g": 1}]},
                {"w": 5, "panels": [{"id": "todos", "g": 0}, {"id": "notes", "g": 1}]},
            ],
        }],
    })
write(p, json.dumps(config, ensure_ascii=False, indent=2) + '\n')

# ---------------- ② health.js：README 场景表 ↔ 生效配置 ----------------
p = os.path.join(WB, 'dsh', 'health.js')
s = read(p)

anchor = "  const counts = { pass: 0, warn: 0, fail: 0, skipped: 0 }"
rule = '''  // ---------- ⑧ 场景表：README 写的场景 ↔ 生效配置 ----------
  // 加一个场景只改 scenes.json 是合法用法，但 README 那张表会悄悄变旧 ——
  // 这条判据就是为了「只改配置、忘了改文档」时有人喊一声。
  {
    const config = readScenes(base)
    const configured = (config.scenes || []).map((scene) => scene.name)
    const readmeText = (await read('README.md')) || ''
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
    }
    const missing = configured.filter((name) => !names.includes(name))
    const extra = names.filter((name) => !configured.includes(name))
    push({
      id: 'config:scenes-readme',
      group: 'config',
      title: 'README 场景表 ↔ 生效场景配置（加了场景要回来改表）',
      status: !names.length ? 'warn' : missing.length || extra.length ? 'fail' : 'pass',
      scanned: names.length,
      actual: { readme: names.length, configured: configured.length, missing, extra },
      evidence: !names.length
        ? 'README 里没有场景表：新增场景时没人会发现漏更新'
        : missing.length || extra.length
          ? '对不上：' +
            (missing.length ? 'README 缺 ' + missing.join('、') : '') +
            (missing.length && extra.length ? '；' : '') +
            (extra.length ? 'README 多 ' + extra.join('、') : '')
          : names.length + ' 个场景两边一致',
    })
  }

'''
s = sub(s, anchor, rule + anchor, 'scenes-readme rule')
write(p, s)

# ---------------- ③ README：场景表加「收工」行 + 标题不再写死三个 ----------------
p = os.path.join(WB, 'README.md')
s = read(p)

s = sub(s, '## V2：三个场景 + 弹性分栏',
        '## V2：场景化面板 + 弹性分栏（场景清单以 `scenes.json` 为准，这里是当前生效的 4 个）', 'readme v2 head')

row = '| 收工 | 左 7：当前交接（撑满）／右 5：待办（自然高）+ 便利贴（撑满） | 收工前：覆盖写 §〇、勾掉做完的、把想法先记下来 |\n'
anchor_row = '| 写作与汇报 | 左栏 3：便利贴 + 待办／右栏 9：AI 对话（最大一块） | 边聊边写，AI 面板占最大一块 |\n'
s = sub(s, anchor_row, anchor_row + row, 'readme v2 row')
write(p, s)
print('p3b applied')
