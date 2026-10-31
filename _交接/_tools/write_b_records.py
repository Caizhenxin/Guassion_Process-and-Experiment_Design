import io, os

GP = r'D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design'
WB = r'D:\GitHub_programe\GitHub\DSH_Workbench'

def read(p):
    return io.open(p, encoding='utf-8').read()

def write(p, s):
    io.open(p, 'w', encoding='utf-8', newline='\r\n' if '\r\n' in s else '\n').write(s)

def sub(s, old, new, label):
    assert s.count(old) == 1, 'anchor %s: %d' % (label, s.count(old))
    return s.replace(old, new)

# ---------------- Log v0.22 ----------------
p = os.path.join(GP, 'Log.md')
s = read(p)
entry = '''## v0.22 (2026-10-28)

**责任人**：蔡振辛

### 新增：总工作台（DSH_Workbench）骨架
- 目标形态定为「**场景 = 项目**」：场景是身份与长期记忆的家，项目是进度与资料的家，两者不重复存同一事实。
- 新建 `D:\\GitHub_programe\\GitHub\\DSH_Workbench`（git 已初始化，首次提交 `71ec5a2`，作者蔡振辛，远端待挂 private）：
  - `projects.json` —— 场景登记表，第一个场景 `gp-experiment` 指向本项目根；
  - `boards\\待办板.md`（最终全机唯一落点，行首带【项目 id】）、`boards\\通知看板.md`；
  - `index\\总索引.md` —— 四状态台账（活 / 常备180天 / 留档 / 待清7天）；
  - `scenes\\gp-experiment\\` —— 定位卡 / 画像 / 私有记忆（对应参考实现图里「场景1」框内的几件）；
  - `archive\\gp-experiment\\` —— 交接快照目录（`.gitignore` 排除，不进 git）；
  - `AGENTS.md` 注入层（1.3 KB，只写"去哪找"，不写正文）。
- 决策记录：① 待办板唯一落点 = 总板（插件阶段 C 切换，切换前仍以项目内 `_交接\\待办板.md` 为临时唯一落点）② git 现在就 init ③ 插件暂不改代码，多项目切换留到阶段 C。

### 验证
- `git log` 首条提交在位；`.gitignore` 实测生效（`git check-ignore` 命中 `archive/**/*`）；骨架 11 个文件全部落盘。

### 文件变更
- 新增（工作台仓库之外的独立目录）：`DSH_Workbench` 全部 11 个文件 + `.git`
- 本项目：`_交接\\总工作台规划_20261028.md`（新）、`_交接\\当前交接.md`、`_交接\\待办板.md`、`Log.md`

---

'''
s = sub(s, '## v0.21 (2026-10-28)', entry + '## v0.21 (2026-10-28)', 'log')
write(p, s)

# ---------------- 待办板（项目内，临时唯一落点） ----------------
p = os.path.join(GP, '_交接', '待办板.md')
s = read(p)
s = sub(s, '- [ ] 2026-10-28 P3 重启验收：顶栏出现 4 个场景标签，点「收工」看到交接 + 待办 + 便利贴',
        '- [x] 2026-10-28 阶段 B：建总工作台 DSH_Workbench 骨架 + git 首次提交\n'
        '- [ ] 2026-10-28 P3 重启验收：顶栏出现 4 个场景标签，点「收工」看到交接 + 待办 + 便利贴', 'board B')
s = sub(s, '- [ ] 下一步 P4 候选：体检独立面板（要动代码）/ 面板类型扩充（chart、flow、site-preview）',
        '- [ ] 2026-10-28 阶段 A：归档快照（§〇 覆盖前自动存 + 按钮 + 保留最近 10 份 + 体检 1 条判据），快照落 DSH_Workbench\\archive\\gp-experiment\\\n'
        '- [ ] 2026-10-28 阶段 C：插件多项目（读 projects.json + 顶栏切换器 + 待办切总板并带项目标签 + 跨项目一致性判据）—— 迁移必须一次性完成，中间态会有两份待办\n'
        '- [ ] 2026-10-28 阶段 D：场景三件接入收工场景（现在文件已建在 DSH_Workbench\\scenes\\gp-experiment\\，插件还没显示）', 'board next')
