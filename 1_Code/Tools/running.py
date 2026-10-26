#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""「现在到底有什么在跑」——不需要重启 DSH、不需要插件、不依赖作业自报。

回答三个问题：
    ① 什么东西在运行      —— OS 进程（python / node / cmd / powershell / DSH 本体）
    ② 运行了多久          —— 进程创建时间到现在
    ③ 对应哪个窗口/项目    —— 命令行里的路径 + DSH 的会话目录（`$DSH_HOME/sessions/<编码过的 cwd>/`）

为什么这么设计（可行性）：
    * OS 层：`Win32_Process` 给 pid / 命令行 / 创建时间 / 父进程，Windows 上稳定可得；
    * 会话层：DSH 把每个工作目录的会话放在 `$DSH_HOME/sessions/<cwd 编码>/`，目录名可反解回项目路径，
      目录的 mtime 就是「这个窗口最后活动时间」；
    * 作业层：`$DSH_HOME/jobboard/jobs/<id>/status.json` 只有自愿上报的作业才有（进度条），
      没有也能看到进程本身——**这是与「只显示自报作业」的关键区别**。
    * 局限：Windows 不给「某个进程属于哪个 GUI 窗口」，所以只能做到**项目级归属**；
      精确到「哪个会话标签页」需要 DSH 插件读 `sessions`/`jobs` 服务（需重启）。

用法：
    python -X utf8 1_Code/Tools/running.py                # 打印到终端
    python -X utf8 1_Code/Tools/running.py --html         # 生成并打开 running.html
    python -X utf8 1_Code/Tools/running.py --watch 5      # 每 5 秒重写 HTML（后台常驻）
    python -X utf8 1_Code/Tools/running.py --json         # 机器可读
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import webbrowser
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DSH_HOME = Path(os.environ.get("DSH_HOME")
                or Path.home() / "AppData" / "Roaming" / "dsh-desktop" / "harness")
OUT_HTML = DSH_HOME / "jobboard" / "running.html"
JOBS = DSH_HOME / "jobboard" / "jobs"

#: 这些进程名值得一看（其余只在跑很久时才列）。
WATCH_NAMES = {"python.exe", "pythonw.exe", "node.exe", "cmd.exe", "powershell.exe",
               "pwsh.exe", "jupyter.exe", "DSH.exe", "electron.exe"}
#: 明显是后台服务/系统组件，列表里默认不占版面。
NOISE = re.compile(r"McAfee|Adobe|WebAdvisor|BrowserHost|MicrosoftEdge|SearchProtocol|"
                   r"RuntimeBroker|OfficeClickToRun|OneDrive", re.I)

PS_SCRIPT = r"""
$ErrorActionPreference='SilentlyContinue'
Get-CimInstance Win32_Process |
  Where-Object { $_.Name -match '^(python|pythonw|node|cmd|powershell|pwsh|jupyter|DSH|electron)\.exe$' } |
  Select-Object ProcessId,ParentProcessId,Name,CreationDate,CommandLine |
  ConvertTo-Json -Depth 3 -Compress
"""


def query_processes() -> list[dict]:
    try:
        raw = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", PS_SCRIPT],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
        ).stdout.strip()
    except Exception as exc:  # pragma: no cover - 环境异常
        print(f"[warn] 进程扫描失败：{exc}", file=sys.stderr)
        return []
    if not raw:
        return []
    data = json.loads(raw)
    if isinstance(data, dict):
        data = [data]
    out = []
    for p in data:
        created = p.get("CreationDate")
        # CIM 的 CreationDate 经过 JSON 后可能是 "/Date(1698...)/" 或 ISO 字符串
        age = None
        if isinstance(created, str):
            m = re.search(r"/Date\((\d+)", created)
            if m:
                age = time.time() - int(m.group(1)) / 1000
            else:
                try:
                    age = time.time() - datetime.fromisoformat(
                        created.replace("Z", "+00:00")).timestamp()
                except ValueError:
                    age = None
        out.append({
            "pid": p.get("ProcessId"),
            "ppid": p.get("ParentProcessId"),
            "name": (p.get("Name") or "").lower(),
            "age": age,
            "cmd": (p.get("CommandLine") or "").strip(),
        })
    return out


def _unescape(s: str) -> str:
    try:
        return json.loads('"' + s.replace('"', '\\"') + '"')
    except Exception:
        return s


PROJ_CACHE = DSH_HOME / "storages" / "session_projcache" / "sessions"
CWD_RE = re.compile(r'"cwd":\s*"((?:[^"\\]|\\.)*)"')
TITLE_RE = re.compile(r'"title":\s*\{\s*"ver":[^}]*?"val":\s*"((?:[^"\\]|\\.)*)"')
CREATED_RE = re.compile(r'"createdAt":\s*(\d{10,})')


