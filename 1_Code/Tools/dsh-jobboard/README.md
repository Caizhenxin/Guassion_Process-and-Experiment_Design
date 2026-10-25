# 作业面板（dsh-jobboard）

给 DSH 加一个侧边栏面板，用来**看所有后台作业的实时进度**：哪一步在跑、跑了多久、心跳还在不在、掉线了去哪重跑。

设计上只认**一个约定**：

```
$DSH_HOME/jobboard/jobs/<job_id>/status.json
```

任何脚本（python / cmd / node / 手工）按这个格式写文件，面板自动出现卡片；面板代码不用改。
写文件的工具是 `1_Code/Tools/jobstatus.py`（两行即可）。

## 一、为什么是插件而不是网页

| 做法 | 看得见 | 要另开窗口 | 掉线能重拉 | 工作量 |
|---|---|---|---|---|
| A 任务计划程序 + 日志 | ❌ | — | ✅ | 10 min |
| B 本地 HTML 看板（`stage8_watch.py` 已有） | ✅ | ✅ | ✅ | 已完成 |
| C DSH 侧边栏面板（本目录） | ✅ | ❌ 就在 DSH 里 | ✅（用同一个 `status.json`） | 已完成 |

B 档仍然可用（`2_Data/Real_Data/New_Design/_pipeline/stage8_d123/status.html`），C 档只是为了不用另开窗口。

## 二、结构

```
$DSH_HOME/jobboard/jobs/<id>/status.json      ← 作业写（jobstatus.py）
        ↓ 读
lib/index.mjs  →  GET /jobboard-api/jobs      ← 宿主侧：扫目录 + 把 mtime 换算成心跳年龄
        ↓ fetch
lib/client.js  →  侧边栏「作业」→ 卡片        ← 前端：2 秒轮询
```

`status.json` 字段（都可缺省，除 `id`/`title`）：`state`（running/done/failed/stalled）、`step`、`done`/`total`、
`pid`、`started_at`、`eta_seconds`、`relaunch`、`log`、`tail`（最近几行）、`meta`。

**存活判断不看 pid，看心跳**：作业每次 `beat()`/`update()` 都会刷新 mtime，超过 10 分钟没动 ⇒ 面板标「心跳停了」。
这样进程被静默杀掉时不会误显示成「运行中」。

## 三、安装 / 卸载（装完要重启）

```powershell
python -X utf8 1_Code/Tools/dsh-jobboard/install.py            # 预演
python -X utf8 1_Code/Tools/dsh-jobboard/install.py --apply    # 真装 → 重启 DSH
python -X utf8 1_Code/Tools/dsh-jobboard/uninstall.py --apply  # 卸掉 → 重启 DSH
```

装的时候改了什么（都可逆）：

- 新建 `$DSH_HOME\profiles\.generations\live\local+dsh-jobboard+<ver>+<hash>\`
  （`package.json`、`generation.json`、`.npmrc`、`node_modules\@local\dsh-jobboard\` 真目录，`node-linker=hoisted` 所以不用 pnpm）；
- `desired.json` 增删一个字符串；改动前备份为 `desired.json.bak-jobboard-<时间戳>`；重装会自动摘掉旧哈希那一条。

回滚三层：① `uninstall.py --apply`；② 把 `desired.json.bak-jobboard-*` 盖回去；③ DSH 自带 `safe-mode.html` / `plugin-recovery.html`。

## 四、自测（不用启动 DSH）

```powershell
node 1_Code/Tools/dsh-jobboard/test_host.mjs     # 13 项：导出、路由注册、JSON 形状、404/405
python -X utf8 1_Code/Tools/jobstatus.py         # 命令行列所有作业
```

`test_host.mjs` 用假的 `ctx`/`webServer` 跑真实的 handler，验的是插件逻辑；重启后还剩一个未知项——
**DSH 的加载器是否接受这个 generation**，表现是侧边栏有没有「作业」条目。

## 五、接入新作业（两个用法）

脚本里：

```python
import sys; sys.path.insert(0, r"1_Code/Tools")
from jobstatus import Job

job = Job("my_fit", "我的长拟合", total=8)
job.update(done=1, step="组 1 完成", eta_seconds=1800)
job.tail(["ELPD = -1639.18"])
job.finish("done")
```

已经把 Stage 8 接上了：`stage8_watch.py` 每次刷新会同步写一份通用 `status.json`
（`--job-id stage8_d123`，传空串则不写）。

## 六、文件

```
1_Code/Tools/jobstatus.py              作业状态约定 + 命令行
1_Code/Tools/dsh-jobboard/
├─ package.json                        插件清单（dsh.bundle / dsh.client）
├─ cordis.patch.yml                    insert 本插件
├─ lib/index.mjs                       宿主侧：/jobboard-api/jobs
├─ lib/client.js                       前端：侧边栏 + 面板（__ModuleLoader__ 格式，无 JSX）
├─ install.py / uninstall.py           安装 / 卸载（默认 dry-run）
└─ test_host.mjs                       宿主侧离线自测
```
