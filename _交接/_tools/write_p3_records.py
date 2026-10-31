import io, os

WB = r'D:\GitHub_programe\GitHub\dsh-my-project-workbench'
GP = r'D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design'

def read(p):
    return io.open(p, encoding='utf-8').read()

def write(p, s, crlf=False):
    io.open(p, 'w', encoding='utf-8', newline='\r\n' if crlf else '\n').write(s)

def sub(s, old, new, label):
    assert s.count(old) == 1, 'anchor %s: %d' % (label, s.count(old))
    return s.replace(old, new)

# ---------------- README：判据条数与自测条数 ----------------
p = os.path.join(WB, 'README.md')
s = read(p)
s = sub(s, '`dsh/health.js` 跑 15 条判据（5 体量 + 5 索引 + 2 交接 + 1 待办板 + 1 指针 + 1 场景配置）',
        '`dsh/health.js` 跑 16 条判据（5 体量 + 5 索引 + 2 交接 + 1 待办板 + 1 指针 + 2 场景配置）', 'readme rules count')
s = sub(s, '# 体检：38 条检查（零扫描 / 量纲 / 锚点 / 幂等 / 两段判定 / 写盘失败）',
        '# 体检：41 条检查（零扫描 / 量纲 / 锚点 / 幂等 / 两段判定 / 场景表 / 写盘失败）', 'readme health count')
write(p, s)

# ---------------- P3 证据文档 ----------------
doc = '''# V6 场景配置驱动（P3）· 2026-10-28

> 判据来源同 V5：`docs/reference/luanyujia-workbench-main/08-升级与改造清单/`（规则要能落成会失败的检查）。
> 本版只做「版式可配置 + 配置本身进体检」，不引入任何新依赖。

## 一、交付物

| 位置 | 内容 |
| --- | --- |
| `dsh/scenes.js`（新，231 行） | `DEFAULT_SCENES` + `ALL_PANEL_IDS` + `validateScenes()` + `readScenes()` + `panelSetOf()` + `scenesSummary()` |
| `scenes.json`（新，根目录） | 覆盖文件：当前 4 个场景（项目总览 / 文件与产物 / 写作与汇报 / 收工） |
| `dsh/index.js` | 新增 `scenes` 路由：GET 只读，返回 `scenes` + `source`(file/default) + `problems` + `drift` |
| `lib/client.js` | `SCENES` 改为可替换；`applySceneConfig()` 客户端二次校验；拉不到／校验不过退回内置兜底并在顶栏说明；`nodeFor` 对未知 id 返回 null（不再渲染成对话面板） |
| `dsh/health.js` | 新增 2 条判据：`config:scenes`（可解析/面板 id 合法/同场景不重复）、`config:scenes-readme`（README 场景表 ↔ 生效场景） |
| `_evidence/test-scenes.mjs`（新） | 14 条检查：8 条校验器反例 + 3 种来源（没有/坏了/合法） |

## 二、为什么「配置只读」

配置不给面板写入口：版式写坏时页面往往**看起来正常**（只是少一块），比直接报错难查一个数量级。
所以配置只许用编辑器改，改错了 `config:scenes` 会 fail，并在顶栏说明已退回内置默认。

## 三、四条校验（都有反例）

1. **未知面板 id → 整份退回默认**。以前 `nodeFor` 的兜底是把未知 id 渲染成 AI 对话面板 —— 认错面板比空白更糟。
2. **同一场景里重复面板 → 整份退回默认**。宿主会话节点会被挂两次，切场景就串台。
3. **场景 id 重复 / 大写带空格 → 退回默认**。id 要当 localStorage 键与标签排序键。
4. **坏 JSON / 空 rows / 顶层不是对象 → 退回默认**，但 `problems` 必须原样交回客户端，顶栏提示一句。

`g` / `w` 写错类型不算错，回落 1 —— 那是排版偏好，不是结构性错误。

## 四、体检抓到的两件事

1. **新增 `scenes` 路由后 README 仍是「11 条接口」**：`index:routes` 双向比对当场 fail（README 多 0 / 代码多 1）。
2. **我给 `dsh/scenes.js` 加了体量红线，但 test-health 的夹具没建这个文件** → `size:dsh/scenes.js` 报「索引指着不存在的文件」，随后「追加 1 行」变 2 行、幂等断言连带失败。修法：夹具补 `dsh/scenes.js` 桩文件，并注明「夹具故意不建 scenes.json，走 warn 路径」。

## 五、验收

```powershell
cd D:\\GitHub_programe\\GitHub\\dsh-my-project-workbench
E:\\Node\\node.exe _evidence\\test-client.mjs    # 12 个面板注册契约
E:\\Node\\node.exe _evidence\\test-scenes.mjs    # ALL 14 PASSED
E:\\Node\\node.exe _evidence\\test-handover.mjs  # 三个反例都报错
E:\\Node\\node.exe _evidence\\test-render.mjs    # A–I 场景/版式
E:\\Node\\node.exe _evidence\\test-server.mjs    # 12 条接口
E:\\Node\\node.exe _evidence\\test-health.mjs    # ALL 41 PASSED（16 条判据，每条至少造红一次）
```

真项目探针：`16 条判据：16 通过 / 0 警告 / 0 失败`；`config:scenes` = 4 个场景来自 scenes.json；
`config:scenes-readme` = 4 个场景两边一致。

## 六、留给下一步

- **体检独立面板**（现在读数寄生在交接面板下半截）：要给 `HealthPanel` 加组件、`ALL_PANELS` 13、README 面板表加行。
- 面板类型扩充（P3 原计划里的 24 类只抄了 12 类）：`chart` / `flow` / `site-preview` 之类。
- `scenes.json` 目前只管「放哪些面板、几列几行」，还不管「每个面板高度上限 / 是否默认展开」。
- 第 4 个场景「收工」是纯配置新增（没改一行代码），可作为以后加场景的样板。
'''
write(os.path.join(WB, '_evidence', 'p3-2026-10-28.md'), doc)

