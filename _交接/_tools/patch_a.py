"""阶段 A：交接归档快照（P4）幂等补丁。

改动面：dsh/index.js、dsh/health.js、lib/client.js、_evidence/test-*.mjs、README.md。
原则：每处锚点必须恰好命中一次；所有改动先在内存里累积，全部成功才落盘（上一轮踩过「同文件多处互相覆盖」）。
"""
import io
import os

WB = r'D:\GitHub_programe\GitHub\dsh-my-project-workbench'

CACHE = {}


def load(rel):
    if rel not in CACHE:
        CACHE[rel] = io.open(os.path.join(WB, rel), encoding='utf-8').read()
    return CACHE[rel]


def edit(rel, old, new, label):
    src = load(rel)
    if new and new in src and old not in src:
        print('  skip  %s（已打过）' % label)
        return
    count = src.count(old)
    assert count == 1, '锚点 %s 命中 %d 次（要恰好 1 次）' % (label, count)
    assert new not in src or old in src, '锚点 %s 新内容已存在' % label
    CACHE[rel] = src.replace(old, new)


def flush():
    for rel, src in CACHE.items():
        io.open(os.path.join(WB, rel), 'w', encoding='utf-8', newline='\n').write(src)
        print('  write %-28s %6d B' % (rel, len(src.encode('utf-8'))))


# ============================ dsh/index.js ============================
rel = 'dsh/index.js'
edit(rel, "import { mkdir, readFile, readdir, stat, writeFile } from 'node:fs/promises'",
     "import { mkdir, readFile, readdir, rm, stat, writeFile } from 'node:fs/promises'", 'import rm')

edit(rel, "      projectRoot: Schema.string().description('本工作台服务的项目文件夹'),",
     "      projectRoot: Schema.string().description('本工作台服务的项目文件夹'),\n"
     "      hubRoot: Schema.string().description('总工作台目录（DSH_Workbench）：交接快照写到 archive/<场景id>/'),", 'schema hubRoot')

edit(rel, """  const dataRoot = resolve(
    (config && config.root) || join(process.env.DSH_HOME || homedir(), 'my-project-workbench'),
  )
""", """  const dataRoot = resolve(
    (config && config.root) || join(process.env.DSH_HOME || homedir(), 'my-project-workbench'),
  )
  // 总工作台（场景 = 项目）：归档快照写到 <hubRoot>/archive/<projects.json 里的场景 id>/。
  // 默认指向本机总工作台；换机器或换目录用 config.hubRoot 覆盖。
  const hubRoot = resolve(
    String((config && config.hubRoot) || process.env.DSH_WORKBENCH_HUB || 'D:\\\\GitHub_programe\\\\GitHub\\\\DSH_Workbench'),
  )
""", 'hubRoot const')

edit(rel, "const BOARD_DATE = /^(\\d{4}-\\d{2}-\\d{2})\\s+/\n", """const BOARD_DATE = /^(\\d{4}-\\d{2}-\\d{2})\\s+/

// ---------- 归档快照（P4）：交接的历史版本 ----------
// 命名与裁剪是纯函数（方便直测）；落盘逻辑在 apply() 里 —— 只有它知道项目根。
const ARCHIVE_KEEP = 10
const SNAPSHOT_RE = /^当前交接-(\\d{8})-(\\d{4})(-(\\d+))?\\.md$/

function snapshotOrder(name) {
  const hit = SNAPSHOT_RE.exec(name)
  if (!hit) return ''
  return hit[1] + hit[2] + (hit[4] ? String(Number(hit[4])).padStart(4, '0') : '0000')
}

// 同一分钟内连写两次不能覆盖前一份：加 -2、-3…（否则连点保存会静默丢一份历史）。
export function snapshotName(when, taken) {
  const pad = (value) => String(value).padStart(2, '0')
  const stamp =
    String(when.getFullYear()) + pad(when.getMonth() + 1) + pad(when.getDate()) +
    '-' + pad(when.getHours()) + pad(when.getMinutes())
  const names = Array.isArray(taken) ? taken : []
  let name = '当前交接-' + stamp + '.md'
  let index = 2
  while (names.includes(name)) {
    name = '当前交接-' + stamp + '-' + index + '.md'
    index += 1
  }
  return name
}

// 只认快照命名：.gitkeep、手写备注一律不碰 —— 误删别人的文件比不裁剪更糟。
export function pruneSnapshots(names, keep = ARCHIVE_KEEP) {
  const list = (Array.isArray(names) ? names : [])
    .filter((name) => SNAPSHOT_RE.test(name))
    .sort((left, right) => snapshotOrder(left).localeCompare(snapshotOrder(right)))
  const over = Math.max(0, list.length - keep)
  return { keep: list.slice(over), drop: list.slice(0, over) }
}
""", 'snapshot helpers')

