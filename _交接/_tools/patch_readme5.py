import io

p = r'D:\GitHub_programe\GitHub\dsh-my-project-workbench\README.md'
s = io.open(p, encoding='utf-8').read()

pairs = [
    ('`dsh/health.js` 跑 11 条判据（4 体量 + 4 索引 + 2 交接 + 1 待办板）',
     '`dsh/health.js` 跑 13 条判据（4 体量 + 5 索引 + 2 交接 + 1 待办板 + 1 指针）'),
    ('（`lib/client.js` 2056 / 2600 行、`dsh/index.js` 741 / 900 行）',
     '（`lib/client.js` 2106 / 2600 行、`dsh/index.js` 741 / 900 行）'),
    ('而是靠 `test-health.mjs` 里 37 条反例：每条判据至少被造红一次。',
     '而是靠 `test-health.mjs` 里 38 条检查：每条判据至少被造红一次，反例按 `SIZE_TARGETS` 现算（改阈值时测试自动跟着走）。'),
    ('# 体检：15 条反例（零扫描 / 量纲 / 锚点 / 幂等 / 写盘失败）',
     '# 体检：38 条检查（零扫描 / 量纲 / 锚点 / 幂等 / 两段判定 / 写盘失败）'),
    ('缺「上次进度/下一步/卡点」直接标红。**覆盖写、不追加** —— 换会话时的唯一入口 |',
     '缺「上次进度/下一步/卡点」直接标红。**覆盖写、不追加** —— 换会话时的唯一入口。面板下半截显示体检读数，一个按钮「跑体检并记待办」 |'),
]

for old, new in pairs:
    assert s.count(old) == 1, 'anchor %d: %s' % (s.count(old), old[:50])
    s = s.replace(old, new)

io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('README updated, lines =', s.count('\n'))