# ---------------- 本项目 Log v0.21 ----------------
log = os.path.join(GP, 'Log.md')
s = read(log)
entry = '''## v0.21 (2026-10-28)

**责任人**：蔡振辛

### 新增功能：工作台场景配置驱动（V6 / P3）
- 版式从 `lib/client.js` 硬编码搬进插件根目录 **`scenes.json`**：加场景/调分栏只改配置，不动代码。新增 `GET /scenes` 只读接口；配置坏了整份退回内置默认，并把问题原文交回客户端（顶栏提示）。
- 新增 `dsh/scenes.js`：`DEFAULT_SCENES` + `ALL_PANEL_IDS` + 校验器（未知面板 id / 同场景重复面板 / 场景 id 重复 / 空 rows / 坏 JSON 全部 fail）+ `readScenes()` 区分「没有文件」「文件坏了」「文件合法」三种来源。
- 第 4 个场景 **「收工」**（左：当前交接；右：待办 + 便利贴）是**纯配置新增**，没有改一行代码 —— 作为以后加场景的样板。
- 体检从 13 条扩到 **16 条**：新增 `config:scenes`（配置本身合法）与 `config:scenes-readme`（README 场景表 ↔ 生效场景，防止「只改配置忘了改文档」）。
- 客户端 `nodeFor` 对未知面板 id 改为返回空 —— 以前会把未知 id 悄悄渲染成 AI 对话面板。

### 问题修复
- 新增 `scenes` 路由后 README 未同步（仍写「11 条接口」），被 `index:routes` 双向比对当场抓出 → 改为 12 条。
- `dsh/scenes.js` 加了体量红线后，`test-health` 夹具缺该文件，导致 3 条断言连带失败 → 夹具补桩文件。

### 验证
- 六份自测全部通过：`test-client` / `test-scenes`(14) / `test-handover` / `test-render` / `test-server`(12 接口) / `test-health`(41 条检查)。
- 真项目探针：`16 条判据：16 通过 / 0 警告 / 0 失败`。

### 文件变更
- 工作台仓库：新增 `dsh/scenes.js`、`scenes.json`、`_evidence/test-scenes.mjs`、`_evidence/p3-2026-10-28.md`；改 `dsh/index.js`、`dsh/health.js`、`lib/client.js`、`_evidence/test-server.mjs`、`_evidence/test-health.mjs`、`README.md`
- 本项目：`_交接/当前交接.md`、`_交接/待办板.md`、`Log.md`

---

'''
s = sub(s, '## v0.20 (2026-10-28)', entry + '## v0.20 (2026-10-28)', 'log anchor')
write(log, s, crlf=('\r\n' in s))

