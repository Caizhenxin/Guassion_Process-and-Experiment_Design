import io

ho = r'D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\_交接\当前交接.md'
h = io.open(ho, encoding='utf-8').read()
start = h.index('## §〇 当前交接')
end = h.find('\n## ', start + 5)
if end < 0:
    end = len(h)

body = '''## §〇 当前交接（覆盖写，不追加 · 第 5 次写 · 2026-10-28）

- **我是谁**：本项目的 AI 协作会话（DSH Desktop）；工作台 = 工作台仓库里的 DSH 插件；用户与我共用这套交接层与待办板。
- **上次进度**：工作台 V5 体检层（P2）已完成 —— 13 条判据、`health` 接口（GET 只读 / POST 才写待办板）、交接面板下半截显示读数；五份自测全绿（体检自测 38 条检查），真项目探针 13 通过 / 0 警告 / 0 失败。此前 V4 交接层（P1）已上线。
- **下一步**：① 等用户重启 DSH Desktop 验收交接面板下半截的读数与按钮 ② P3 = 场景配置驱动（scenes.json）+ 体检独立面板（细节见待办板与工作台仓库 _evidence/p2-2026-10-28.md）。
- **卡点**：① 改插件后必须重载 DSH Desktop 才生效，面板验收只能靠用户眼睛 ② 灵枢 cg 写入连续 3 次被 gate 拒收（缺出处标记 / 条件空间），决策只落文件、不进 cg ③ 工作台仓库没有 git，任何改动都要幂等补丁 + 快照 + 自测还原。
- **细节在哪**：进度与版本 → `Log.md` v0.20；待办唯一落点 → `_交接/待办板.md`；事实口径 → `5_Reference/AGENTS.md` §三；工作台改动与翻车留档 → 工作台仓库的 _evidence/p2-2026-10-28.md（V4 见 v4-2026-10-28.md）；参考实现在工作台仓库 docs/reference/luanyujia-workbench-main\（记忆机制看 00-核心机制\\二-记忆机制.md，规矩机械化看 08-升级与改造清单\）。
'''

h = h[:start] + body + h[end:]
io.open(ho, 'w', encoding='utf-8', newline='\r\n' if '\r\n' in h else '\n').write(h)
print('§〇 v5 ok, total bytes =', len(h.encode('utf-8')))
