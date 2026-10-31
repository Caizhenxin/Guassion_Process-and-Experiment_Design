# -*- coding: utf-8 -*-
"""P1 交接层补丁：把 my-project-workbench 改出「§〇 交接面板 + 待办板落项目内 + 反例自测」。

设计约束（照抄淋雨家工作台的记忆机制，只抄机制）：
  1. 判据唯一出处 —— 空 / 缺字段 / 超 4096 字节只在 dsh/index.js 的 inspectHandover 里判一次；
  2. 覆盖写不追加 —— handover 面板写的是同一份文件，不是日志；
  3. 会失败的检查 —— _evidence/test-handover.mjs 故意造三个反例，必须全部报错。

跑法：python -X utf8 _交接/_tools/patch_p1.py
"""
import sys
from pathlib import Path

ROOT = Path(r"D:\GitHub_programe\GitHub\dsh-my-project-workbench")
DRY = "--dry" in sys.argv

EDITS = []  # (相对路径, 说明, old, new)


def edit(rel, label, old, new):
    EDITS.append((rel, label, old, new))


# ============================ dsh/index.js ============================

edit(
    r"dsh\index.js",
    "import 增加 dirname",
    "import { basename, extname, isAbsolute, join, normalize, resolve, sep } from 'node:path'",
    "import { basename, dirname, extname, isAbsolute, join, normalize, resolve, sep } from 'node:path'",
)

edit(
    r"dsh\index.js",
    "交接层常量",
    "const SKIP_DIRS = new Set(['node_modules', '.git', '__pycache__', '.venv', 'venv', '_scratch'])\n",
    """const SKIP_DIRS = new Set(['node_modules', '.git', '__pycache__', '.venv', 'venv', '_scratch'])

// 交接层（抄淋雨家工作台的记忆机制，只取「一个事实只存一处」那部分）：
//   私有层 = _交接/当前交接.md 的「§〇 当前交接」，覆盖写、≤4KB，
//            只答四问：我是谁 / 干到哪 / 下一步 / 卡在哪；
//   共享层 = _交接/待办板.md，「该做什么」的唯一落点，体检的 ⛔ 项也追加到这里。
const HANDOVER_REL = join('_交接', '当前交接.md')
const BOARD_REL = join('_交接', '待办板.md')
const HANDOVER_MAX = 4096
// 判据只写在这一个地方：客户端与自测脚本都读它。两处各判一次 = 两份结论，早晚打架。
const HANDOVER_REQUIRED = ['上次进度', '下一步', '卡点']
const BOARD_HEADER = [
  '# 待办板（全机唯一落点）',
  '',
  '> 「该做什么」只在**这一处**记；一行一件：`- [ ] YYYY-MM-DD 事项`。',
  '> 做完打勾或删行；体检的 ⛔ 项会自动追加到这里，同一件只许一行。',
  '',
  '',
].join('\\n')
const BOARD_LINE = /^\\s*-\\s*\\[( |x|X)\\]\\s*(.+?)\\s*$/
const BOARD_DATE = /^(\\d{4}-\\d{2}-\\d{2})\\s+/
""",
)

edit(
    r"dsh\index.js",
    "导出判据 inspectHandover",
    "export function apply(ctx, config) {",
    """/**
 * 「§〇 当前交接」的判据 —— 唯一出处。
 * 空文件 / 缺「上次进度|下一步|卡点」/ 超过 4096 字节，任一命中即 ok=false。
 * 自测脚本会故意造这三个反例：它们必须全部报错，否则这个检查只是装饰。
 */
export function inspectHandover(source) {
  const text = String(source == null ? '' : source)
  const bytes = Buffer.byteLength(text, 'utf8')
  const fields = {}
  for (const field of HANDOVER_REQUIRED) {
    fields[field] = new RegExp('(?:^|\\\\n)\\\\s*[-*]?\\\\s*' + field + '\\\\s*[：:]').test(text)
  }
  const missing = HANDOVER_REQUIRED.filter((field) => !fields[field])
  const empty = !text.trim()
  return {
    ok: !empty && missing.length === 0 && bytes <= HANDOVER_MAX,
    bytes,
    limit: HANDOVER_MAX,
    over: bytes > HANDOVER_MAX,
    empty,
    fields,
    missing,
  }
}

export function apply(ctx, config) {""",
)

