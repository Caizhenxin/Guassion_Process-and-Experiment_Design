import io, json, os

WB = r'D:\GitHub_programe\GitHub\dsh-my-project-workbench'

def read(p):
    return io.open(p, encoding='utf-8').read()

def write(p, s, crlf=False):
    io.open(p, 'w', encoding='utf-8', newline='\r\n' if crlf else '\n').write(s)

def sub(s, old, new, label):
    assert s.count(old) == 1, 'anchor %s: count=%d' % (label, s.count(old))
    return s.replace(old, new)

# ---------------- ① scenes.js：补 fs / path 导入 ----------------
p = os.path.join(WB, 'dsh', 'scenes.js')
s = read(p)
s = sub(s, "export const SCENES_REL = 'scenes.json'",
        "import { existsSync, readFileSync } from 'node:fs'\n"
        "import { join } from 'node:path'\n\n"
        "export const SCENES_REL = 'scenes.json'", 'scenes imports')
write(p, s)

# ---------------- ② scenes.json（覆盖文件，先与内置默认一致） ----------------
scenes = {
    "version": 1,
    "note": "工作台版式覆盖文件。改这里不需要动代码；id 必须是 README 面板表里的 id。解析失败会自动退回内置默认并报出来。",
    "scenes": [
        {"id": "overview", "name": "项目总览", "icon": "◎", "rows": [
            {"g": 1.25, "columns": [
                {"w": 7, "panels": [{"id": "kpi", "g": 0}, {"id": "handover", "g": 1}, {"id": "milestones", "g": 1}]},
                {"w": 5, "panels": [{"id": "lastWork", "g": 0}, {"id": "notes", "g": 1}, {"id": "todos", "g": 0}]},
            ]},
            {"g": 1, "columns": [{"w": 1, "panels": [{"id": "arch", "g": 1}]}]},
        ]},
        {"id": "files", "name": "文件与产物", "icon": "▤", "rows": [
            {"g": 1, "columns": [
                {"w": 4, "panels": [{"id": "files", "g": 1}]},
                {"w": 8, "panels": [{"id": "preview", "g": 1}, {"id": "gallery", "g": 1}]},
            ]},
        ]},
        {"id": "work", "name": "写作与汇报", "icon": "✎", "rows": [
            {"g": 1, "columns": [
                {"w": 3, "panels": [{"id": "links", "g": 0}, {"id": "notes", "g": 1}, {"id": "todos", "g": 0}]},
                {"w": 9, "panels": [{"id": "chat", "g": 1}]},
            ]},
        ]},
    ],
}
write(os.path.join(WB, 'scenes.json'), json.dumps(scenes, ensure_ascii=False, indent=2) + '\n')

# ---------------- ③ index.js：scenes 路由 ----------------
p = os.path.join(WB, 'dsh', 'index.js')
s = read(p)
s = sub(s, "import { appendHealthTodos, inspectProject } from './health.js'",
        "import { WORKBENCH_ROOT, appendHealthTodos, inspectProject } from './health.js'\n"
        "import { readScenes, scenesSummary } from './scenes.js'", 'index import')

route = '''  // 场景配置（P3）：版式的唯一出处是插件根目录的 scenes.json。
  // GET 只读 —— 配置只许用编辑器改，不给面板写入口：写坏了版式会「看起来正常」却少一块。
  // 解析失败退回内置默认，但把问题原文一起交回去（客户端顶栏会提示）。
  ctx.connection.fetch.register({
    path: PREFIX + 'scenes',
    methods: ['GET'],
    requestBody: 'buffered',
    async fetch() {
      try {
        const config = readScenes(WORKBENCH_ROOT)
        return ok(Object.assign({ ok: true }, config, { summary: scenesSummary(config) }))
      } catch (error) {
        return fail(error)
      }
    },
  })

'''
s = sub(s, "  // 体检（P2）：GET 只读；只有 POST {append:true} 才写待办板", route + "  // 体检（P2）：GET 只读；只有 POST {append:true} 才写待办板", 'index route')
write(p, s)

# ---------------- ④ client.js ----------------
p = os.path.join(WB, 'lib', 'client.js')
s = read(p)

