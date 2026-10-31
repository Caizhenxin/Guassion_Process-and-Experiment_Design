import io

# ============ ① Log.md v0.20 ============
log = r'D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\Log.md'
s = io.open(log, encoding='utf-8').read()

entry = '''## v0.20 (2026-10-28)

**责任人**：蔡振辛

### 新增功能：工作台体检层（V5）
- 工作台仓库 `dsh-my-project-workbench` 新增 `dsh/health.js`，**13 条判据**：体量 4 + 索引 5（面板表 / `__test.panels` / 接口表 / 自测脚本 / 正文数字）+ 交接 3（§〇 四问齐全 / 距今新鲜度 / 指针指向的文件存在）+ 待办板 1（身份键合法）。
- 新增接口 `health`：`GET` 只读出报告（`status` + 每条判据实测值 + `digest`），`POST {append:true}` 才把 ⛔ 项写进 `_交接/待办板.md`（同一件只留一行，`[x]` 记 `staleDone` 不算已修）。
- 「当前交接」面板下半截显示体检读数（状态 + 通过/警告/失败 + 最多 5 行 digest），一个按钮「跑体检并记待办」。
- 实现规矩四条：`scanned===0` 一律 fail；索引锚点不命中即 fail；量纲用磁盘字节与 `\\n` 计数；阈值定在预算位置（越 85% 告警），「会红」由 38 条反例证明而非生产环境常红。

### 问题修复（体检第一天抓出的三个真问题）
- **两段判定缺失**：初版用项目根找 `lib/client.js`，换项目就全红 → 拆成「工作台自身」与「当前项目」两段判定。
- **`__test.panels` 少 2 项**（缺 `handover`/`arch`）：测试少覆盖两个面板 → 补齐为 12↔12。
- **§〇 里混入跨仓库路径**：指向工作台仓库的 `_evidence/v4-2026-10-28.md`，项目根里不存在 → 改为普通文字说明归属。

### 验证
- `test-client` / `test-handover` / `test-render` / `test-server` / `test-health` 五份全部 `PASSED`（`test-health` 38 条检查，13 条判据各造红至少一次）。
- 真项目只读探针：`13 条判据：13 通过 / 0 警告 / 0 失败`，§〇 2499/4096 字节，四问齐全。

### 文件变更
- 工作台仓库：新增 `dsh/health.js`、`_evidence/test-health.mjs`、`_evidence/p2-2026-10-28.md`；改 `dsh/index.js`、`lib/client.js`、`_evidence/test-server.mjs`、`README.md`（V5 章节）
- 本项目：`_交接/当前交接.md`（§〇 覆盖写）、`_交接/待办板.md`、`Log.md`

---

'''

anchor = '## v0.19 (2026-10-28)'
assert s.count(anchor) == 1, 'log anchor'
s = s.replace(anchor, entry + anchor)
io.open(log, 'w', encoding='utf-8', newline='\r\n' if '\r\n' in s else '\n').write(s)
print('Log v0.20 ok')

# ============ ② 待办板 ============
board = r'D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\_交接\待办板.md'
b = io.open(board, encoding='utf-8').read()
b = b.replace(
    '- [ ] 2026-10-28 P1 验收：重启 DSH Desktop 后确认「当前交接」面板出现、能读能写、缺字段标红',
    '- [x] 2026-10-28 P1 验收：重启后「当前交接」面板已挂载（体检 `index:panels`/`index:testpanels` 12↔12 双向锁定）')
b = b.replace(
    '- [ ] 2026-10-28 P2 开工：体检脚本（体量红线 / 索引对不上 / §〇 超线）+ ⛔ 自动追加进本板（同件一行去重）',
    '- [x] 2026-10-28 P2 完成：体检 13 条判据 + `health` 接口 + 交接面板读数（见工作台 `_evidence/p2-2026-10-28.md`）\n'
    '- [ ] 2026-10-28 P2 重启验收：交接面板下半截能看到「全绿 · 13 条」和「跑体检并记待办」按钮\n'
    '- [ ] 2026-10-28 P3 开工：场景配置驱动（`scenes.json`）+ 体检独立面板')
io.open(board, 'w', encoding='utf-8', newline='\r\n' if '\r\n' in b else '\n').write(b)
print('board ok')

# ============ ③ §〇 当前交接（覆盖写） ============
ho = r'D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\_交接\当前交接.md'
h = io.open(ho, encoding='utf-8').read()
start = h.index('## §〇 当前交接')
end = h.find('\n## §一', start)
assert start > 0 and end > start, 'section anchor'

body = '''## §〇 当前交接（覆盖写，不追加 · 第 4 次写 · 2026-10-28）

- **我是谁**：本项目的 AI 协作会话（DSH Desktop），工作台 = `dsh-my-project-workbench` 插件，用户与我共用这套交接层与待办板。
- **干到哪**：工作台 **V5 体检层（P2）已完成**——`dsh/health.js` 13 条判据、`health` 接口（GET 只读 / POST 才写待办板）、交接面板下半截显示读数；五份自测全绿（`test-health` 38 条检查），真项目探针 `13 通过 / 0 警告 / 0 失败`。此前 V4 交接层（P1）已上线。
- **下一步**：① 等用户重启 DSH Desktop 验收交接面板读数 ② P3 = 场景配置驱动（`scenes.json`）+ 体检独立面板（细节见待办板与工作台 `_evidence/p2-2026-10-28.md`）。
- **卡点**：① 改插件后必须重载 DSH Desktop 才生效，面板验收只能靠用户眼睛 ② `cg(op=write)` 连续 3 次被 gate 拒收（缺出处标记/条件空间），决策只落文件不进 cg ③ 工作台仓库**无 git**，任何改动都要幂等补丁 + 快照。
- **细节在哪**：进度与版本 → 本项目 `Log.md` v0.20；待办唯一落点 → `_交接/待办板.md`；事实口径 → `5_Reference/AGENTS.md` §三；工作台改动与翻车留档 → 工作台仓库 `_evidence/p2-2026-10-28.md`（V4 见 v4-2026-10-28.md）；参考实现 → 工作台仓库 `docs/reference/luanyujia-workbench-main/`（记忆机制看 `00-核心机制/二-记忆机制.md`，规矩机械化看 `08-升级与改造清单/`）。
'''
h = h[:start] + body + h[end:]
io.open(ho, 'w', encoding='utf-8', newline='\r\n' if '\r\n' in h else '\n').write(h)
print('§〇 ok, bytes =', len(h.encode('utf-8')))