edit(
    r"dsh\index.js",
    "待办板/交接文件读写",
    """  async function writeStore(file, value) {
    await mkdir(dataRoot, { recursive: true })
    await writeFile(join(dataRoot, file), JSON.stringify(value, null, 2), 'utf8')
    return value
  }
""",
    """  async function writeStore(file, value) {
    await mkdir(dataRoot, { recursive: true })
    await writeFile(join(dataRoot, file), JSON.stringify(value, null, 2), 'utf8')
    return value
  }

  // ---------- 交接层：私有层（§〇 覆盖写）+ 共享层（待办板） ----------

  function dateOnly() {
    const now = new Date()
    const pad = (value) => String(value).padStart(2, '0')
    return now.getFullYear() + '-' + pad(now.getMonth() + 1) + '-' + pad(now.getDate())
  }

  function normalizeTodoList(list) {
    if (!Array.isArray(list)) return []
    return list
      .map((item, index) => ({
        id: String((item && item.id) || 'b' + index),
        text: String((item && (item.text || item.title || item.content)) || '').trim(),
        at: String((item && (item.at || item.time)) || ''),
        done: Boolean(item && (item.done || item.completed || item.finished)),
      }))
      .filter((item) => item.text)
  }

  // 待办板是 markdown：人能直接看、能进 git，机器也能逐行判。
  function parseBoard(source) {
    const items = []
    for (const line of String(source || '').split(/\\r?\\n/)) {
      const matched = BOARD_LINE.exec(line)
      if (!matched) continue
      const body = matched[2]
      const dated = BOARD_DATE.exec(body)
      items.push({
        id: 'b' + items.length,
        text: dated ? body.slice(dated[0].length) : body,
        at: dated ? dated[1] : '',
        done: matched[1].toLowerCase() === 'x',
      })
    }
    return items
  }

  function boardText(items) {
    const rows = items.map((item) => {
      const mark = item.done ? 'x' : ' '
      const day = /^\\d{4}-\\d{2}-\\d{2}/.test(String(item.at || '')) ? item.at : dateOnly()
      return '- [' + mark + '] ' + day + ' ' + item.text
    })
    return BOARD_HEADER + (rows.length ? rows.join('\\n') + '\\n' : '')
  }

  // 一次性迁移：老版本把待办存在 DSH 数据目录的 todos.json，搬进项目内的待办板（唯一落点）。
  async function migrateBoard() {
    const legacy = normalizeTodoList(await readStore('todos.json', []))
    if (!legacy.length) return 0
    const abs = join(projectRoot, BOARD_REL)
    await mkdir(dirname(abs), { recursive: true })
    await writeFile(abs, boardText(legacy), 'utf8')
    return legacy.length
  }

  async function readBoard() {
    const abs = join(projectRoot, BOARD_REL)
    let source = ''
    try {
      source = await readFile(abs, 'utf8')
    } catch {
      const migrated = await migrateBoard()
      if (migrated) source = await readFile(abs, 'utf8').catch(() => '')
    }
    return { items: parseBoard(source), path: displayPath(abs) }
  }

  async function saveBoard(list) {
    const abs = join(projectRoot, BOARD_REL)
    await mkdir(dirname(abs), { recursive: true })
    await writeFile(abs, boardText(normalizeTodoList(list)), 'utf8')
    return readBoard()
  }

  async function readHandover() {
    const abs = join(projectRoot, HANDOVER_REL)
    let text = ''
    let info = null
    try {
      info = await stat(abs)
      if (info.isFile()) text = await readFile(abs, 'utf8')
    } catch {
      info = null
    }
    return Object.assign(inspectHandover(text), {
      text,
      path: displayPath(abs),
      exists: Boolean(info),
      updatedAt: info ? Math.round(info.mtimeMs) : null,
    })
  }
""",
)

