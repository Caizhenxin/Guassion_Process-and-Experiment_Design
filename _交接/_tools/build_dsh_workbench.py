import io, os, json

WB = r'D:\GitHub_programe\GitHub\DSH_Workbench'
GP = r'D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design'

def w(rel, text):
    p = os.path.join(WB, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    io.open(p, 'w', encoding='utf-8', newline='\r\n').write(text)
    return p

# ---------- projects.json ----------
projects = {
    "version": 1,
    "note": "场景 = 项目 登记表。root 必须是被登记项目的绝对路径；handover/log/facts 是相对 root 的路径。改这里不需要动插件代码。",
    "projects": [
        {
            "id": "gp-experiment",
            "name": "Guassion-Process-Experiment-Design",
            "kind": "research",
            "root": GP,
            "handover": "_交接\\当前交接.md",
            "board": "boards\\待办板.md",
            "log": "Log.md",
            "facts": "5_Reference\\AGENTS.md",
            "sceneDir": "scenes\\gp-experiment",
            "session": {"id": None, "title": None, "updated": None},
            "status": "active",
            "registered": "2026-10-28"
        }
    ]
}
w('projects.json', json.dumps(projects, ensure_ascii=False, indent=2) + '\r\n')

# ---------- AGENTS.md（注入层，短） ----------
w('AGENTS.md', '''# 总工作台 · 注入层（越短越好）

这是**总工作台**的家：只放"跨项目才知道"的东西，不放任何项目的正文。

## 去哪找
| 想知道 | 看哪 |
| --- | --- |
| 有哪些场景（=项目）、根路径在哪 | `projects.json` |
| 该做什么（全机唯一待办） | `boards\\待办板.md`（行首带【项目 id】） |
| 东西在哪、什么状态 | `index\\总索引.md`（活 / 常备180天 / 留档 / 待清7天） |
| 某个场景我是谁、怎么干活 | `scenes\\<项目id>\\定位卡.md`、`画像.md` |
| 某个场景的长期结论 | `scenes\\<项目id>\\私有记忆.md`（只追加） |
| 交接的历史版本 | `archive\\<项目id>\\` |

## 三条铁律
1. **同一事实只存一处**：进度在项目根 `_交接\\当前交接.md`；身份在 `scenes\\`；待办在 `boards\\`；数字在项目的事实口径。谁都不许复制。
2. **这里不写正文**：项目里的结论、报错原文、临时路径都不进本目录。
3. **只登记不强求**：新项目只登记 id + root + 名称就能用；没建交接文件不报错。

## 项目侧约定（每个被登记的仓库）
`_交接\\当前交接.md`（§〇 覆盖写、≤4096 字节、四问：我是谁 / 干到哪 / 下一步 / 卡在哪）+ `Log.md`（版本史）+ 事实口径文件（数字唯一出处）。
''')

# ---------- 待办板（迁移中） ----------
w('boards\\待办板.md', '''# 待办板（全机唯一落点）

规则：同一件事只许一行；行首 `【项目id】` 标归属；完成打 `[x]`；老于 30 天的已完成行搬 `index\\总索引.md` 的留档区。

> 迁移中（2026-10-28）：插件当前仍读写项目内 `<项目根>\\_交接\\待办板.md`，**那仍是临时唯一落点**。
> 阶段 C 把插件切到这里之后，本文件才成为唯一落点；在那之前不要在两处同时记待办。

- [ ] 【gp-experiment】阶段 B：建总工作台骨架（本目录）并 git init
- [ ] 【gp-experiment】阶段 C：插件切到总板 + 顶栏项目切换器
- [ ] 【gp-experiment】阶段 A（后补）：归档快照：§〇 覆盖前存一份 + 保留最近 10 份 + 体检 1 条判据
- [ ] 【gp-experiment】阶段 D：场景三件（定位卡 / 画像 / 私有记忆）+ 收工场景显示
''')

# ---------- 通知看板 ----------
w('boards\\通知看板.md', '''# 通知看板（发生了什么）

只追加，写完不再改；一行一条，`日期 · 一句话`。超过 50 行或老于 90 天的搬 `index\\总索引.md` 留档区。

- 2026-10-28 · 总工作台骨架建成：projects.json / boards / index / scenes / archive，登记第一个场景 gp-experiment
''')

# ---------- 总索引 ----------
w('index\\总索引.md', '''# 总索引（东西在哪 + 什么状态）

四状态：**活**（每天用）· **常备**（180 天不动就降级）· **留档**（只读留证）· **待清**（7 天内处理，否则删或搬）。

## 活
| 东西 | 位置 | 说明 |
| --- | --- | --- |
| 场景登记表 | `projects.json` | 场景 = 项目 |
| 待办板 | `boards\\待办板.md` | 全机唯一（阶段 C 起生效） |
| 场景身份 | `scenes\\gp-experiment\\` | 定位卡 / 画像 / 私有记忆 |
| GP 项目进度 | `<GP root>\\_交接\\当前交接.md` §〇 | 覆盖写，≤4096 字节 |

## 常备
| 东西 | 位置 | 上次用到 |
| --- | --- | --- |
| 工作台插件源码 | `D:\\GitHub_programe\\GitHub\\dsh-my-project-workbench` | 2026-10-28 |
| 淋雨家全量参考 | `dsh-my-project-workbench\\docs\\reference\\luanyujia-workbench-main` | 2026-10-28 |
| 失败案例库 | `D:\\GitHub_programe\\GitHub\\Self-Repo\\AI_Self_Improvement` | 2026-10-28 |

## 留档
| 东西 | 位置 | 为什么留 |
| --- | --- | --- |
| 工作台 V4/V5/V6 证据 | `dsh-my-project-workbench\\_evidence\\` | 每版判定与翻车留档 |
| 旧参考包（2026-10-22 部分抓取） | `dsh-my-project-workbench\\docs\\reference\\2026-10-22-旧参考包` | 早期 HTML 对照 |

## 待清
| 东西 | 位置 | 期限内要做的 |
| --- | --- | --- |
| （空） | | |
''')

# ---------- 场景三件 ----------
w('scenes\\gp-experiment\\定位卡.md', '''# 定位卡 · gp-experiment

> 体量红线：≤4 KB。只写"我是谁、去哪找、怎么判"，不写进度（进度在项目 `_交接\\当前交接.md`）。

## 身份与职责
- 我是 **Guassion-Process-Experiment-Design** 这个实验项目的 AI 协作会话。
- 职责：实验设计与统计口径、数据清理与建模、论文（10 章）、可视化与交付。
- 机主：蔡振辛（中文交流；他要的是"能验算的结论"，不是漂亮话）。

## 资产地图（都在项目根下，别复制内容）
| 要什么 | 去哪 |
| --- | --- |
| 干到哪 / 下一步 / 卡在哪 | `_交接\\当前交接.md` §〇 |
| 数字与口径（唯一出处） | `5_Reference\\AGENTS.md` §三 事实口径 |
| 版本史与每次交付 | `Log.md` |
| 脚本与中间结果 | 项目内 `_tools\\`、`artifacts\\` 等实际目录 |
| 失败教训（跨项目） | `D:\\GitHub_programe\\GitHub\\Self-Repo\\AI_Self_Improvement\\INDEX.md` |

## 触发词 → 去哪
- 「上次做到哪」→ 读 §〇
- 「这个数字对不对」→ 先查事实口径，再查 Log 对应版本
- 「改统计口径」→ 先改事实口径一处，再重算，最后记 Log
- 「出图/出表」→ 先看已有 `artifacts`，避免重造

## 铁律
1. 数字只认事实口径一处；两处打架先去重，不许"哪个好看用哪个"。
2. 口径变更必须先写进事实口径再重算，不许边算边改。
3. 交付前自检：能不能用一条命令复现。
''')

w('scenes\\gp-experiment\\画像.md', '''# 场景画像 · gp-experiment

> 这个场景**怎么干活**（偏好、禁忌、常用流程）。体量红线 ≤4 KB。

## 机主偏好
- 中文优先；结论先行，再给证据。
- 反感"看起来对"：要能验算的数字、能重复的命令、能指认的路径。
- 长任务要分批交付并留可回滚点，不要一口气改十个文件。

## 禁忌
- 不擅自改统计口径（改必先说、先落事实口径）。
- 不把旧数据（如旧 87 人样本）混进新口径做主结论。
- 不在两处存同一事实（账本/待办/口径都只有一处）。
- 不用"可能/大概"掩盖没查清的事，查不清就说查不清。

## 常用流程
1. 开工：读 §〇 四问 → 查失败案例库 → 跑峰谷闸门 → 再动手。
2. 计算：先小样本试跑 → 断言检查（量纲/数量级）→ 全量 → 落 artifacts。
3. 收工：覆盖写 §〇（四问）+ 记 Log + 更新待办板。
4. 交付：给数字 + 复现命令 + 文件路径，三样齐。

## 环境
- Windows + pwsh；Python 用 `-X utf8` 避免编码事故；Node 在 `E:\\Node\\node.exe`。
- 网络受限：GitHub 直连不通，以本地副本为准。
''')

w('scenes\\gp-experiment\\私有记忆.md', '''# 私有记忆 · gp-experiment（只追加，不覆盖）

写法：一行一条结论 + 日期，写完不回头改；过期的加 `→ 已被 X 取代`。红线 ≤12 KB，超了先搬 `archive\\`。

- 2026-10-28 交接的意义不是留档，是让下一个会话能接着干：§〇 只答四问，细节留指针。
- 2026-10-28 规矩要能落成"会失败的检查"才算数；不能失败的规矩只是口号。
- 2026-10-28 判据红了先修事实，不许改判据迁就现状（唯一例外：判据本身写错了，要留下改判据的理由）。
- 2026-10-28 跨仓库的文件路径别用反引号写进 §〇，体检会把它当"项目内不存在的文件"判红。
''')

# ---------- archive 占位 ----------
w('archive\\gp-experiment\\.gitkeep', '')

# ---------- .gitignore ----------
w('.gitignore', '''# 归档快照不进 git（体积大、可重建），只保留最近几份在本机
archive/**/*
!archive/**/.gitkeep

# 临时与系统文件
*.tmp
*.bak
~$*
Thumbs.db
desktop.ini
.DS_Store

# 隐私：任何密钥/令牌
*.key
*.pem
.env
.env.*
''')

# ---------- README ----------
w('README.md', '''# DSH_Workbench · 总工作台

以"场景 = 项目"组织的工作台**记忆与索引的家**。项目正文不在这里，这里只放跨项目才知道的东西。

| 文件 | 作用 |
| --- | --- |
| `projects.json` | 场景（=项目）登记表：id / 名称 / root / 会话绑定 |
| `boards\\待办板.md` | 全机唯一待办落点（行首带【项目 id】） |
| `boards\\通知看板.md` | 发生了什么（只追加） |
| `index\\总索引.md` | 东西在哪、什么状态（活/常备/留档/待清） |
| `scenes\\<项目id>\\` | 定位卡 / 画像 / 私有记忆（身份与长期结论） |
| `archive\\<项目id>\\` | 交接的历史快照（不进 git） |

## 为什么这样分

- **身份与长期记忆**（我是谁、怎么干活、学到什么）跟着场景走 → `scenes\\`
- **进度与资料**（干到哪、文件在哪）跟着项目走 → 项目根 `_交接\\`、`Log.md`、实际文件
- 两者不重复存同一事实：这是这套东西最容易烂掉的地方。

## 给自己看的边界

- 本目录不是代码仓库主体；工作台插件源码在 `D:\\GitHub_programe\\GitHub\\dsh-my-project-workbench`。
- 插件当前仍按单个 `projectRoot` 工作；多项目切换在阶段 C 实现（见项目内 `_交接\\总工作台规划_20261028.md`）。
''')

print('files written')
for root, dirs, files in os.walk(WB):
    for f in files:
        p = os.path.join(root, f)
        print('%-52s %6d B' % (os.path.relpath(p, WB), os.path.getsize(p)))
