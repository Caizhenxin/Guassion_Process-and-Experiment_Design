#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""作业状态约定（任何长作业都能写，面板只读它）。

约定只有一句话：**作业在自己的目录里写一个 `status.json`**，面板只认这一个文件。

    $DSH_HOME/jobboard/jobs/<job_id>/status.json

任何脚本（python / cmd / node / 手工）只要按下面的字段写这个文件，就能出现在
DSH 侧边栏的「作业」面板里，不需要改面板代码。

字段（除 `id`/`title` 外都可缺省）：

    id          作业短名，建议和目录名一致（`stage8_d123`）
    title       人看到的名字（`Stage 8 真实数据 17 人`）
    state       running | done | failed | stalled
    step        当前步骤的一句话（`组 1 M-T1 拟合中`）
    done/total  进度分子分母（`0/8` 个模型）
    pid         进程号（面板显示，不作为存活依据）
    started_at  ISO 时间
    eta_seconds 预计剩余秒
    relaunch    掉线后可以重跑的启动脚本（可选，面板只展示不执行）
    log         日志路径（可选）
    tail        最近几行日志（list[str]，面板直接显示）
    meta        任意附加字段（dict，面板显示成键值对）

存活判断用 `updated_at` 的新鲜度：作业每 `heartbeat()` 一次就等于「我还活着」。
这样一个进程被静默杀掉时，面板会因为心跳变旧而变红，而不用去猜 pid。

用法（脚本里两行）：

    from jobstatus import Job
    job = Job("stage8_d123", "Stage 8 真实数据 17 人", total=8)
    job.update(done=1, step="组 1 M-T3")     # 每完成一步调一次
    job.tail(lines)                          # 可选：把日志尾巴带上
    job.finish("done")

命令行看一眼：

    python -X utf8 1_Code/Tools/jobstatus.py            # 列所有作业
    python -X utf8 1_Code/Tools/jobstatus.py --prune    # 删掉 7 天前已结束的
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

#: 作业根目录：`$DSH_HOME/jobboard/jobs`，没有 DSH_HOME 时退到 `~/.dsh-jobboard`。
ROOT = Path(os.environ.get("DSH_JOBBOARD_DIR")
            or (Path(os.environ["DSH_HOME"]) / "jobboard" / "jobs"
                if os.environ.get("DSH_HOME") else Path.home() / ".dsh-jobboard"))


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def job_dir(job_id: str) -> Path:
    return ROOT / job_id


class Job:
    """一个作业的状态文件句柄。所有写入都是「整文件替换」，读到的永远是完整 JSON。"""

    def __init__(self, job_id: str, title: str, total: int | None = None,
                 relaunch: str | None = None, log: str | None = None):
        self.id = job_id
        self.path = job_dir(job_id) / "status.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data: dict = {
            "id": job_id,
            "title": title,
            "state": "running",
            "step": "",
            "done": 0,
            "total": total,
            "pid": os.getpid(),
            "started_at": now_iso(),
            "updated_at": now_iso(),
            "eta_seconds": None,
            "relaunch": relaunch,
            "log": log,
            "tail": [],
            "meta": {},
        }
        self.flush()

    # ---- 写 ----
    def flush(self) -> None:
        self.data["updated_at"] = now_iso()
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self.data, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8", newline="\n")
        tmp.replace(self.path)

    def update(self, **kw) -> None:
        self.data.update(kw)
        self.flush()

    def beat(self, step: str | None = None) -> None:
        """心跳：只更新时间戳（可选顺便换步骤文字）。"""
        if step is not None:
            self.data["step"] = step
        self.flush()

    def tail(self, lines: list[str] | str, keep: int = 8) -> None:
        rows = [lines] if isinstance(lines, str) else list(lines)
        rows = [r.rstrip() for r in rows if r.strip()]
        self.data["tail"] = (self.data.get("tail") or [])[-keep:] + rows
        self.data["tail"] = self.data["tail"][-keep:]
        self.flush()

    def finish(self, state: str = "done", step: str | None = None) -> None:
        self.data["state"] = state
        if step is not None:
            self.data["step"] = step
        self.data["eta_seconds"] = 0 if state == "done" else self.data.get("eta_seconds")
        self.flush()


def age_seconds(path: Path) -> float:
    try:
        return time.time() - path.stat().st_mtime
    except OSError:
        return float("inf")


def scan(root: Path = ROOT) -> list[dict]:
    """读出所有作业（面板/命令行共用）。"""
    out: list[dict] = []
    if not root.is_dir():
        return out
    for d in sorted(root.iterdir()):
        f = d / "status.json"
        if not f.is_file():
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        data["age_seconds"] = round(age_seconds(f), 1)
        out.append(data)
    out.sort(key=lambda x: (x.get("state") != "running", x.get("started_at") or ""))
    return out


def _fmt_age(sec: float) -> str:
    if sec < 90:
        return f"{sec:.0f} 秒前"
    if sec < 5400:
        return f"{sec / 60:.0f} 分钟前"
    return f"{sec / 3600:.1f} 小时前"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prune", action="store_true", help="删除 7 天前已结束的作业目录")
    ap.add_argument("--root", default=None)
    args = ap.parse_args()
    root = Path(args.root) if args.root else ROOT

    if args.prune:
        cutoff = time.time() - 7 * 86400
        n = 0
        for d in root.iterdir() if root.is_dir() else []:
            f = d / "status.json"
            if not f.is_file():
                continue
            try:
                state = json.loads(f.read_text(encoding="utf-8")).get("state")
            except Exception:
                state = None
            if state != "running" and f.stat().st_mtime < cutoff:
                shutil.rmtree(d, ignore_errors=True)
                n += 1
        print(f"[prune] 删了 {n} 个")
        return 0

    jobs = scan(root)
    print(f"作业根目录：{root}")
    if not jobs:
        print("（还没有作业写过 status.json）")
        return 0
    for j in jobs:
        total = j.get("total")
        prog = f"{j.get('done', 0)}/{total}" if total else "—"
        print(f"[{j.get('state', '?'):8s}] {j.get('title') or j.get('id')}"
              f"  {prog}  {_fmt_age(j['age_seconds'])}  {j.get('step') or ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