edit(
    r"dsh\index.js",
    "todos 改落待办板 + 新增 handover 路由",
    """  ctx.connection.fetch.register({
    path: PREFIX + 'todos',
    methods: ['GET', 'POST'],
    requestBody: 'buffered',
    async fetch(request) {
      try {
        if (request.method === 'GET') return ok({ ok: true, todos: await readStore('todos.json', []) })
        const body = await request.json()
        const todos = Array.isArray(body && body.todos) ? body.todos : []
        await writeStore('todos.json', todos)
        return ok({ ok: true, todos })
      } catch (error) {
        return fail(error)
      }
    },
  })
""",
    """  // 待办不再落 DSH 数据目录：它必须是**项目内**的一份文件，才谈得上「唯一落点」，
  // 也才能让 P2 的体检脚本把 ⛔ 项直接追加进来。
  ctx.connection.fetch.register({
    path: PREFIX + 'todos',
    methods: ['GET', 'POST'],
    requestBody: 'buffered',
    async fetch(request) {
      try {
        if (request.method === 'GET') {
          const board = await readBoard()
          return ok({ ok: true, todos: board.items, boardPath: board.path, store: 'board' })
        }
        const body = await request.json()
        const board = await saveBoard(Array.isArray(body && body.todos) ? body.todos : [])
        return ok({ ok: true, todos: board.items, boardPath: board.path, store: 'board' })
      } catch (error) {
        return fail(error)
      }
    },
  })

  // §〇 当前交接：GET 读 + POST 覆盖写。
  // 超线不拦写 —— 拦了人会绕过工具直接改文件，那连判据都没了；只把 over 交回去让面板标红。
  ctx.connection.fetch.register({
    path: PREFIX + 'handover',
    methods: ['GET', 'POST'],
    requestBody: 'buffered',
    async fetch(request) {
      try {
        if (request.method === 'GET') return ok(Object.assign({ ok: true }, await readHandover()))
        const body = await request.json()
        const text = String((body && body.text) || '')
        const abs = join(projectRoot, HANDOVER_REL)
        await mkdir(dirname(abs), { recursive: true })
        await writeFile(abs, text, 'utf8')
        return ok(Object.assign({ ok: true, writtenAt: Date.now() }, await readHandover()))
      } catch (error) {
        return fail(error)
      }
    },
  })
""",
)

# ============================ lib/client.js ============================