edit(rel, """  async function readHandover() {""", """  // 归档落在总工作台：先按 projects.json 的 root 反查场景 id，查不到就用目录名。
  async function projectIdOf() {
    try {
      const raw = JSON.parse(await readFile(join(hubRoot, 'projects.json'), 'utf8'))
      const list = Array.isArray(raw && raw.projects) ? raw.projects : []
      const norm = (value) => String(value || '').replace(/\\//g, '\\\\').replace(/\\\\+$/, '').toLowerCase()
      const hit = list.find((item) => item && norm(item.root) === norm(projectRoot))
      if (hit && hit.id) return { id: String(hit.id), source: 'projects.json' }
    } catch {
      /* 没有 projects.json 不算错：单项目用法照样能归档（用目录名当 id） */
    }
    return { id: basename(projectRoot), source: 'dirname' }
  }

  async function archiveSummary() {
    const found = await projectIdOf()
    const dir = join(hubRoot, 'archive', found.id)
    const kept = pruneSnapshots(await readdir(dir).catch(() => [])).keep
    let latestAt = null
    if (kept.length) {
      const info = await stat(join(dir, kept[kept.length - 1])).catch(() => null)
      latestAt = info ? Math.round(info.mtimeMs) : null
    }
    return {
      dir,
      id: found.id,
      idSource: found.source,
      count: kept.length,
      latest: kept.length ? kept[kept.length - 1] : null,
      latestAt,
      keep: ARCHIVE_KEEP,
    }
  }

  // 覆盖写之前先把上一版存进归档，再裁剪到最近 10 份。
  async function archiveHandover(source) {
    if (!String(source || '').trim()) return { written: false, reason: '当前交接是空的，没有可归档的内容' }
    const found = await projectIdOf()
    const dir = join(hubRoot, 'archive', found.id)
    await mkdir(dir, { recursive: true })
    const name = snapshotName(new Date(), await readdir(dir).catch(() => []))
    await writeFile(join(dir, name), source, 'utf8')
    const after = pruneSnapshots(await readdir(dir).catch(() => []))
    for (const old of after.drop) await rm(join(dir, old), { force: true })
    return { written: true, name, id: found.id, count: after.keep.length, dropped: after.drop.length }
  }

  async function readHandover() {""", 'archive helpers in apply')

edit(rel, """    return Object.assign(inspectHandover(text), {
      text,
      path: displayPath(abs),
      exists: Boolean(info),
      updatedAt: info ? Math.round(info.mtimeMs) : null,
    })""", """    return Object.assign(inspectHandover(text), {
      text,
      path: displayPath(abs),
      exists: Boolean(info),
      updatedAt: info ? Math.round(info.mtimeMs) : null,
      archive: await archiveSummary(),
    })""", 'readHandover archive')

edit(rel, """        const text = String((body && body.text) || '')
        const abs = join(projectRoot, HANDOVER_REL)
        await mkdir(dirname(abs), { recursive: true })
        await writeFile(abs, text, 'utf8')
        return ok(Object.assign({ ok: true, writtenAt: Date.now() }, await readHandover()))""",
     """        const text = String((body && body.text) || '')
        const abs = join(projectRoot, HANDOVER_REL)
        // 覆盖之前先归档上一版；内容没变就不存（否则连点保存会刷出一串相同快照）。
        const previous = await readFile(abs, 'utf8').catch(() => '')
        const archived =
          previous && previous !== text && body.archive !== false ? await archiveHandover(previous) : null
        await mkdir(dirname(abs), { recursive: true })
        await writeFile(abs, text, 'utf8')
        return ok(Object.assign({ ok: true, writtenAt: Date.now(), archived }, await readHandover()))""",
     'handover POST archive')

