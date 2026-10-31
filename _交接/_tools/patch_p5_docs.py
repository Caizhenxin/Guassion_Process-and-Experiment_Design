"""P5 补丁 3：体检键格式与 Python 体检器统一 + README 反映「待办只一处」。"""
import io

WB = r'D:\GitHub_programe\GitHub\dsh-my-project-workbench'

edits = [
    # ---- health.js：键改成 <!--体检:id-->，与 tools\体检.py 同一套 ----
    ('dsh/health.js',
     '⟦health:<ruleId>⟧。全角括号避开 markdown 与代码块语法。',
     '<!--体检:<ruleId>-->。与总工作台 tools\\体检.py 共用一套键 —— 一行两种格式，'
     '等于同一条问题被两个体检器各追加一次，去重就白做了。'),
    ('dsh/health.js',
     'export const HEALTH_KEY = /⟦health:([^\\s⟧]+)⟧/',
     'export const HEALTH_KEY = /<!--\\s*体检:([^>]+?)-->/'),
    ('dsh/health.js',
     "line.includes('⟦health:')",
     '/<!--\\s*体检:/.test(line)'),
    ('dsh/health.js',
     "' 行有 ⟦health: 但键不合法'",
     "' 行有 <!--体检: 但键不合法'"),
    ('dsh/health.js',
     "' ⟦health:' + rule.id + '⟧'",
     "' <!--体检:' + rule.id + '-->'"),
    # ---- test-health：跟着改断言 ----
    ('_evidence/test-health.mjs',
     '/⛔ .*⟦health:size:lib\\/client\\.js⟧/.test(text)',
     '/⛔ .*<!--体检:size:lib\\/client\\.js-->/.test(text)'),
    ('_evidence/test-health.mjs',
     '- [x] 2026-10-27 ⛔ 体量超线 ⟦health:size:lib/client.js⟧\\n',
     '- [x] 2026-10-27 ⛔ 体量超线 <!--体检:size:lib/client.js-->\\n'),
    ('_evidence/test-health.mjs',
     "check('键是全角括号 ⟦⟧', line.includes('⟦health:') && line.includes('⟧'))",
     "check('键是 HTML 注释（与 tools/体检.py 同格式）', /<!--体检:/.test(line) && line.includes('-->'))"),
    # ---- README ----
    ('README.md',
     '| 待办清单 | 勾选、删除、回车添加，同样存在 DSH 用户数据目录 |',
     '| 待办清单 | 勾选、删除、回车添加；落**总工作台** `boards/待办板.md`，每行带 `【项目id】`，'
     '只重写本项目那几行 |'),
    ('README.md',
     '⛔ 行的身份键是行尾 `⟦health:<ruleId>⟧`：全等比较、不用 `includes`',
     '⛔ 行的身份键是行尾 `<!--体检:<ruleId>-->`（与总工作台 `tools/体检.py` 同一格式，'
     '否则同一条问题会被两个体检器各追加一次）：全等比较、不用 `includes`'),
    ('README.md',
     '| `todos` | GET 读 / POST 存，落**项目内** `_交接/待办板.md`（唯一落点）；'
     '老数据首次读取时自动从 DSH 数据目录迁过来 |',
     '| `todos` | GET 读 / POST 存，落**总工作台** `boards/待办板.md`（唯一落点，每行带项目标签）；'
     '只重写本项目那几行，别人的行与人写的说明原样保留 |'),
    ('README.md',
     'E:\\Node\\node.exe _evidence\\test-scenes.mjs    # 场景配置：14 条检查（未知面板 / 重复面板 / 坏 JSON / 三来源）',
     'E:\\Node\\node.exe _evidence\\test-scenes.mjs    # 场景配置：14 条检查（未知面板 / 重复面板 / 坏 JSON / 三来源）\n'
     'E:\\Node\\node.exe _evidence\\test-board.mjs     # 待办板：11 条检查（标签 / 合并 / 别人的行不许动 / 迁移）'),
    ('README.md',
     '六份都输出 `ALL ... PASSED`。',
     '七份都输出 `ALL ... PASSED`。'),
]

V7 = '''
## V7：待办收成一处 + 覆盖写前自动归档（2026-10-29）

上一版把待办落在项目内的 `_交接/待办板.md`，那是「试行版」的遗产：同一个人的活散在两个仓库里，
总工作台的工具看不见它。V7 收成一处：

1. **待办只有一处**：`DSH_Workbench/boards/待办板.md`，每行 `- [ ] YYYY-MM-DD 【项目id】事项`。
   项目 id 由 `projects.json` 的 `root` 反查；读回来时标签自动剥掉，界面上还是干净的一句话。
2. **只重写本项目那几行**（`dsh/board.js` 的 `mergeTagBlock`）：别人的行、人写在列表之外的说明、
   小节标题一个字都不动 —— 上一版整篇重写会静默吃掉手写的备注。
3. **覆盖写前先归档**：`POST /snapshot` 手动存一份、`POST /handover` 覆盖写之前自动存一份，
   都落 `DSH_Workbench/archive/<项目id>/`，与总工作台 `tools/交接.py` 共用命名 `交接-YYYYMMDD-HHMMSS.md`
   和 10 份上限；面板上的「存快照」按钮就是这条接口。
4. **体检键与 Python 体检器统一**：行尾身份键从 `⟦health:<id>⟧` 改成 `<!--体检:<id>-->`。

自测也跟着改了，原因值得留档：`test-server.mjs` 原来直接往**真项目**的待办板 POST，靠「退出时还原」兜底 ——
那是在补救「写错了地方」，不如一开始就别写那儿。V7 把自测整个跑在**临时总工作台**里
（`mkdtemp` + 一份夹具板），`test-board.mjs` 连磁盘都不碰，只判合并规则。
另外 `doc` 接口的自测原来指着项目里某个真实 HTML 产物，产物一改名就假红 —— 改成自建夹具。
'''

cache = {}
for rel, old, new in edits:
    if rel not in cache:
        cache[rel] = io.open(WB + '\\' + rel.replace('/', '\\'), encoding='utf-8').read()
    src = cache[rel]
    if old in src:
        cache[rel] = src.replace(old, new, 1)
        print('  patch', rel, '|', old[:34].replace('\n', ' '))
    elif new in src:
        print('  skip (already)', rel)
    else:
        raise SystemExit('ANCHOR MISS in ' + rel + ': ' + old[:60])

# README 末尾追加 V7
src = cache['README.md']
if '## V7：待办收成一处' not in src:
    src = src.rstrip('\n') + '\n' + V7
    cache['README.md'] = src
    print('  append V7')

for rel, body in cache.items():
    path = WB + '\\' + rel.replace('/', '\\')
    io.open(path, 'w', encoding='utf-8', newline='\n').write(body.replace('\r\n', '\n'))
    print('written', rel, len(body), 'chars')