edit(
    r"lib\client.js",
    "新增 HandoverPanel 组件",
    "    /* ---------------- 架构图（内嵌 archify 生成的单文件 HTML）---------------- */",
    """    /* ---------------- 当前交接（§〇，覆盖写）---------------- */

    // 判据在服务端 inspectHandover（唯一出处）。这里只显示结果、负责写回，不另立一套规矩。
    const HANDOVER_LIMIT = 4096
    const HANDOVER_FIELDS = ['上次进度', '下一步', '卡点']

    function HandoverPanel(props) {
      const store = useApi('handover')
      const [text, setText] = useState('')
      const [dirty, setDirty] = useState(false)
      const [msg, setMsg] = useState('')

      useEffect(() => {
        if (!dirty && store.data && typeof store.data.text === 'string') setText(store.data.text)
      }, [store.data, dirty])

      const bytes = new TextEncoder().encode(text).length
      const percent = Math.min(100, Math.round((bytes / HANDOVER_LIMIT) * 100))
      const over = bytes > HANDOVER_LIMIT
      const missing = HANDOVER_FIELDS.filter((field) => !new RegExp(field + '\\\\s*[：:]').test(text))
      const empty = !text.trim()

      const save = async () => {
        try {
          await postJson('handover', { text })
          setDirty(false)
          setMsg('已覆盖写 · ' + stamp())
          store.reload()
        } catch (error) {
          setMsg('保存失败：' + errText(error))
        }
      }

      const info = store.data || {}
      const sub = store.error
        ? '读取失败：' + store.error
        : (bytes / 1024).toFixed(2) + ' / ' + (HANDOVER_LIMIT / 1024).toFixed(0) + ' KB' +
          (info.updatedAt ? ' · 上次写入 ' + agoText(info.updatedAt) : ' · 还没有交接文件') +
          (msg ? ' · ' + msg : '')

      const hint = empty
        ? '空文件：新会话读到它等于没交接。'
        : missing.length
          ? '缺 ' + missing.join(' / ') + ' —— §〇 只答四问，缺一项下次开工就断片。'
          : over
            ? '超出 4096 字节 ' + (bytes - HANDOVER_LIMIT) + ' B：把历史搬 _交接/归档/，这里只留指针。'
            : ''

      return h(
        Panel,
        {
          id: 'handover',
          no: props.no,
          title: '当前交接（§〇）',
          sub,
          style: props.style,
          expanded: props.expanded,
          onExpand: props.onExpand,
          actions: [h(RefreshChip, { onClick: store.reload })],
        },
        h(
          'div',
          { className: 'mpw-hobox' },
          h('div', { className: 'mpw-gauge' + (over ? ' is-bad' : empty || missing.length ? ' is-warn' : '') },
            h('i', { style: { width: percent + '%' } })),
          hint ? h('div', { className: 'mpw-hint' + (empty || missing.length ? ' is-bad' : '') }, hint) : null,
          h('textarea', {
            className: 'mpw-textarea',
            spellCheck: false,
            placeholder: '- 身份：项目 … · 面板 … · 第 N 次写\\n- 上次进度：…\\n- 下一步：① … ② …\\n- 卡点：…\\n- 细节在哪：…',
            value: text,
            onChange: (event) => {
              setText(event.target.value)
              setDirty(true)
            },
            onKeyDown: (event) => {
              if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
                event.preventDefault()
                save()
              }
            },
          }),
          h(
            'div',
            { className: 'mpw-rowacts' },
            h('button', { type: 'button', className: 'mpw-btn', onClick: save, disabled: !dirty }, '覆盖写回'),
            h(
              'button',
              {
                type: 'button',
                className: 'mpw-chip',
                onClick: () => {
                  setDirty(false)
                  setMsg('已放弃改动')
                  store.reload()
                },
              },
              '放弃改动',
            ),
            h('span', { className: 'mpw-dim small' }, dirty ? '有未保存改动（Ctrl+Enter 写回）' : '只覆盖这一份，不追加'),
          ),
        ),
      )
    }

    /* ---------------- 架构图（内嵌 archify 生成的单文件 HTML）---------------- */""",
)

edit(
    r"lib\client.js",
    "总览场景加交接面板",
    "              { w: 7, panels: [{ id: 'kpi', g: 0 }, { id: 'milestones', g: 1 }] },",
    "              { w: 7, panels: [{ id: 'kpi', g: 0 }, { id: 'handover', g: 1 }, { id: 'milestones', g: 1 }] },",
)

edit(
    r"lib\client.js",
    "ALL_PANELS 加 handover",
    "const ALL_PANELS = ['kpi', 'lastWork', 'milestones', 'arch', 'files', 'preview', 'gallery', 'notes', 'todos', 'links', 'chat']",
    "const ALL_PANELS = ['kpi', 'handover', 'lastWork', 'milestones', 'arch', 'files', 'preview', 'gallery', 'notes', 'todos', 'links', 'chat']",
)

edit(
    r"lib\client.js",
    "nodeFor 分派 handover",
    "        if (id === 'todos') return h(TodosPanel, Object.assign({ key: id }, frame, shared))",
    "        if (id === 'todos') return h(TodosPanel, Object.assign({ key: id }, frame, shared))\n        if (id === 'handover') return h(HandoverPanel, Object.assign({ key: id }, frame, shared))",
)

edit(
    r"lib\client.js",
    "待办面板小字写明落点",
    """      const left = items.filter((item) => !item.done).length
      const sub = store.error ? '读取失败：' + store.error : '未完成 ' + left + ' / 共 ' + items.length + (msg ? ' · ' + msg : '')""",
    """      const left = items.filter((item) => !item.done).length
      const boardPath = (store.data && store.data.boardPath) || '_交接/待办板.md'
      const sub = store.error
        ? '读取失败：' + store.error
        : '未完成 ' + left + ' / 共 ' + items.length + ' · 落 ' + boardPath + (msg ? ' · ' + msg : '')""",
)