# ---------------- 待办板 ----------------
board = os.path.join(GP, '_交接', '待办板.md')
b = read(board)
b = b.replace('- [ ] 2026-10-28 P3 开工：场景配置驱动（`scenes.json`）+ 体检独立面板',
              '- [x] 2026-10-28 P3 完成：`scenes.json` 配置驱动 + 第 4 个场景「收工」（纯配置新增）+ 体检 16 条判据\n'
              '- [ ] 2026-10-28 P3 重启验收：顶栏出现 4 个场景标签，点「收工」看到交接 + 待办 + 便利贴\n'
              '- [ ] 下一步 P4 候选：体检独立面板（要动代码）/ 面板类型扩充（chart、flow、site-preview）')
write(board, b, crlf=('\r\n' in b))

# ---------------- §〇 覆盖写 ----------------
ho = os.path.join(GP, '_交接', '当前交接.md')
h = read(ho)
start = h.index('## §〇 当前交接')
end = h.find('\n## ', start + 5)
if end < 0:
    end = len(h)
body = '''## §〇 当前交接（覆盖写，不追加 · 第 6 次写 · 2026-10-28）

- **我是谁**：本项目的 AI 协作会话（DSH Desktop）；工作台 = 工作台仓库里的 DSH 插件（V2→V6 由我实现）；用户与我共用这套交接层与待办板。
- **上次进度**：工作台 V6 场景配置驱动（P3）已完成 —— 版式搬进 `scenes.json`（4 个场景，第 4 个「收工」是纯配置新增）、`GET /scenes` 只读接口、配置坏了整份退回默认并报给顶栏；体检从 13 条扩到 16 条（新增配置合法性与 README 场景表一致性）；六份自测全绿（体检 41 条检查），真项目探针 16 通过 / 0 警告 / 0 失败。
- **下一步**：① 等用户重启 DSH Desktop 验收：顶栏 4 个场景标签 + 「收工」场景 ② P4 二选一：体检独立面板（要动代码）或面板类型扩充（chart / flow / site-preview）。
- **卡点**：① 改插件后必须重载 DSH Desktop 才生效，验收只能靠用户眼睛 ② 灵枢 cg 写入连续被 gate 拒收（缺出处标记 / 条件空间），决策只落文件、不进 cg ③ 工作台仓库没有 git，任何改动都要幂等补丁 + 快照 + 自测还原 ④ `lib/client.js` 已 2100+ 行（红线 2600），加面板要小心体量。
- **细节在哪**：进度与版本 → `Log.md` v0.21；待办唯一落点 → `_交接/待办板.md`；事实口径 → `5_Reference/AGENTS.md` §三；工作台改动与翻车留档 → 工作台仓库 _evidence/p3-2026-10-28.md（V5 见 p2-2026-10-28.md，V4 见 v4-2026-10-28.md）；版式配置 → 工作台仓库 scenes.json；参考实现 → 工作台仓库 docs/reference/luanyujia-workbench-main\\。
'''
h = h[:start] + body + h[end:]
write(ho, h, crlf=('\r\n' in h))
print('records done; handover bytes =', len(h.encode('utf-8')))