s = sub(s, "    const SCENES = [", "    let SCENES = [", 'client let')
s = sub(s, "'kpi', 'handover', 'lastWork', 'milestones', 'arch', 'files', 'preview', 'gallery', 'notes', 'todos', 'links', 'chat'",
        "'kpi', 'handover', 'lastWork', 'milestones', 'arch', 'files', 'preview', 'gallery', 'notes', 'todos', 'links', 'chat'", 'noop')

helper = '''    // 版式来自 scenes.json（GET /scenes）。这里再做一遍校验：服务端坏了、或版本旧了，
    // 也不能让未知 id 走到 nodeFor —— 那里以前的兜底是把未知 id 渲染成 AI 对话面板。
    // 任何一处不合法就整份退回内置默认：半份配置比整份默认更难查。
    function applySceneConfig(payload) {
      const reject = { applied: false, scenes: SCENES }
      if (!payload || payload.source !== 'file' || !payload.ok) return reject
      const list = payload.scenes
      if (!Array.isArray(list) || !list.length) return reject
      const safe = []
      for (const scene of list) {
        if (!scene || typeof scene.id !== 'string' || !scene.id) return reject
        const rows = []
        const seen = new Set()
        for (const row of scene.rows || []) {
          const columns = []
          for (const column of (row && row.columns) || []) {
            const panels = []
            for (const panel of (column && column.panels) || []) {
              const id = panel && panel.id
              if (!ALL_PANELS.includes(id) || seen.has(id)) return reject
              seen.add(id)
              panels.push({ id: id, g: Number(panel.g) || 0 })
            }
            if (panels.length) columns.push({ w: Number(column.w) || 1, panels: panels })
          }
          if (columns.length) rows.push({ g: Number(row.g) || 1, columns: columns })
        }
        if (!rows.length || !seen.size) return reject
        safe.push({ id: scene.id, name: String(scene.name || scene.id), icon: String(scene.icon || '◎'), rows: rows })
      }
      return { applied: true, scenes: safe }
    }

'''
s = sub(s, "    function clampTabTarget(target, dragIsPinned, fixedCount) {", helper + "    function clampTabTarget(target, dragIsPinned, fixedCount) {", 'client helper')

effects = '''
      // 版式来自 scenes.json：拿到后整体替换 SCENES，并按新场景集重算标签顺序。
      // 拉不到／校验不过就继续用内置兜底，顶栏提示一句 —— 静默退回默认比报错更难查。
      const [scenesRev, setScenesRev] = useState(0)
      const scenesTried = useRef(false)
      useEffect(() => {
        if (scenesTried.current) return
        scenesTried.current = true
        getJson('scenes')
          .then((payload) => {
            const result = applySceneConfig(payload)
            if (result.applied) {
              SCENES = result.scenes
              setScenesRev((value) => value + 1)
            }
            if (payload && Array.isArray(payload.problems) && payload.problems.length) {
              setBanner('场景配置有问题，已用内置默认：' + payload.problems[0])
            }
          })
          .catch(() => {})
      }, [])

      useEffect(() => {
        if (!scenesRev) return
        const ids = SCENES.map((scene) => scene.id)
        setSceneId((current) => (ids.includes(current) ? current : ids[0]))
        setOrder(() => {
          const saved = loadJson('sceneOrder', null)
          if (!Array.isArray(saved)) return ids
          const kept = saved.filter((id) => ids.includes(id))
          return kept.concat(ids.filter((id) => !kept.includes(id)))
        })
      }, [scenesRev])
'''
s = sub(s, "      const filesJump = useState({ path: '', rev: 0 })[0]",
        "      const filesJump = useState({ path: '', rev: 0 })[0]", 'noop2') if False else s
anchor = "      const [filesJump, setFilesJump] = useState({ path: '', rev: 0 })\n"
s = sub(s, anchor, anchor + effects, 'client effects')

s = sub(s, "        return h(ChatPanel, Object.assign({ key: id }, frame, { conversation, service, projectRoot }))",
        "        if (id === 'chat') return h(ChatPanel, Object.assign({ key: id }, frame, { conversation, service, projectRoot }))\n"
        "        // 未知 id 返回 null：宁可空一格，也不能把配置写错的 id 悄悄渲染成对话面板。\n"
        "        return null", 'nodeFor fallback')
write(p, s)

print('part1 done')