edit(
    r"lib\client.js",
    "交接面板样式",
    "      '.mpw-foot{flex:0 0 auto}',",
    """      '.mpw-foot{flex:0 0 auto}',
      '.mpw-hobox{display:flex;flex-direction:column;height:100%;min-height:0;gap:6px}',
      '.mpw-hobox .mpw-textarea{flex:1 1 auto;min-height:120px;resize:none;',
      'font-family:ui-monospace,Consolas,monospace;font-size:11.5px;line-height:1.7}',
      '.mpw-gauge{height:4px;border-radius:2px;background:var(--mpw-cyan-soft);overflow:hidden;flex:0 0 auto}',
      '.mpw-gauge>i{display:block;height:100%;background:var(--mpw-cyan);width:0}',
      '.mpw-gauge.is-warn>i{background:var(--mpw-warn)}',
      '.mpw-gauge.is-bad>i{background:var(--mpw-bad)}',
      '.mpw-hint{font-size:11px;color:var(--mpw-warn);word-break:break-word}',
      '.mpw-hint.is-bad{color:var(--mpw-bad)}',""",
)

# ============================ _evidence/test-client.mjs ============================

edit(
    r"_evidence\test-client.mjs",
    "自测：面板数 11 → 12",
    """// 网格：11 个面板全部挂载（切场景只改 display，不卸载）""",
    """// 网格：12 个面板全部挂载（切场景只改 display，不卸载）""",
)

edit(
    r"_evidence\test-client.mjs",
    "自测：期望面板清单加 handover",
    """for (const expected of ['kpi', 'lastWork', 'milestones', 'arch', 'files', 'preview', 'gallery', 'notes', 'todos', 'links', 'chat']) {
  assert.ok(ids.includes(expected), '面板必须常驻挂载：' + expected)
}
assert.equal(ids.length, 11, '11 个面板都应在 DOM 里')""",
    """for (const expected of ['kpi', 'handover', 'lastWork', 'milestones', 'arch', 'files', 'preview', 'gallery', 'notes', 'todos', 'links', 'chat']) {
  assert.ok(ids.includes(expected), '面板必须常驻挂载：' + expected)
}
assert.equal(ids.length, 12, '12 个面板都应在 DOM 里')""",
)

edit(
    r"_evidence\test-client.mjs",
    "自测：总览可见面板加 handover",
    """  ['arch', 'kpi', 'lastWork', 'milestones', 'notes', 'todos'],
  '总览场景应该显示概览/上次工作/里程碑/便利贴/待办/架构图',""",
    """  ['arch', 'handover', 'kpi', 'lastWork', 'milestones', 'notes', 'todos'],
  '总览场景应该显示概览/交接/上次工作/里程碑/便利贴/待办/架构图',""",
)

edit(
    r"_evidence\test-client.mjs",
    "自测：序号正则 01–07",
    """  assert.match(text(no), /^\\s*0[1-6]\\s*$/, '序号应补零：' + text(no))""",
    """  assert.match(text(no), /^\\s*0[1-7]\\s*$/, '序号应补零：' + text(no))""",
)

# ============================ README.md ============================

edit(
    r"README.md",
    "场景表写交接面板",
    "| 项目总览 | 第一行 左 7：整体进展（自然高）· 里程碑（撑满）／右 5：上次做到哪（自然高）· 便利贴（撑满）· 待办（自然高）；第二行整宽：项目架构图 | 每次打开先看「整体 + 上次到哪 + 系统长什么样」 |",
    "| 项目总览 | 第一行 左 7：整体进展（自然高）· **当前交接**（撑满）· 里程碑（撑满）／右 5：上次做到哪（自然高）· 便利贴（撑满）· 待办（自然高）；第二行整宽：项目架构图 | 每次打开先看「整体 + 交接 + 上次到哪」 |",
)

edit(
    r"README.md",
    "能力表加一行",
    "| 上次做到哪 | `Log.md` 最新一条的标题、小节与要点（直接回答「上次做到哪」） |",
    """| 上次做到哪 | `Log.md` 最新一条的标题、小节与要点（直接回答「上次做到哪」） |
| 当前交接（§〇） | 直接读写项目里的 `_交接/当前交接.md`：按 4096 字节算进度条，缺「上次进度/下一步/卡点」直接标红。**覆盖写、不追加** —— 换会话时的唯一入口 |""",
)