edit(rel, """  // 场景配置（P3）：版式的唯一出处是插件根目录的 scenes.json。""",
     """  // 归档快照（P4）：手动把当前交接存一份进总工作台归档；不动项目里的交接文件。
  ctx.connection.fetch.register({
    path: PREFIX + 'snapshot',
    methods: ['POST'],
    requestBody: 'buffered',
    async fetch() {
      try {
        const source = await readFile(join(projectRoot, HANDOVER_REL), 'utf8').catch(() => '')
        const result = await archiveHandover(source)
        return ok(Object.assign({ ok: true }, result, { archive: await archiveSummary() }))
      } catch (error) {
        return fail(error)
      }
    },
  })

  // 场景配置（P3）：版式的唯一出处是插件根目录的 scenes.json。""", 'snapshot route')

edit(rel, "    const report = await inspectProject({ root: projectRoot, inspectHandover })",
     "    const report = await inspectProject({ root: projectRoot, inspectHandover, hub: hubRoot, archiveId: (await projectIdOf()).id })",
     'health call hub')

# ============================ dsh/health.js ============================
rel = 'dsh/health.js'
edit(rel, "import { dirname, join } from 'node:path'",
     "import { basename, dirname, join } from 'node:path'", 'health import basename')

edit(rel, "export async function inspectProject({ root, selfRoot, inspectHandover, now = Date.now() }) {",
     "export async function inspectProject({ root, selfRoot, inspectHandover, hub, archiveId, now = Date.now() }) {",
     'health signature')

edit(rel, """      evidence: age == null ? '取不到修改时间' : '最后修改距今 ' + age + ' 天',
    })
  }
""", """      evidence: age == null ? '取不到修改时间' : '最后修改距今 ' + age + ' 天',
    })
  }

  // ---------- ⑥b 归档快照：历史版本必须能读、数量受控 ----------
  // 「当前交接 → 归档备份」那条线要真的转起来：只有覆盖写、没有归档，等于没有历史。
  {
    const keep = 10
    const snapshot = /^当前交接-\\d{8}-\\d{4}(-\\d+)?\\.md$/
    const ledger = archiveId || basename(root)
    const dir = hub ? join(hub, 'archive', ledger) : null
    let names = []
    let readError = ''
    if (dir) {
      try {
        const entries = await readdir(dir, { withFileTypes: true })
        names = entries
          .filter((entry) => entry.isFile() && snapshot.test(entry.name))
          .map((entry) => entry.name)
          .sort()
      } catch (error) {
        readError = error && error.code === 'ENOENT' ? '' : String((error && error.message) || error)
      }
    }
    let broken = ''
    if (names.length) {
      const body = await readFile(join(dir, names[names.length - 1]), 'utf8').catch(() => '')
      if (!body.trim()) broken = '最新一份快照是空的'
      else if (!/§〇/.test(body)) broken = '最新一份不含 §〇 标题（不像交接快照）'
    }
    const status = !dir
      ? 'skipped'
      : readError || broken
        ? 'fail'
        : names.length > keep + 2
          ? 'fail'
          : names.length
            ? 'pass'
            : 'warn'
    push({
      id: 'handover:archive',
      group: 'handover',
      title: '归档快照（≤' + keep + ' 份，最新一份可读）',
      status,
      scanned: names.length,
      actual: {
        dir: dir || null,
        count: names.length,
        keep,
        latest: names.length ? names[names.length - 1] : null,
        ledger,
      },
      evidence: !dir
        ? '没有配置总工作台目录（config.hubRoot），跳过归档判据'
        : readError
          ? '归档目录读不了：' + readError
          : broken
            ? broken
            : names.length > keep + 2
              ? '归档 ' + names.length + ' 份，超过保留上限 ' + keep + '（裁剪没生效）'
              : names.length
                ? '归档 ' + names.length + ' 份，最新 ' + names[names.length - 1]
                : '还没有归档快照（第一次覆盖写之后就有了）',
    })
  }
""", 'health archive rule')

