import io, os

WB = r'D:\GitHub_programe\GitHub\dsh-my-project-workbench'
GP = r'D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design'
HUB = r'D:\GitHub_programe\GitHub\DSH_Workbench'


def read(p):
    return io.open(p, encoding='utf-8').read()


def write(p, s):
    io.open(p, 'w', encoding='utf-8', newline='\r\n' if '\r\n' in s else '\n').write(s)


def sub(s, old, new, label):
    assert s.count(old) == 1, 'anchor %s: %d' % (label, s.count(old))
    return s.replace(old, new)


# ---------------- README：自测条数 ----------------
p = os.path.join(WB, 'README.md')
s = read(p)
s = sub(s, '# 交接层：三个反例必须全部报错', '# 交接层：反例必须全部报错 + 快照命名/裁剪', 'readme handover comment')
s = sub(s, '# 体检：41 条检查（零扫描 / 量纲 / 锚点 / 幂等 / 两段判定 / 场景表 / 写盘失败）',
        '# 体检：46 条检查（零扫描 / 量纲 / 锚点 / 幂等 / 两段判定 / 场景表 / 归档 / 写盘失败）', 'readme health comment')
write(p, s)

# ---------------- 证据文档 ----------------
doc = '''# V7 交接归档快照（阶段 A）· 2026-10-28

> 图里「当前交接 → 归档备份 → 历史会话」那条线，这一版才真的转起来。
> 之前只有一句规矩「旧的搬归档」，没有机制 —— 规矩没有会失败的检查，就只是口号。

## 一、交付物

| 位置 | 内容 |
| --- | --- |
| `dsh/index.js` | 新增 `POST /snapshot`（手动存一份）；`POST /handover` 覆盖写之前**自动归档上一版**；`GET /handover` 带回 `archive` 摘要 |
| `dsh/index.js`（导出） | `snapshotName(when, taken)` 与 `pruneSnapshots(names, keep)` —— 纯函数，可直接测 |
| `dsh/health.js` | 第 17 条判据 `handover:archive`：归档目录可读 / 最新一份非空且含 §〇 / 份数 ≤ 12 |
| `lib/client.js` | 交接面板加「存快照」按钮；副标题显示「归档 N 份」 |
| `_evidence/test-handover.mjs` | 新增 4 条：命名、同分钟加序号、裁剪只碰快照、路由存在 |
| `_evidence/test-health.mjs` | 新增 5 条：1 份 pass / 15 份 fail / 空快照 fail / 无目录 warn / 没配 hub skipped |

## 二、几条不容商量的实现细节

1. **归档目录在项目之外**：`<hubRoot>/archive/<场景id>/`，场景 id 从总工作台的 `projects.json` 按 `root` 反查，查不到退回目录名。所以同一套插件既能单项目用，也能进总工作台。
2. **内容没变就不存**：`POST /handover` 只在「旧内容 ≠ 新内容」时归档。否则连点保存会刷出一串一模一样的快照，把 10 份额度吃满 —— 那等于没有历史。
3. **同一分钟连存两份不覆盖**：`snapshotName` 会加 `-2`、`-3` 后缀。`pruneSnapshots` 按（时间戳, 序号）排序，不用文件名字典序 —— 字典序会把 `-2` 排在无序号前，剪掉真正最新的那份。
4. **裁剪只认快照命名**：`.gitkeep`、手写备注一律不碰。误删别人的文件比不裁剪更糟。
5. **存快照不动原文件**：探针实测 `当前交接.md` 内容与 mtime 都不变。

## 三、验证

```powershell
E:\\Node\\node.exe _evidence\\test-handover.mjs   # 全部通过（反例 + 快照命名/裁剪/路由）
E:\\Node\\node.exe _evidence\\test-health.mjs     # ALL 46 PASSED（每条判据至少红一次）
E:\\Node\\node.exe _evidence\\test-server.mjs     # 13 条接口 ALL SERVER CHECKS PASSED
E:\\Node\\node.exe _evidence\\test-client.mjs / test-scenes.mjs / test-render.mjs
```

真项目探针（项目内 `_交接\\_tools\\probe_archive.mjs`）：`0 份 → 存 1 份 → 内容与当前交接逐字一致 → 原文件未动 → handover:archive = pass`。

## 四、顺带暴露的真问题

体检从「16 全过」变成「14 通过 / 3 警告」，三条都是体量逼近红线：

| 判据 | 实测 | 红线 |
| --- | --- | --- |
| `size:dsh/index.js` | 869 行 / 32151 B | 900 行 / 32768 B |
| `size:dsh/health.js` | 630 行 / 26726 B | 700 行 / 36864 B |
| `size:README.md` | 161 行 / 14058 B | 260 行 / 16384 B |

**不改判据迁就现状**（那是把体检改成安慰剂）。正确做法是先拆：`index.js` 里的交接/归档与待办板各拆成模块，再进阶段 C —— 否则 C 一加必撞线。

## 五、留给下一步

- 拆 `dsh/index.js`：`handover.js`（§〇 判定 + 归档）、`board.js`（待办板解析/保存）各成模块。
- 阶段 C：多项目（读 `projects.json` + 顶栏切换器 + 待办切总板带项目标签）。
- `archive` 目前只有手动与覆盖写触发，还没有「收工自动存」—— 那要等阶段 D 的收工场景。
'''
write(os.path.join(WB, '_evidence', 'v7-2026-10-28.md'), doc)