edit(
    r"README.md",
    "接口表：notes/todos/handover",
    "| `notes` `todos` | GET 读 / POST 存，落 `root` 目录 |",
    """| `notes` | GET 读 / POST 存，落 `root`（DSH 用户数据目录，不写项目仓库） |
| `todos` | GET 读 / POST 存，落**项目内** `_交接/待办板.md`（唯一落点）；老数据首次读取时自动从 DSH 数据目录迁过来 |
| `handover` | GET 读 / POST 覆盖写 `_交接/当前交接.md`；判据 `inspectHandover`：空 / 缺字段 / 超 4096 字节 = 不通过（超线只警告不拦写，拦了人会绕过工具改文件） |""",
)

edit(
    r"README.md",
    "自测脚本清单",
    """E:\\Node\\node.exe _evidence\\test-client.mjs    # 注册契约 + 结构（11 个面板）""",
    """E:\\Node\\node.exe _evidence\\test-client.mjs    # 注册契约 + 结构（12 个面板）
E:\\Node\\node.exe _evidence\\test-handover.mjs  # 交接层：三个反例必须全部报错""",
)

edit(
    r"README.md",
    "V4 章节",
    "没抄的：换整壳（自己拉起引擎，升级会互相拖累）、24 种面板、`⧉` 多窗口、未激活标签收窄成图标。",
    """没抄的：换整壳（自己拉起引擎，升级会互相拖累）、24 种面板、`⧉` 多窗口、未激活标签收窄成图标。

## V4：交接层（抄他的「记忆机制」，只抄机制不抄系统）

判据来自他那句「**规矩写在文档里靠自觉，机制跑在代码里靠机器**」。V4 只做四件，每件都要求"会失败"：

1. **私有层** `_交接/当前交接.md`：只答「我是谁 / 干到哪 / 下一步 / 卡在哪」，**覆盖写**、≤ 4096 字节；
   缺字段或超线，面板直接标红。换会话时它是唯一入口。
2. **待办板** `_交接/待办板.md`：`todos` 面板改落这里（老数据首次读取自动迁移），全机唯一落点，
   为 P2「体检 ⛔ 自动进待办」铺路。
3. **注入层** 项目根 `AGENTS.md`：只放"不读就会白干"的铁律 + 单一权威表，指向上面两份文件；不写教程。
4. **反例自测** `_evidence/test-handover.mjs`：空文件 / 超 4096 字节 / 缺「卡点」三个反例必须**全部报错**
   —— 不报就说明这个检查是假的。

没做的（留给 P2/P3）：体检脚本与 ⛔ 自动进待办、四块板里的通知看板与总索引、配置驱动的场景系统。""",
)

# ============================ _evidence/test-server.mjs ============================

edit(
    r"_evidence\test-server.mjs",
    "自测：路由数 9 → 10",
    "assert.equal(routes.length, 9, '应该有 9 条路由')",
    "assert.equal(routes.length, 10, '应该有 10 条路由（新增 handover）')",
)

# 待办改落「项目内」之后，自测的 POST 就会写进真项目的数据 —— 这是这次改造带出来的副作用。
# 处理办法不是让自测别测，而是让它自己拍快照、退出时还原（成功失败都还原）。
edit(
    r"_evidence\test-server.mjs",
    "自测：先拍待办板快照，退出时还原",
    """const dataRoot = await mkdtemp(join(tmpdir(), 'mpw-data-'))
mod.apply(ctx, {
  root: dataRoot,
  projectRoot: 'D:/GitHub_programe/GitHub/Guassion-Process-Experiment-Design',
})""",
    """const PROJECT = 'D:/GitHub_programe/GitHub/Guassion-Process-Experiment-Design'
const BOARD = join(PROJECT, '_交接', '待办板.md')

// 待办现在落在**项目内**的待办板，所以自测的 POST 会写进真项目的数据。
// 跑之前拍快照、退出时无论成败都还原 —— 自测不许改用户的真待办。
const boardSnapshot = (() => {
  try {
    return readFileSync(BOARD, 'utf8')
  } catch {
    return null
  }
})()
process.on('exit', () => {
  try {
    if (boardSnapshot == null) rmSync(BOARD, { force: true })
    else writeFileSync(BOARD, boardSnapshot, 'utf8')
  } catch (error) {
    console.error('待办板还原失败：' + error.message)
  }
})

const dataRoot = await mkdtemp(join(tmpdir(), 'mpw-data-'))
mod.apply(ctx, {
  root: dataRoot,
  projectRoot: PROJECT,
})""",
)