# ============================ lib/client.js ============================
rel = 'lib/client.js'
edit(rel, """      const runHealth = async () => {""", """      const snapshot = async () => {
        try {
          const result = await postJson('snapshot', {})
          setMsg(result && result.written ? '已存快照 ' + result.name : (result && result.reason) || '没有可归档的内容')
          store.reload()
        } catch (error) {
          setMsg('存快照失败：' + errText(error))
        }
      }

      const runHealth = async () => {""", 'client snapshot fn')

edit(rel, """        : (bytes / 1024).toFixed(2) + ' / ' + (HANDOVER_LIMIT / 1024).toFixed(0) + ' KB' +
          (info.updatedAt ? ' · 上次写入 ' + agoText(info.updatedAt) : ' · 还没有交接文件') +
          (msg ? ' · ' + msg : '')""",
     """        : (bytes / 1024).toFixed(2) + ' / ' + (HANDOVER_LIMIT / 1024).toFixed(0) + ' KB' +
          (info.updatedAt ? ' · 上次写入 ' + agoText(info.updatedAt) : ' · 还没有交接文件') +
          (info.archive && info.archive.count ? ' · 归档 ' + info.archive.count + ' 份' : '') +
          (msg ? ' · ' + msg : '')""", 'client sub archive')

edit(rel, """            h('button', { type: 'button', className: 'mpw-btn', onClick: save, disabled: !dirty }, '覆盖写回'),""",
     """            h('button', { type: 'button', className: 'mpw-btn', onClick: save, disabled: !dirty }, '覆盖写回'),
            h('button', { type: 'button', className: 'mpw-chip', onClick: snapshot }, '存快照'),""",
     'client snapshot button')

# ============================ _evidence/test-handover.mjs ============================
rel = '_evidence/test-handover.mjs'
edit(rel, "const clientSource = await readFile(join(root, 'lib', 'client.js'), 'utf8')",
     """check('快照命名：同分钟第二次加序号，不覆盖前一份', () => {
  const when = new Date(2026, 9, 28, 20, 30)
  assert.equal(server.snapshotName(when, []), '当前交接-20261028-2030.md')
  assert.equal(server.snapshotName(when, ['当前交接-20261028-2030.md']), '当前交接-20261028-2030-2.md')
})

check('快照裁剪：只留最近 10 份，不碰非快照文件', () => {
  const names = ['.gitkeep', '随手记.md']
  for (let day = 1; day <= 12; day += 1) names.push('当前交接-202610' + String(day).padStart(2, '0') + '-0930.md')
  const result = server.pruneSnapshots(names, 10)
  assert.equal(result.keep.length, 10, '应保留 10 份')
  assert.equal(result.drop.length, 2, '应裁掉 2 份')
  assert.ok(result.keep.every((name) => name.startsWith('当前交接-')), '留下的必须都是快照')
  assert.ok(!result.keep.includes('.gitkeep'), '.gitkeep 不许被算进快照')
})

check('快照裁剪：同分钟带序号的按序号排序（-2 比无序号的新）', () => {
  const result = server.pruneSnapshots(['当前交接-20261028-2030-2.md', '当前交接-20261028-2030.md'], 1)
  assert.deepEqual(result.keep, ['当前交接-20261028-2030-2.md'])
})

const clientSource = await readFile(join(root, 'lib', 'client.js'), 'utf8')""", 'test-handover snapshot cases')

edit(rel, """if (failed > 0) {""",
     """check('服务端注册了 snapshot 路由（手动存快照）', () => {
  assert.ok(serverSource.includes("PREFIX + 'snapshot'"), '缺 snapshot 路由')
  assert.ok(serverSource.includes('archiveHandover'), '缺归档函数')
})

if (failed > 0) {""", 'test-handover snapshot route')

# ============================ _evidence/test-health.mjs ============================
rel = '_evidence/test-health.mjs'
edit(rel, """async function ruleOf(root, id) {
  const report = await inspectProject({ root, selfRoot: root, inspectHandover })""",
     """async function ruleOf(root, id, extra) {
  const report = await inspectProject(Object.assign({ root, selfRoot: root, inspectHandover }, extra || {}))""",
     'test-health ruleOf extra')

