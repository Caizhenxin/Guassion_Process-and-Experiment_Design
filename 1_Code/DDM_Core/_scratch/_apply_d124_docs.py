# -*- coding: utf-8 -*-
"""D124 落纸：DSH 侧边栏作业面板（通用 status.json 约定）。

幂等：已存在则跳过。
"""
from pathlib import Path

ROOT = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
PLAN = ROOT / "5_Reference/08_工作流/工作流_主计划.md"

D_ROW = (
    "| **D124** | 2026-10-25 | **后台作业从「每个任务自己搭看板」收成一条通用约定："
    "`$DSH_HOME/jobboard/jobs/<id>/status.json` + DSH 侧边栏面板**。"
    "任何脚本（python / cmd / node / 手工）按字段写这个文件，面板自动出卡片，"
    "面板代码不用改；写文件的入口是 `1_Code/Tools/jobstatus.py`（两行）。"
    "存活判断**不看 pid 看心跳**（每次 `beat()` 刷新 mtime，>10 min 判「心跳停了」）"
    "——进程被静默杀掉时不会误显示成运行中，这正是 2026-10-25 两次事故的共同教训。"
    "插件装在 `1_Code/Tools/dsh-jobboard/`（`install.py` / `uninstall.py` / `cordis.patch.yml`，"
    "装完需重启 DSH）；本地 HTML 看板（`stage8_watch.py`）保留为 B 档备选。 | "
    "用户 2026-10-25「想要一个通用一点的后台作业可视化，不限于 cmd」；"
    "`2026-10-25_长时后台作业挂在会话上随重启被杀.md` | "
    "`1_Code/Tools/dsh-jobboard/`（11 文件）+ `1_Code/Tools/jobstatus.py`（201 行）+ "
    "`stage8_watch.py`（写入同一格式）；提交 `c98e011` |"
)

PROG_ROW = (
    "| 2026-10-25 | **21（通用作业面板 → D124）** | "
    "**把「看进度」从一次性脚本变成约定**：`status.json` 一个格式，DSH 侧边栏一张卡片，"
    "存活按心跳判（不认 pid）。Stage 8 的看板同步改成写这个格式，两种看法共用一份状态。"
    "未做：面板装到用户 DSH 后的实机验收（需重启 DSH）。 | 用户 2026-10-25 提出「通用后台作业可视化」 | "
    "`1_Code/Tools/dsh-jobboard/`；`1_Code/Tools/jobstatus.py`；提交 `c98e011` |"
)

CHG_ROW = (
    "| 2026-10-25 | **新增 D124（DSH 侧边栏作业面板）**：通用 `status.json` 约定 + "
    "`jobstatus.py` 写入工具 + 插件 11 文件；存活性按心跳（mtime）判，不认 pid；"
    "`stage8_watch.py` 同步输出该格式。 |"
)

EV_ROW = (
    "| `1_Code/Tools/dsh-jobboard/`（`lib/index.mjs` 宿主侧扫目录 + `lib/client.js` 侧边栏卡片 + "
    "`install.py`/`uninstall.py`/`cordis.patch.yml`）+ `1_Code/Tools/jobstatus.py` | "
    "D124 证据：`status.json` 字段 `state/step/done/total/pid/started_at/eta_seconds/relaunch/log/tail/meta`；"
    "心跳 >10 min ⇒ 「心跳停了」；本地 HTML 看板与面板共用一份状态；提交 `c98e011`（1366 行） |"
)


def insert_before(lines, prefix, row, tag):
    hits = [i for i, ln in enumerate(lines) if ln.startswith(prefix)]
    assert len(hits) == 1, f"{tag}: 命中 {len(hits)} 次"
    lines.insert(hits[0], row)


def insert_after(lines, prefix, row, tag):
    hits = [i for i, ln in enumerate(lines) if ln.startswith(prefix)]
    assert len(hits) == 1, f"{tag}: 命中 {len(hits)} 次"
    lines.insert(hits[0] + 1, row)


def main() -> None:
    text = PLAN.read_text(encoding="utf-8")
    if "**D124**" in text:
        print("[plan] D124 已存在，跳过")
        return
    lines = text.split("\n")
    insert_before(lines, "| **D123** | 2026-10-25 |", D_ROW, "D124 决策行")
    insert_after(lines, "| 2026-10-25 | **20（t0 上界与快反应剔除 → D123）** |", PROG_ROW, "进度行")
    insert_after(lines, "| 2026-10-25 | **新增 D123（", CHG_ROW, "变更日志行")
    while lines and lines[-1].strip() == "":
        lines.pop()
    lines.append(EV_ROW)
    lines.append("")
    PLAN.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(f"[plan] {PLAN.name}: {len(lines)} 行")


if __name__ == "__main__":
    main()