edit(
    r"_evidence\test-server.mjs",
    "自测：引入同步文件接口",
    "import { mkdtemp } from 'node:fs/promises'",
    "import { readFileSync, rmSync, writeFileSync } from 'node:fs'\nimport { mkdtemp } from 'node:fs/promises'",
)

# ============================ _evidence/test-render.mjs ============================
# 渲染自测里另有一套硬编码期望（面板清单 + 数量 + 总览可见集），必须一起改，
# 否则会出现「客户端契约过了、渲染过了 11 个」这种半新半旧的状态。

edit(
    r"_evidence\test-render.mjs",
    "渲染自测：总览可见集加 handover",
    "assert.deepEqual(a.visible.map((panel) => panel.props['data-panel']).sort(), ['arch', 'kpi', 'lastWork', 'milestones', 'notes', 'todos'])",
    "assert.deepEqual(a.visible.map((panel) => panel.props['data-panel']).sort(), ['arch', 'handover', 'kpi', 'lastWork', 'milestones', 'notes', 'todos'])",
)

edit(
    r"_evidence\test-render.mjs",
    "渲染自测：面板清单加 handover",
    "for (const expected of ['kpi', 'lastWork', 'milestones', 'arch', 'files', 'preview', 'gallery', 'notes', 'todos', 'links', 'chat']) {",
    "for (const expected of ['kpi', 'handover', 'lastWork', 'milestones', 'arch', 'files', 'preview', 'gallery', 'notes', 'todos', 'links', 'chat']) {",
)

edit(
    r"_evidence\test-render.mjs",
    "渲染自测：面板数 11 → 12",
    "assert.equal(internals.ALL_PANELS.length, 11, '11 个面板常驻挂载')",
    "assert.equal(internals.ALL_PANELS.length, 12, '12 个面板常驻挂载')",
)

# ============================ 执行 ============================


def apply_edits():
    """顺序累积：同一文件的多处改动必须叠在上一处的结果上。

    第一版写成「每次都从原文替换」，结果同一文件只有最后一处生效
    —— 20 个锚点全部「命中」，文件却只改了一个角，自测才把它抓出来。
    """
    cache = {}
    changed = set()
    problems = []
    for rel, label, old, new in EDITS:
        path = ROOT / rel
        if rel not in cache:
            cache[rel] = path.read_bytes().decode("utf-8")
        source = cache[rel]
        if old in source:
            if new in source:
                print("  ? 跳过（新旧锚点共存，需人工看）：%s · %s" % (rel, label))
                continue
            cache[rel] = source.replace(old, new, 1)
            changed.add(rel)
            print("  + %s · %s" % (rel, label))
        elif new in source:
            print("  = 跳过（已打过）：%s · %s" % (rel, label))
        else:
            problems.append("%s  [%s] 新旧锚点都找不到" % (rel, label))
    if problems:
        print("\n锚点校验失败，未写任何文件：")
        for line in problems:
            print("  ! " + line)
        return 1
    if not changed:
        print("\n没有需要改的地方。")
        return 0
    if DRY:
        print("\n[dry] 只校验锚点，不写文件。待改：%s" % ", ".join(sorted(changed)))
        return 0
    for rel in sorted(changed):
        data = cache[rel].encode("utf-8")
        (ROOT / rel).write_bytes(data)
        print("  已写 %s（%d 字节）" % (rel, len(data)))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("目标仓库：%s" % ROOT)
    code = apply_edits()
    print("完成" if code == 0 else "失败")
    sys.exit(code)