# ---------------- 本项目 Log v0.23 ----------------
p = os.path.join(GP, 'Log.md')
s = read(p)
entry = '''## v0.23 (2026-10-28)

**责任人**：蔡振辛

### 新增功能：交接归档快照（工作台阶段 A / V7）
- 覆盖写 `_交接/当前交接.md` 之前，自动把上一版存进总工作台 `DSH_Workbench\\archive\\gp-experiment\\`（保留最近 10 份，按时间戳+序号排序裁剪，非快照文件不碰）。
- 新增 `POST /snapshot` 手动存快照；交接面板加「存快照」按钮，副标题显示「归档 N 份」。
- 场景 id 从总工作台 `projects.json` 按项目根反查，查不到退回目录名 —— 同一套插件单项目也能用。
- 体检新增第 17 条判据 `handover:archive`（目录可读 / 最新一份含 §〇 / 份数 ≤ 12），并造了 5 个反例。
- 「内容没变不归档」「同分钟加序号」两条规则是为了不让快照刷成一堆重复品。

### 问题与信号
- 体检从 16 全过变成 **14 通过 / 3 警告**：`dsh/index.js` 869/900 行（96%）、`dsh/health.js` 630/700 行（90%）、`README.md` 161/260 行。**没有改判据迁就现状**，而是把「拆 index.js」记进待办。

### 验证
- 六份自测全过：`test-handover` / `test-health`（46 条）/ `test-server`（13 条接口）/ `test-client` / `test-scenes` / `test-render`。
- 真项目探针 `probe_archive.mjs`：快照落盘、内容逐字一致、原文件未动、`handover:archive = pass`。

### 文件变更
- 工作台仓库：`dsh/index.js`、`dsh/health.js`、`lib/client.js`、`_evidence/test-handover.mjs`、`_evidence/test-health.mjs`、`_evidence/test-server.mjs`、`README.md`、`_evidence/v7-2026-10-28.md`（新）
- 总工作台：`archive\\gp-experiment\\当前交接-20261028-2222.md`（首份快照）、`boards\\待办板.md`
- 本项目：`_交接\\当前交接.md`、`_交接\\待办板.md`、`_交接\\_tools\\patch_a.py`、`_交接\\_tools\\probe_archive.mjs`、`Log.md`

---

'''
s = sub(s, '## v0.22 (2026-10-28)', entry + '## v0.22 (2026-10-28)', 'log')
write(p, s)