def windows() -> list[dict]:
    """DSH 窗口 = 会话投影文件。标题、工作目录、最后活动都由它给，比目录名可靠。"""
    if not PROJ_CACHE.is_dir():
        return []
    rows = []
    for f in PROJ_CACHE.glob("session-*.json"):
        try:
            head = f.read_text(encoding="utf-8", errors="replace")[:8000]
        except OSError:
            continue
        cwd = CWD_RE.search(head)
        if not cwd:
            continue
        title = TITLE_RE.search(head)
        created = CREATED_RE.search(head)
        mtime = f.stat().st_mtime
        rows.append({
            "sid": f.stem.replace("session-", "")[:8],
            "title": _unescape(title.group(1)) if title else "（无标题）",
            "cwd": _unescape(cwd.group(1)),
            "last": datetime.fromtimestamp(mtime).strftime("%m-%d %H:%M"),
            "ago_s": time.time() - mtime,
            "born": (datetime.fromtimestamp(int(created.group(1)) / 1000).strftime("%m-%d %H:%M")
                     if created else "—"),
        })
    rows.sort(key=lambda r: r["ago_s"])
    return rows


def known_projects(wins: list[dict]) -> list[str]:
    """用于归属判断的项目路径（越长越优先匹配）。"""
    cands = [w["cwd"] for w in wins]
    cands += [r"Guassion-Process-Experiment-Design", r"SPE_Database", r"Self-Repo"]
    return sorted({c for c in cands if c}, key=len, reverse=True)


def attribute(cmd: str, projects: list[str]) -> str:
    low = cmd.lower()
    for p in projects:
        if p.lower() in low:
            return Path(p).name
    m = re.search(r"[A-Za-z]:\\[^\"\s]+", cmd)
    if m:
        parts = Path(m.group(0)).parts[:3]
        return "\\".join(parts) if parts else "—"
    return "—"


def load_jobs() -> dict[int, dict]:
    """自报作业：pid → 状态（用于给进程挂进度条）。"""
    out: dict[int, dict] = {}
    if not JOBS.is_dir():
        return out
    for d in JOBS.iterdir():
        f = d / "status.json"
        if not f.is_file():
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if data.get("pid"):
            out[int(data["pid"])] = data
    return out


def human_age(sec: float | None) -> str:
    if sec is None:
        return "—"
    if sec < 90:
        return f"{sec:.0f} 秒"
    if sec < 5400:
        return f"{sec / 60:.0f} 分钟"
    if sec < 172800:
        return f"{sec / 3600:.1f} 小时"
    return f"{sec / 86400:.1f} 天"


def collect() -> dict:
    procs = query_processes()
    wins = windows()
    projects = known_projects(wins)
    jobs = load_jobs()
    me = os.getpid()
    rows = []
    for p in procs:
        cmd = p["cmd"] or ""
        if p["pid"] == me or NOISE.search(cmd) or "Win32_Process" in cmd or "running.py" in cmd:
            continue
        long_enough = (p["age"] or 0) >= 60
        if p["name"] not in WATCH_NAMES and not long_enough:
            continue
        job = jobs.get(p["pid"])
        rows.append({
            "pid": p["pid"],
            "ppid": p["ppid"],
            "name": p["name"].replace(".exe", ""),
            "age": p["age"],
            "age_h": human_age(p["age"]),
            "cmd": cmd[:400],
            "project": attribute(cmd, projects),
            "job": job,
        })
    rows.sort(key=lambda r: -(r["age"] or 0))
    return {
        "at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "windows": wins,
        "procs": rows,
        "jobs_root": str(JOBS),
    }


def render_text(data: dict) -> str:
    lines = [f"扫描时间 {data['at']}", ""]
    lines.append("== 最近的 DSH 窗口（按最后活动） ==")
    for w in data["windows"][:6]:
        lines.append(f"  {w['last']}（{human_age(w['ago_s'])}前）  {w['title']}")
        lines.append(f"        {w['cwd']}  [{w['sid']}]")
    lines += ["", "== 正在跑的进程 =="]
    for r in data["procs"]:
        tag = f"  [{r['job']['title']} {r['job'].get('done', 0)}/{r['job'].get('total')}]" if r["job"] else ""
        lines.append(f"  {r['age_h']:>8}  {r['name']:<10} pid {r['pid']:<7} {r['project']:<28}{tag}")
        lines.append(f"            {r['cmd'][:150]}")
    if not data["procs"]:
        lines.append("  （没有匹配的进程）")
    return "\n".join(lines)


