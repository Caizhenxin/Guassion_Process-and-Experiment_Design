import io, os

WB = r'D:\GitHub_programe\GitHub\dsh-my-project-workbench'
p = os.path.join(WB, 'dsh', 'health.js')
s = io.open(p, encoding='utf-8').read()

def sub(s, old, new, label):
    assert s.count(old) == 1, 'anchor %s: %d' % (label, s.count(old))
    return s.replace(old, new)

# ① 导入场景配置（无循环：scenes.js 不引 health.js）
s = sub(s, "import { fileURLToPath } from 'node:url'",
        "import { fileURLToPath } from 'node:url'\n\nimport { readScenes } from './scenes.js'", 'import')

# ② 新模块也给一条体量红线
s = sub(s, "  { rel: vector('dsh', 'health.js'), lines: 620, bytes: 32 * 1024 },",
        "  { rel: vector('dsh', 'health.js'), lines: 700, bytes: 36 * 1024 },\n"
        "  { rel: vector('dsh', 'scenes.js'), lines: 340, bytes: 18 * 1024 },", 'size target')

# ③ config:scenes 判据：插在 counts 汇总之前（待办板判据之后）
anchor = "  const counts = { pass: 0, warn: 0, fail: 0, skipped: 0 }"
rule = '''  // ---------- ⑦ 场景配置：坏文件退回默认，但必须报出来 ----------
  // 场景配置在插件的 selfRoot（base），不在项目里 —— 它描述的是「工作台长什么样」。
  {
    const config = readScenes(base)
    const problems = config.problems || []
    const drift = config.drift || []
    const scenes = config.scenes || []
    push({
      id: 'config:scenes',
      group: 'config',
      title: 'scenes.json 可解析、面板 id 合法、同一场景不重复',
      status: problems.length ? 'fail' : config.present ? 'pass' : 'warn',
      scanned: scenes.length,
      actual: { source: config.source, scenes: scenes.length, drift, problems },
      evidence: problems.length
        ? '配置有问题（已退回内置默认）：' + problems.slice(0, 2).join('；')
        : config.present
          ? scenes.length + ' 个场景来自 scenes.json' +
            (drift.length ? '，比内置默认多出面板：' + drift.join('、') : '')
          : '没有 scenes.json，用的是内置默认版式（想自定义版式就建一份）',
    })
  }

'''
s = sub(s, anchor, rule + anchor, 'config rule')
io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('health part done; lines =', s.count('\n'))