edit(rel, """const root = await fresh({ '_交接/当前交接.md': handoverSource(['上次进度', '下一步']) })""",
     """{
  const root = await fresh({})
  const hub = join(root, 'hub')
  const dir = join(hub, 'archive', 'proj')
  await mkdir(dir, { recursive: true })
  await writeFile(join(dir, '当前交接-20261028-2030.md'), '# §〇 当前交接\\n- 上次进度：甲\\n', 'utf8')
  const { rule } = await ruleOf(root, 'handover:archive', { hub, archiveId: 'proj' })
  check('归档 1 份且可读 → pass', rule && rule.status === 'pass', rule && rule.status)
}
{
  const root = await fresh({})
  const hub = join(root, 'hub')
  const dir = join(hub, 'archive', 'proj')
  await mkdir(dir, { recursive: true })
  for (let index = 1; index <= 15; index += 1) {
    await writeFile(join(dir, '当前交接-202610' + String(index).padStart(2, '0') + '-0930.md'), '# §〇\\n', 'utf8')
  }
  const { rule } = await ruleOf(root, 'handover:archive', { hub, archiveId: 'proj' })
  check('归档 15 份（超上限）→ fail', rule && rule.status === 'fail', rule && rule.status)
}
{
  const root = await fresh({})
  const hub = join(root, 'hub')
  const dir = join(hub, 'archive', 'proj')
  await mkdir(dir, { recursive: true })
  await writeFile(join(dir, '当前交接-20261028-2030.md'), '   \\n', 'utf8')
  const { rule } = await ruleOf(root, 'handover:archive', { hub, archiveId: 'proj' })
  check('最新快照是空的 → fail', rule && rule.status === 'fail', rule && rule.status)
}
{
  const root = await fresh({})
  const hub = join(root, 'hub')
  const { rule } = await ruleOf(root, 'handover:archive', { hub, archiveId: 'proj' })
  check('归档目录还不存在 → warn（不是 fail）', rule && rule.status === 'warn', rule && rule.status)
}
{
  const root = await fresh({})
  const { rule } = await ruleOf(root, 'handover:archive')
  check('没配总工作台目录 → skipped（不假装通过）', rule && rule.status === 'skipped', rule && rule.status)
}
const root = await fresh({ '_交接/当前交接.md': handoverSource(['上次进度', '下一步']) })""",
     'test-health archive cases')

# ============================ _evidence/test-server.mjs ============================
rel = '_evidence/test-server.mjs'
edit(rel, """const dataRoot = await mkdtemp(join(tmpdir(), 'mpw-data-'))
mod.apply(ctx, {
  root: dataRoot,
  projectRoot: PROJECT,
})""", """const dataRoot = await mkdtemp(join(tmpdir(), 'mpw-data-'))
// 归档落总工作台：自测必须指向临时目录，绝不许往真 DSH_Workbench 里写快照。
const hubRoot = await mkdtemp(join(tmpdir(), 'mpw-hub-'))
mod.apply(ctx, {
  root: dataRoot,
  projectRoot: PROJECT,
  hubRoot,
})""", 'test-server hub')

edit(rel, "assert.equal(routes.length, 12, '应该有 12 条路由（新增 health / scenes）')",
     "assert.equal(routes.length, 13, '应该有 13 条路由（新增 health / scenes / snapshot）')", 'test-server routes')

# ============================ README.md ============================
rel = 'README.md'
edit(rel, "| `scenes` | GET 只读：读插件根目录的 `scenes.json`",
     "| `snapshot` (POST) | 手动把当前交接存一份进总工作台 `archive/<场景id>/`（保留最近 10 份）；不动项目里的文件 |\n"
     "| `scenes` | GET 只读：读插件根目录的 `scenes.json`", 'readme snapshot row')

src = load(rel)
for old, new, label in [
    ('12 条接口', '13 条接口', 'readme routes count'),
    ('16 条判据', '17 条判据', 'readme judge count'),
]:
    assert old in src, 'README 里找不到 ' + old
    src = src.replace(old, new)
CACHE[rel] = src

flush()
print('patch A 完成')