HTML_HEAD = """<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta http-equiv="refresh" content="{refresh}">
<title>正在跑什么</title>
<style>
 body{{font:13px/1.6 -apple-system,"Segoe UI",sans-serif;margin:0;padding:22px 26px;background:#fff;color:#1f2328}}
 h1{{font-size:17px;margin:0 0 4px}} .muted{{color:#59636e}}
 table{{border-collapse:collapse;width:100%;margin-top:10px}}
 th,td{{text-align:left;padding:5px 10px 5px 0;border-bottom:1px solid #eaeef2;vertical-align:top}}
 th{{color:#59636e;font-weight:600;font-size:12px}}
 code{{font-family:ui-monospace,Consolas,monospace;font-size:11.5px;color:#59636e}}
 .age{{font-variant-numeric:tabular-nums;white-space:nowrap}}
 .chip{{display:inline-block;padding:0 8px;border-radius:999px;font-size:11.5px;border:1px solid}}
 .run{{background:#ddf4ff;color:#0969da;border-color:#b6e3ff}}
 .done{{background:#dafbe1;color:#1a7f37;border-color:#aceebb}}
 .stale{{background:#fff1e5;color:#bc4c00;border-color:#ffd8a8}}
</style></head><body>
"""


def render_html(data: dict, refresh: int = 5) -> str:
    parts = [HTML_HEAD.format(refresh=refresh),
             '<h1>正在跑什么</h1>',
             f'<div class="muted">扫描时间 {data["at"]} · 每 {refresh} 秒自动刷新 · 数据源：'
             'Windows 进程表 + DSH 会话目录 + 自报作业</div>']

    parts.append('<h2 style="font-size:14px;margin:18px 0 0">DSH 窗口（按最后活动）</h2><table>'
                 '<tr><th>最后活动</th><th>窗口标题</th><th>工作目录</th></tr>')
    for w in data["windows"][:8]:
        parts.append(f'<tr><td class="age">{w["last"]} <span class="muted">（{human_age(w["ago_s"])}前）</span></td>'
                     f'<td>{w["title"]} <span class="muted">[{w["sid"]}]</span></td>'
                     f'<td><code>{w["cwd"]}</code></td></tr>')
    parts.append("</table>")

    parts.append('<h2 style="font-size:14px;margin:18px 0 0">正在跑的进程</h2><table>'
                 '<tr><th>已运行</th><th>进程</th><th>PID</th><th>归属</th><th>进度</th><th>命令行</th></tr>')
    for r in data["procs"]:
        if r["job"]:
            j = r["job"]
            state = j.get("state", "")
            cls = "done" if state == "done" else ("stale" if state in ("failed", "stalled") else "run")
            total = j.get("total")
            prog = f'<span class="chip {cls}">{j.get("title", "作业")} {j.get("done", 0)}/{total}</span>'
            if j.get("step"):
                prog += f'<div class="muted" style="font-size:11.5px">{j["step"]}</div>'
        else:
            prog = '<span class="muted">—</span>'
        parts.append(
            f'<tr><td class="age">{r["age_h"]}</td><td>{r["name"]}</td><td>{r["pid"]}</td>'
            f'<td>{r["project"]}</td><td>{prog}</td><td><code>{r["cmd"][:220]}</code></td></tr>')
    parts.append("</table>")
    if not data["procs"]:
        parts.append('<p class="muted">（没有匹配的进程）</p>')
    parts.append("</body></html>")
    return "".join(parts)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="看现在有什么在跑、跑了多久、属于哪个窗口")
    ap.add_argument("--html", action="store_true", help="写 HTML 并打开浏览器")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    ap.add_argument("--watch", type=int, default=0, help="每 N 秒重写一次 HTML（常驻）")
    ap.add_argument("--refresh", type=int, default=5, help="HTML 自动刷新秒数")
    args = ap.parse_args(argv)

    if args.watch:
        print(f"[watch] 每 {args.watch}s 刷新 → {OUT_HTML}")
        webbrowser.open(OUT_HTML.as_uri()) if OUT_HTML.exists() else None
        while True:
            data = collect()
            OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
            OUT_HTML.write_text(render_html(data, args.refresh), encoding="utf-8")
            print(f"[watch] {data['at']} 进程 {len(data['procs'])} 个")
            time.sleep(args.watch)

    data = collect()
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0
    if args.html or args.refresh:
        OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
        OUT_HTML.write_text(render_html(data, args.refresh), encoding="utf-8")
        print(f"[html] {OUT_HTML}")
        if args.html:
            webbrowser.open(OUT_HTML.as_uri())
    if not args.json:
        print(render_text(data))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
