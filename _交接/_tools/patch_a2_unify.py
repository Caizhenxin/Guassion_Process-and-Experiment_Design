"""把插件侧的快照命名统一到总工作台（M3.3）那一套：交接-YYYYMMDD-HHMMSS.md

为什么必须统一：同一个 archive 目录现在有两个入口在写（总工作台 tools/交接.py 与
插件面板）。命名不同 ⇒ 两套 glob 各认各的，各留 10 份，同一个目录里混着两条序列，
「保留最近 10 份」这条规矩就不成立了。统一后谁写都进同一条序列、共用 10 份额度。
"""
import io
import os
import shutil

WB = r'D:\GitHub_programe\GitHub\dsh-my-project-workbench'
HUB = r'D:\GitHub_programe\GitHub\DSH_Workbench'


def read(p):
    return io.open(p, encoding='utf-8').read()


def write(p, s):
    io.open(p, 'w', encoding='utf-8', newline='\r\n' if '\r\n' in s else '\n').write(s)


cache = {}
edits = []


def edit(rel, old, new, label):
    edits.append((rel, old, new, label))


# ---------------- dsh/index.js ----------------
edit('dsh/index.js',
     "const SNAPSHOT_RE = /^当前交接-(\\d{8})-(\\d{4})(-(\\d+))?\\.md$/",
     "const SNAPSHOT_RE = /^交接-(\\d{8})-(\\d{6})(-(\\d+))?\\.md$/",
     'index snapshot re')

edit('dsh/index.js',
     """// 同一分钟内连写两次不能覆盖前一份：加 -2、-3…（否则连点保存会静默丢一份历史）。
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
}""",
     """// 命名与总工作台 tools/交接.py 完全一致：同一个 archive 目录两个入口写，必须同一条序列，
// 否则各留各的 10 份，「保留最近 10 份」就名存实亡。
// 同一秒内连写两次不能覆盖前一份：加 -2、-3…（否则连点保存会静默丢一份历史）。
export function snapshotName(when, taken) {
  const pad = (value) => String(value).padStart(2, '0')
  const stamp =
    String(when.getFullYear()) + pad(when.getMonth() + 1) + pad(when.getDate()) +
    '-' + pad(when.getHours()) + pad(when.getMinutes()) + pad(when.getSeconds())
  const names = Array.isArray(taken) ? taken : []
  let name = '交接-' + stamp + '.md'
  let index = 2
  while (names.includes(name)) {
    name = '交接-' + stamp + '-' + index + '.md'
    index += 1
  }
  return name
}""",
     'index snapshotName')

# ---------------- dsh/health.js ----------------
edit('dsh/health.js',
     '    const snapshot = /^当前交接-\\d{8}-\\d{4}(-\\d+)?\\.md$/',
     '    // 与总工作台 tools/交接.py 同一套命名（交接-YYYYMMDD-HHMMSS.md），两个入口共用这条 glob\n'
     '    const snapshot = /^交接-\\d{8}-\\d{6}(-\\d+)?\\.md$/',
     'health snapshot re')

# ---------------- _evidence/test-handover.mjs ----------------
edit('_evidence/test-handover.mjs',
     """  assert.equal(server.snapshotName(when, []), '当前交接-20261028-2030.md')
  assert.equal(server.snapshotName(when, ['当前交接-20261028-2030.md']), '当前交接-20261028-2030-2.md')""",
     """  assert.equal(server.snapshotName(when, []), '交接-20261028-203000.md')
  assert.equal(server.snapshotName(when, ['交接-20261028-203000.md']), '交接-20261028-203000-2.md')
  // 与总工作台 tools/交接.py 同命名：面板存的快照，命令行那条 glob 也认
  assert.match(server.snapshotName(when, []), /^交接-\\d{8}-\\d{6}\\.md$/)""",
     'test naming')

edit('_evidence/test-handover.mjs',
     "for (let day = 1; day <= 12; day += 1) names.push('当前交接-202610' + String(day).padStart(2, '0') + '-0930.md')",
     "for (let day = 1; day <= 12; day += 1) names.push('交接-202610' + String(day).padStart(2, '0') + '-093000.md')",
     'test prune build')

edit('_evidence/test-handover.mjs',
     "assert.ok(result.keep.every((name) => name.startsWith('当前交接-')), '留下的必须都是快照')",
     "assert.ok(result.keep.every((name) => name.startsWith('交接-')), '留下的必须都是快照')",
     'test prune prefix')

edit('_evidence/test-handover.mjs',
     """  const result = server.pruneSnapshots(['当前交接-20261028-2030-2.md', '当前交接-20261028-2030.md'], 1)
  assert.deepEqual(result.keep, ['当前交接-20261028-2030-2.md'])""",
     """  const result = server.pruneSnapshots(['交接-20261028-203000-2.md', '交接-20261028-203000.md'], 1)
  assert.deepEqual(result.keep, ['交接-20261028-203000-2.md'])""",
     'test order')

# ---------------- 逐条应用（三态） ----------------
for rel, old, new, label in edits:
    if rel not in cache:
        cache[rel] = read(os.path.join(WB, rel))
    src = cache[rel]
    if old in src:
        cache[rel] = src.replace(old, new, 1)
        print('  patch', label)
    elif new in src:
        print('  skip (already)', label)
    else:
        raise SystemExit('ANCHOR MISS: ' + label)

for rel, body in cache.items():
    write(os.path.join(WB, rel), body)
    print('written', rel)

# ---------------- 迁移已存在的那份快照 ----------------
adir = os.path.join(HUB, 'archive', 'gp-experiment')
old_path = os.path.join(adir, '当前交接-20261028-2222.md')
new_path = os.path.join(adir, '交接-20261028-222200.md')
if os.path.exists(old_path) and not os.path.exists(new_path):
    shutil.move(old_path, new_path)
    print('migrated', os.path.basename(old_path), '->', os.path.basename(new_path))
else:
    print('migrate skip:', os.path.exists(old_path), os.path.exists(new_path))
print('archive now:', sorted(os.listdir(adir)))
