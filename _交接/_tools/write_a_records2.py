"""阶段 A 收尾（第二次跑）：记录真实状态 —— 命名统一 + 待办只剩总板 + §〇 第 8 次写。"""
import io
import os

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


# ---------------- 1. Log.md：改掉不实的文件清单 + 补命名统一 ----------------
p = os.path.join(GP, 'Log.md')
s = read(p)
s = sub(s,
        '- 总工作台：`archive\\gp-experiment\\当前交接-20261028-2222.md`（首份快照）、`boards\\待办板.md`',
        '- 总工作台：`archive\\gp-experiment\\交接-20261028-222200.md`（首份快照，命名已与 `tools\\交接.py` 统一）',
        'log hub files')
s = sub(s,
        '- 本项目：`_交接\\当前交接.md`、`_交接\\待办板.md`、`_交接\\_tools\\patch_a.py`、`_交接\\_tools\\probe_archive.mjs`、`Log.md`',
        '- 本项目：`_交接\\当前交接.md`、`_交接\\_tools\\patch_a.py`、`_交接\\_tools\\patch_a2_unify.py`、'
        '`_交接\\_tools\\probe_archive.mjs`、`_交接\\_tools\\write_a_records.py`、`Log.md`\n'
        '\n'
        '### 补充：快照命名统一（同日晚）\n'
        '- 发现总工作台 `tools\\交接.py`（M3.3）早就在写同一个 `archive\\<id>\\` 目录，命名是 `交接-YYYYMMDD-HHMMSS.md`；插件侧原来是 `当前交接-YYYYMMDD-HHMM.md`。\n'
        '- **两个入口、两套 glob、各留 10 份 ⇒「保留最近 10 份」名存实亡**。已把插件侧统一到 `交接-YYYYMMDD-HHMMSS.md`（含秒、同秒加 `-2` 后缀），并把已存在的 `当前交接-20261028-2222.md` 迁移为 `交接-20261028-222200.md`。\n'
        '- 改完 `test-health` 先红了 3 条（夹具还在用旧命名）—— 这正是判据该有的反应；夹具改完 `ALL 46 PASSED`。\n',
        'log project files')

s = sub(s,
        '### 验证\n- 六份自测全过：`test-handover` / `test-health`（46 条）/ `test-server`（13 条接口）/ `test-client` / `test-scenes` / `test-render`。\n',
        '### 验证\n- 六份自测全过：`test-handover` / `test-health`（46 条）/ `test-server`（13 条接口）/ `test-client` / `test-scenes` / `test-render`。\n'
        '- 命名统一后复跑：六份仍全绿；真项目探针第二次通过（归档 3 份、`handover:archive = pass`）。\n',
        'log verify')
write(p, s)

# ---------------- 2. 证据文档补一节 ----------------
p = os.path.join(WB, '_evidence', 'v7-2026-10-28.md')
s = read(p)
s = sub(s, '## 五、留给下一步',
        '''## 五、命名统一（同日晚补做）

总工作台 `tools\\交接.py`（M3.3）早就往同一个 `archive\\<id>\\` 目录写快照，命名是 `交接-YYYYMMDD-HHMMSS.md`；
插件侧第一版是 `当前交接-YYYYMMDD-HHMM.md`。**两个入口、两套 glob、各留 10 份 ⇒「保留最近 10 份」名存实亡。**

现在统一为 `交接-YYYYMMDD-HHMMSS.md`（带秒、同秒加 `-2` 后缀），已存在的旧名文件迁移为 `交接-20261028-222200.md`。

改完 `test-health` 先红 3 条 —— 夹具还按旧命名造快照，判据认不出来。这正是判据该有的反应：**它抓的不是我的错，是我漏改的夹具**。夹具改完 `ALL 46 PASSED`。

## 六、留给下一步''',
        'doc section')
s = sub(s, '- 阶段 C：多项目（读 `projects.json` + 顶栏切换器 + 待办切总板带项目标签）。',
        '- **口径已变**：待办板自 2026-10-28 起只剩总工作台 `DSH_Workbench\\boards\\待办板.md` 一处，'
        '项目内 `_交接\\待办板.md` 只留指针 —— 所以「阶段 C 待办切总板」这件事已经在协议层完成，剩的是插件侧不再写项目板。',
        'doc c note')
write(p, s)

# ---------------- 3. 总工作台：总板 + 通知看板 ----------------
p = os.path.join(HUB, 'boards', '待办板.md')
s = read(p)
s = sub(s, '- [x] 2026-10-28 【workbench】入口页 `index.html`',
        '- [x] 2026-10-28 【workbench】插件面板存的快照与 `tools\\交接.py` 统一命名（`交接-YYYYMMDD-HHMMSS.md`），两个入口共用一条序列、共用 10 份额度\n'
        '- [x] 2026-10-28 【workbench】入口页 `index.html`', 'hub board add')
write(p, s)

p = os.path.join(HUB, 'boards', '通知看板.md')
s = read(p).rstrip('\r\n')
s += '\r\n- 2026-10-28 · 快照命名统一：插件面板与 `tools\\交接.py` 现在写同一条序列（`交接-YYYYMMDD-HHMMSS.md`），archive/gp-experiment 已有 3 份\r\n'
write(p, s)

# ---------------- 4. §〇 第 8 次写 ----------------
p = os.path.join(GP, '_交接', '当前交接.md')
s = read(p)
start = s.index('## §〇 当前交接')
end = s.find('\n## ', start + 5)
if end < 0:
    end = len(s)
body = '''## §〇 当前交接（覆盖写，不追加 · 第 8 次写 · 2026-10-28）

- **我是谁**：本项目的 AI 协作会话（DSH Desktop）。工作台 = 总工作台 DSH_Workbench（Python 工具线，已 git 初始化）+ 工作台仓库里的 DSH 插件（V2→V7，机主已定「不依赖插件界面」）。我负责插件侧与任何需要写文件的活。
- **上次进度**：插件侧归档快照落地（覆盖写前自动存、`POST /snapshot`、面板「存快照」按钮、体检第 17 条 `handover:archive`），并**把命名统一到总工作台 `tools/交接.py` 那一套** `交接-YYYYMMDD-HHMMSS.md` → 两个入口共用一条序列与 10 份额度；archive/gp-experiment 现有 3 份。六份自测全绿（体检 46 条、接口 13 条），真项目探针两次通过。
- **下一步**：① 拆 `dsh/index.js`（体检 869/900 行 = 96%，`health.js` 630/700 = 90%，`README.md` 161/260）—— 交接+归档、待办板各拆一个模块 ② 按总板走 M4 协作三件或「拿真实仓库试 `tools/新项目.py`」③ 阶段 D 场景三件（定位卡/画像/私有记忆）接入收工场景。
- **卡点**：① 改插件后必须重载 DSH Desktop 才生效，验收靠机主 ② 灵枢 cg 写入被 gate 拒收，决策只落文件 ③ 工作台仓库无 git，改动一律幂等补丁 + 自测还原 ④ 体检 3 条体积警告，**不改判据迁就，只能拆** ⑤ 插件侧 todos 仍写项目内板（该文件已作废只剩指针），插件要改读总板才一致。
- **细节在哪**：版本史 → Log.md v0.23；待办唯一落点 → `D:\\GitHub_programe\\GitHub\\DSH_Workbench\\boards\\待办板.md`；事实口径 → `5_Reference/AGENTS.md` §三；插件各版留档 → 工作台仓库 _evidence（v7 = 本次归档）。
'''
s = s[:start] + body + s[end:]
write(p, s)
print('s0 bytes =', len(body.encode('utf-8')))
