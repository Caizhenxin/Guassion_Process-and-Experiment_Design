"""P5 收尾记录：README 计数、§〇 第 9 次覆盖写、Log v0.24、待办板、evidence。"""
import io
import os

WB = r'D:\GitHub_programe\GitHub\dsh-my-project-workbench'
P = r'D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design'
HUB = r'D:\GitHub_programe\GitHub\DSH_Workbench'
TODAY = '2026-10-30'

def read(path):
    return io.open(path, encoding='utf-8', newline='').read()

def write(path, text):
    io.open(path, 'w', encoding='utf-8', newline='').write(text)

# ---------- 1. README 计数 ----------
p = os.path.join(WB, 'README.md')
src = read(p)
reps = [
    ('17 条判据（5 体量 + 5 索引 + 2 交接 + 1 待办板 + 1 指针 + 2 场景配置）',
     '18 条判据（6 体量 + 5 索引 + 2 交接 + 1 待办板 + 1 指针 + 2 场景配置 + 1 归档）'),
    ('38 条检查', '46 条检查'),
    ('11 条检查（标签 / 合并 / 别人的行不许动 / 迁移）', '13 条检查（标签 / 合并 / 别人的行不许动 / 迁移 / 认领守卫）'),
    ('13 条接口（含越界、扩展名、二进制与不安全网址拒绝）', '14 条接口（含越界、扩展名、二进制与不安全网址拒绝）'),
]
done = 0
for old, new in reps:
    if old in src:
        src = src.replace(old, new, 1)
        done += 1
write(p, src)
print('README 改', done, '处')

# ---------- 2. §〇 第 9 次覆盖写 ----------
S0 = '''# §〇 当前交接

**我是谁**：GP 实验项目会话（实验设计 + 数据分析主项目）。工作台插件归属于总工作台 DSH_Workbench，登记 id 为 gp-experiment。

**上次进度**（2026-10-30）：

- 插件 P5 完成：待办收成一处（总工作台 boards/待办板.md，行首带【项目id】）、交接归档快照（覆盖写前自动存，保留 10 份）、体检键统一为双括号 health 标记且修好即自动打勾；index.js 撞体积红线，已把待办落盘层拆到 boardStore.js。七份自测全绿（体检 18 条判据：15 通过 / 3 警告 / 0 失败），真项目探针通过。
- 总工作台侧：骨架、登记表 v2、总板、工具四件（体检 / 交接 / 新项目 / 反例测试）已落盘，git 三提交。
- 本轮修掉一个真 bug：面板打开时会把板上无标签的行认领成自己项目（GP 曾把三条 workbench 的活改写成自己标签）。现在规则是「板上已有任何项目标签 ⇒ 谁都不许认领」。

**下一步**：

- 重启 DSH Desktop 验收：交接面板看「归档 N 份」与存快照按钮；待办面板看行首是否带【gp-experiment】。
- 插件线只剩一件小事：总览加一条「总进度」摘要。之后精力回 GP：D48 deadline 两代口径、SPE 交互检验与四层保留方案、第 10 章。

**卡点**：

- 工作台仓库没有 git，改动必须走幂等补丁 + 快照；本轮出现三次「幽灵成功」（脚本报告成功但文件没变），代价都来自这里。
- 灵枢 cg 写入被 gate 拒收（缺出处标记），所以决策只落文件、不进 cg。
- 沙箱：workspace 只有 GP 项目目录，工作台与 DSH_Workbench 的写入需要放开权限（本会话已放开）。

**细节在哪**：工作台插件见其 README 与 _evidence 目录；总工作台见 DSH_Workbench 的 index/进度.md；本项目见 Log.md 与 5_Reference。
'''
src = read(os.path.join(P, '_交接', '当前交接.md'))
io.open(os.path.join(P, '_交接', '当前交接.md'), 'w', encoding='utf-8', newline='\n').write(S0)
print('§〇 写', len(S0.encode('utf-8')), '字节')

# ---------- 3. Log v0.24 ----------
p = os.path.join(P, 'Log.md')
src = read(p)
entry = '''
## v0.24 (2026-10-30) 工作台插件 P5：待办收成一处 + 归档快照 + 键统一 + 拆分

- 待办板唯一落点改为总工作台 boards/待办板.md，行首带【项目id】；插件只改自己标签的行，别人的项目行与人写的说明一个字不许动。
- 修掉认领 bug：板上已有任何项目标签时，无标签行谁都不许认领（此前先打开面板的项目会把别人的活改写）。
- 体检的 ⛔ 项改为写进总板并带去重键，问题修好后下次体检自动打勾（人工与机器同一句标记，不再各写一份）。
- index.js 撞体积红线（33098/32768 B），把待办落盘层拆到 dsh/boardStore.js：781 行 / 29080 B，判据转 warn。
- 自测 7 份全绿：test-health 46 条、test-board 13 条、test-server 14 条接口及其余四份；真项目探针：待办读总板、正文无标签、归档可读。
- 遗留：交接面板与待办面板需重启 DSH Desktop 验收；总览的「总进度」一条尚未做。
'''
if '## v0.24' not in src:
    anchor = '\n## v0.23'
    if anchor in src:
        src = src.replace(anchor, entry + anchor, 1)
    else:
        src = entry.lstrip('\n') + '\n' + src
    write(p, src)
    print('Log v0.24 写入')
else:
    print('Log v0.24 已存在')

# ---------- 4. 待办板 ----------
p = os.path.join(HUB, 'boards', '待办板.md')
src = read(p)
lines = [
    '- [ ] 2026-10-30 【gp-experiment】P5 重启验收：交接面板显示「归档 N 份」与存快照按钮；待办面板行首带【gp-experiment】',
    '- [x] 2026-10-30 【gp-experiment】P5 完成：待办收成总板 / 归档快照 / 体检键统一 / index.js 拆出 boardStore.js（18 判据：15 通过 3 警告 0 失败）',
]
if 'P5 完成：待办收成总板' not in src:
    head, sep, tail = src.partition('\n## 已做')
    src = head.rstrip('\n') + '\n' + lines[0] + '\n' + sep + '\n' + lines[1] + '\n' + tail.lstrip('\n')
    if 'P5 重启验收' not in head:
        pass
    write(p, src)
    print('待办板加 2 行')
else:
    print('待办板已有 P5 行')