# ---------------- 项目内待办板 ----------------
p = os.path.join(GP, '_交接', '待办板.md')
s = read(p)
s = sub(s, '- [ ] 2026-10-28 阶段 A：归档快照（§〇 覆盖前自动存 + 按钮 + 保留最近 10 份 + 体检 1 条判据），快照落 DSH_Workbench\\archive\\gp-experiment\\',
        '- [x] 2026-10-28 阶段 A：归档快照（覆盖写前自动存 + 存快照按钮 + 最近 10 份 + 体检 handover:archive）—— 首份快照 20261028-2222\n'
        '- [ ] 2026-10-28 拆 dsh/index.js（体检 size 已 869/900 行）：交接+归档、待办板各拆一个模块，再进阶段 C', 'board A')
write(p, s)

# ---------------- 总工作台：总板 + 通知看板 ----------------
p = os.path.join(HUB, 'boards', '待办板.md')
s = read(p)
s = sub(s, '- [ ] 【gp-experiment】阶段 A（后补）：归档快照：§〇 覆盖前存一份 + 保留最近 10 份 + 体检 1 条判据',
        '- [x] 【gp-experiment】阶段 A：归档快照（首份 当前交接-20261028-2222.md 已落 archive/gp-experiment）\n'
        '- [ ] 【gp-experiment】先拆 dsh/index.js（869/900 行）再进阶段 C，否则多项目改造必撞体量红线', 'hub board A')
write(p, s)

p = os.path.join(HUB, 'boards', '通知看板.md')
s = read(p)
s = s.rstrip('\r\n') + '\r\n- 2026-10-28 · 阶段 A 完成：交接覆盖写前自动归档到 archive/gp-experiment，保留最近 10 份；体检第 17 条判据上线\n'
write(p, s)

# ---------------- §〇 覆盖写（第 8 次） ----------------
p = os.path.join(GP, '_交接', '当前交接.md')
s = read(p)
start = s.index('## §〇 当前交接')
end = s.find('\n## ', start + 5)
if end < 0:
    end = len(s)
body = '''## §〇 当前交接（覆盖写，不追加 · 第 8 次写 · 2026-10-28）

- **我是谁**：本项目的 AI 协作会话（DSH Desktop）；工作台 = 工作台仓库里的 DSH 插件（V2→V7）；用户与我共用交接层与待办板；方向是「场景 = 项目」的多项目总工作台。
- **上次进度**：阶段 A 完成 —— 交接归档快照：覆盖写前自动把上一版存进总工作台 archive/gp-experiment（首份 当前交接-20261028-2222.md），保留最近 10 份、只认快照命名、内容没变不存、同一分钟加序号；新增 POST /snapshot 与面板「存快照」按钮；体检第 17 条 handover:archive（含 5 个反例）。六份自测全过（体检 46 条、接口 13 条），真项目探针通过。
- **下一步**：① 先拆 dsh/index.js（体检 size 已 869/900 行 = 96%，health.js 630/700 = 90%）—— 交接+归档、待办板各拆一个模块 ② 再进阶段 C：插件多项目（读 projects.json + 顶栏切换器 + 待办切总板带项目标签 + 跨项目一致性判据）③ 阶段 D：场景三件（定位卡/画像/私有记忆）接入收工场景。
- **卡点**：① 改插件后必须重载 DSH Desktop 才生效，验收靠用户 ② 灵枢 cg 写入被 gate 拒收，决策只落文件 ③ 工作台仓库无 git，改动要幂等补丁 + 快照 + 自测还原 ④ 体检 3 条体积警告：index.js / health.js / README 都逼近红线，**不改判据迁就，只能拆** ⑤ 待办仍读写项目内待办板，切总板前有「两份待办」风险。
- **细节在哪**：版本史 → Log.md v0.23；待办唯一落点（临时）→ `_交接/待办板.md`；事实口径 → `5_Reference/AGENTS.md` §三；总工作台规划 → `_交接/总工作台规划_20261028.md`；工作台各版留档 → 工作台仓库 _evidence（v7 = 本次归档，p3/p2 见前）。
'''
s = s[:start] + body + s[end:]
write(p, s)
print('records ok; s0 bytes =', len(body.encode('utf-8')))
