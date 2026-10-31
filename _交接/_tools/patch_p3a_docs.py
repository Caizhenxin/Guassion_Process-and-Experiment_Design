import io, os

WB = r'D:\GitHub_programe\GitHub\dsh-my-project-workbench'

def sub(s, old, new, label, count=1):
    assert s.count(old) == count, 'anchor %s: %d' % (label, s.count(old))
    return s.replace(old, new)

# ---------------- test-server.mjs ----------------
p = os.path.join(WB, '_evidence', 'test-server.mjs')
s = io.open(p, encoding='utf-8').read()
s = sub(s, "assert.equal(routes.length, 11, '应该有 11 条路由（新增 health）')",
        "assert.equal(routes.length, 12, '应该有 12 条路由（新增 health / scenes）')", 'ts routes')
s = sub(s, "// 5b) 体检：GET 只读不改文件；POST 幂等（同一件事只许一行）",
        '''// 5a) 场景配置：GET 只读，坏文件退回默认也必须把问题交回来
const scenesGet = await get('scenes')
console.log('\\n[scenes]', scenesGet.summary)
assert.equal(scenesGet.ok, true, 'scenes 顶层 ok 必须为 true')
assert.ok(['file', 'default'].indexOf(scenesGet.source) >= 0, 'source 只能是 file/default')
assert.ok(Array.isArray(scenesGet.scenes) && scenesGet.scenes.length > 0, '至少要有一个场景')
for (const scene of scenesGet.scenes) {
  assert.ok(scene.id && scene.name, '场景要有 id 与 name')
  assert.ok(Array.isArray(scene.rows) && scene.rows.length, '场景必须有行')
  for (const row of scene.rows) {
    for (const column of row.columns || []) {
      for (const panel of column.panels || []) assert.ok(panel.id, '面板要有 id')
    }
  }
}
assert.deepEqual(scenesGet.problems, [], '真项目的 scenes.json 必须没有问题')

// 5b) 体检：GET 只读不改文件；POST 幂等（同一件事只许一行）''', 'ts scenes')
io.open(p, 'w', encoding='utf-8', newline='\n').write(s)

# ---------------- README.md ----------------
p = os.path.join(WB, 'README.md')
s = io.open(p, encoding='utf-8').read()

s = sub(s, '`dsh/health.js` 跑 13 条判据（4 体量 + 5 索引 + 2 交接 + 1 待办板 + 1 指针）',
        '`dsh/health.js` 跑 15 条判据（5 体量 + 5 索引 + 2 交接 + 1 待办板 + 1 指针 + 1 场景配置）', 'readme rules')

v6 = '''## V6：场景配置驱动（版式不再写死在代码里）

版式原先硬编码在 `lib/client.js` 的 `SCENES` 里：加一个面板要改 4 处，改错一处就只是
「看起来正常」。现在**唯一出处是根目录的 `scenes.json`**：

- `GET /scenes` 读它 → 客户端只消费 + 兜底渲染。配置只许用编辑器改，**不提供面板写入口**：
  写坏了版式会「看起来正常」却少一块，比直接报错更难查。
- `dsh/scenes.js` 握内置默认值 + 校验：未知面板 id、同一场景重复面板、场景 id 重复、rows 空、
  坏 JSON —— 任一不合法就**整份退回默认**（不给半份配置），并把问题原文一起交回去，顶栏提示一句。
- 客户端的 `SCENES` 降级为**启动兜底**（拉不到／校验不过时才用），`nodeFor` 对未知 id 现在返回空，
  不再把未知 id 悄悄渲染成 AI 对话面板。
- 体检新增 `config:scenes`：配置坏了 fail（已退回默认也要说清），没有文件则 warn（用内置默认是合法用法）。

```json
{ "version": 1, "scenes": [
  { "id": "overview", "name": "项目总览", "icon": "◎",
    "rows": [ { "g": 1.25, "columns": [
      { "w": 7, "panels": [ { "id": "kpi", "g": 0 }, { "id": "handover", "g": 1 } ] },
      { "w": 5, "panels": [ { "id": "notes", "g": 1 } ] } ] } ] } ] }
```

'''
s = sub(s, '## 服务端接口（`/api/my-project-workbench/`）', v6 + '## 服务端接口（`/api/my-project-workbench/`）', 'readme v6')

s = sub(s, "| `health` |", "| `scenes` | GET 只读：读插件根目录的 `scenes.json`，返回 `scenes` + `source`(file/default) + `problems` + `drift`；配置坏了退回内置默认 |\n| `health` |", 'readme route row')

s = sub(s, '# 11 条接口（含越界、扩展名、二进制与不安全网址拒绝）',
        '# 12 条接口（含越界、扩展名、二进制与不安全网址拒绝）', 'readme server count')

s = sub(s, 'E:\\Node\\node.exe _evidence\\test-health.mjs    # 体检：38 条检查（零扫描 / 量纲 / 锚点 / 幂等 / 两段判定 / 写盘失败）',
        'E:\\Node\\node.exe _evidence\\test-scenes.mjs    # 场景配置：14 条检查（未知面板 / 重复面板 / 坏 JSON / 三来源）\n'
        'E:\\Node\\node.exe _evidence\\test-health.mjs    # 体检：38 条检查（零扫描 / 量纲 / 锚点 / 幂等 / 两段判定 / 写盘失败）', 'readme tests')

s = sub(s, '五份都输出 `ALL ... PASSED`。', '六份都输出 `ALL ... PASSED`。', 'readme five')
io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('docs+tests patched')