write(p, s)

# ---------------- 总工作台总板：把 B 划掉 ----------------
p = os.path.join(WB, 'boards', '待办板.md')
s = read(p)
s = sub(s, '- [ ] 【gp-experiment】阶段 B：建总工作台骨架（本目录）并 git init',
        '- [x] 【gp-experiment】阶段 B：建总工作台骨架（本目录）并 git init（71ec5a2）', 'wb board B')
write(p, s)

# ---------------- 规划文档：待定项落定 ----------------
p = os.path.join(GP, '_交接', '总工作台规划_20261028.md')
s = read(p)
s = sub(s, '''## 五、待定（需要机主拍板）

- [ ] 待办板唯一落点：总板（推荐）还是各项目一份？
- [ ] `DSH_Workbench` 现在就 `git init`，还是骨架齐了再 init？
- [ ] 阶段 A 是否现在就做？''',
        '''## 五、已拍板（2026-10-28）

- [x] 待办板唯一落点 = **总板**（阶段 C 切换；切换前项目内 `_交接\\待办板.md` 是临时唯一落点，不许两处同时记）
- [x] `DSH_Workbench` **现在就 git init**（已完成，首提交 71ec5a2，远端等 private repo 建好再挂）
- [x] 先做阶段 **B**（骨架），已完成；阶段 A（归档快照）顺延到下一步，快照正好落 `archive\\gp-experiment\\`''', 'plan decisions')
write(p, s)

# ---------------- §〇 覆盖写（第 7 次） ----------------
p = os.path.join(GP, '_交接', '当前交接.md')
s = read(p)
start = s.index('## §〇 当前交接')
end = s.find('\n## ', start + 5)
if end < 0:
    end = len(s)
body = '''## §〇 当前交接（覆盖写，不追加 · 第 7 次写 · 2026-10-28）

- **我是谁**：本项目的 AI 协作会话（DSH Desktop）；工作台 = 工作台仓库里的 DSH 插件（V2→V6 由我实现）；用户与我共用交接层与待办板；项目方向已定为「场景 = 项目」的多项目总工作台。
- **上次进度**：阶段 B 完成 —— 建好总工作台 DSH_Workbench（路径 D:\\GitHub_programe\\GitHub\\DSH_Workbench，git 已初始化，首提交 71ec5a2）：场景登记表 projects.json、全机唯一待办板、通知看板、总索引四状态台账、场景三件（定位卡/画像/私有记忆，已为 gp-experiment 写好）、archive 快照目录、1.3KB 注入层；插件代码这一轮一行没改。
- **下一步**：① 阶段 A —— 归档快照（§〇 覆盖前自动存到 DSH_Workbench\\archive\\gp-experiment\\，保留最近 10 份，加按钮与体检判据）② 阶段 C —— 插件多项目（读 projects.json + 顶栏项目切换器 + 待办切总板带项目标签 + 跨项目一致性判据），迁移必须一次做完。
- **卡点**：① 改插件后必须重载 DSH Desktop 才生效，验收靠用户 ② 灵枢 cg 写入被 gate 拒收，决策只落文件 ③ 工作台仓库无 git，改动要幂等补丁 + 快照 + 自测还原 ④ lib/client.js 已 2100+ 行（红线 2600）⑤ 插件 todos 仍读写项目内待办板 —— 切总板前存在「两份待办」风险，必须先改代码再搬数据。
- **细节在哪**：版本史 → Log.md v0.22；待办唯一落点（临时）→ `_交接/待办板.md`；事实口径 → `5_Reference/AGENTS.md` §三；总工作台规划 → `_交接/总工作台规划_20261028.md`；工作台改动留档 → 工作台仓库 _evidence 下的 p2/p3 文档。
'''
s = s[:start] + body + s[end:]
write(p, s)
print('records ok; s0 bytes =', len(body.encode('utf-8')))
