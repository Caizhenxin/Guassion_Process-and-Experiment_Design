"""Stage 8 长跑作业的实时看板 + 断线自动重启。

为什么有这个工具
================
Stage 8 全量拟合一次 2–5 h。它死掉是**静默的**：会话/终端一断，进程被回收，
日志停在「开始」那一行，输出目录可能一个字节都没有（组文件只在整组两个模型都
跑完时才落盘）。2026-10-25 因此白跑过一次（见
`Self-Repo/AI_Self_Improvement/2026-10-25_长时后台作业挂在会话上随重启被杀.md`）。

这个工具解决两件事：

1. **看得见**：每 30 s 生成一次 `status.html`（浏览器自动刷新）与 `status.json`，
   显示 8 个模型拟合的完成矩阵、每个模型的 ELPD / 耗时、ETA、日志心跳。
2. **掉线自动重启**：进程不在且作业未完成时，用 `--relaunch` 指定的启动脚本
   重新拉起（带 `--resume`，已完成的组直接复用），最多 `--max-restart` 次。

用法
====
    # 一次性快照（不循环、不重启）
    python -X utf8 1_Code/Experiment/stage8_watch.py --once

    # 持续监控（后台跑它；进程掉了自动重启）
    python -X utf8 1_Code/Experiment/stage8_watch.py --loop --every 30 \
        --relaunch 1_Code/DDM_Core/_scratch/_stage8_launch.cmd

产物（默认都在 --out-dir 下）：
    status.html   浏览器打开即可，15 s 自动刷新
    status.json   机器可读快照
    status.md     终端/聊天里贴的那种文本

退出码：0 = 作业已完成或正常运行中；1 = 已中断且未能重启。
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOG = ROOT / "1_Code/DDM_Core/_scratch/_stage8_d123_r2.log"
DEFAULT_OUT = ROOT / "2_Data/Real_Data/New_Design/_pipeline/stage8_d123"
DEFAULT_PID = ROOT / "1_Code/DDM_Core/_scratch/_stage8_d123_r2.pid"
DEFAULT_RELAUNCH = ROOT / "1_Code/DDM_Core/_scratch/_stage8_launch.cmd"

MODELS = ("M-T1", "M-T3")
MODEL_CN = {"M-T1": "M-T1（ρ 自由）", "M-T3": "M-T3（ρ 固定）"}

RE_GROUP = re.compile(r"^组 (\d)：(\d+) 人")
RE_START = re.compile(r"^\s*\[(M-T\d)\] rho_free=(\w+) 开始")
RE_DONE = re.compile(
    r"^\s*\[(M-T\d)\] 完成\s+([\d.]+)s：ELPD\s+(-?[\d.]+)\s*±\s*([\d.]+)"
    r"；p_loo\s+([\d.]+)；k_max\s+([\d.]+)")
RE_RESULT = re.compile(r"^\s*\[结果\]|stage8_results\.json")


# --------------------------------------------------------------------------- #
# 解析
# --------------------------------------------------------------------------- #
def parse_log(path: Path) -> dict:
    """把日志解析成 {组: {n_subj, models: {M: {...}}}}。"""
    groups: dict[str, dict] = {}
    cur_group = None
    tail: list[str] = []
    if not path.exists():
        return {"groups": {}, "tail": [], "mtime": None, "size": 0}
    text = path.read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines():
        m = RE_GROUP.match(line.strip())
        if m:
            cur_group = m.group(1)
            groups.setdefault(cur_group, {"n_subj": int(m.group(2)), "models": {}})
            continue
        m = RE_START.match(line)
        if m and cur_group:
            g = groups.setdefault(cur_group, {"n_subj": 0, "models": {}})
            g["models"].setdefault(m.group(1), {})
            g["models"][m.group(1)]["started"] = True
            g["models"][m.group(1)].setdefault("done", False)
            continue
        m = RE_DONE.match(line)
        if m and cur_group:
            g = groups.setdefault(cur_group, {"n_subj": 0, "models": {}})
            d = g["models"].setdefault(m.group(1), {})
            d.update({"done": True, "seconds": float(m.group(2)),
                      "elpd": float(m.group(3)), "elpd_se": float(m.group(4)),
                      "p_loo": float(m.group(5)), "k_max": float(m.group(6))})
            continue
    lines = [ln for ln in text.splitlines() if ln.strip()]
    tail = lines[-14:]
    st = path.stat()
    return {"groups": groups, "tail": tail,
            "mtime": datetime.fromtimestamp(st.st_mtime), "size": st.st_size}


def pid_alive(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                             capture_output=True, text=True, errors="ignore",
                             timeout=20).stdout
    except Exception:                                            # noqa: BLE001
        return False
    return str(pid) in out


def read_pid(path: Path) -> int | None:
    try:
        return int(path.read_text(encoding="ascii").strip().splitlines()[0])
    except Exception:                                            # noqa: BLE001
        return None


# --------------------------------------------------------------------------- #
# 状态推断
# --------------------------------------------------------------------------- #
def build_status(log_path: Path, out_dir: Path, pid_file: Path,
                 restarts: list[str], relaunch: Path | None,
                 n_groups: int = 4) -> dict:
    info = parse_log(log_path)
    # 预置组表：日志里还没出现的组也要显示成「等待」，否则进度分母会随日志变大
    for gid in [str(i) for i in range(1, n_groups + 1)]:
        info["groups"].setdefault(gid, {"n_subj": 0, "models": {}})
    pid = read_pid(pid_file)
    alive = pid_alive(pid)
    done_models = 0
    total_models = 0
    per_group = []
    durations: list[float] = []
    for gid in sorted(info["groups"]):
        g = info["groups"][gid]
        cells = []
        for mk in MODELS:
            total_models += 1
            d = g["models"].get(mk)
            if d and d.get("done"):
                done_models += 1
                durations.append(d["seconds"])
                cells.append({"model": mk, "state": "done",
                              "seconds": d.get("seconds"), "elpd": d.get("elpd"),
                              "elpd_se": d.get("elpd_se"), "p_loo": d.get("p_loo"),
                              "k_max": d.get("k_max")})
            elif d and d.get("started"):
                cells.append({"model": mk, "state": "running"})
            else:
                cells.append({"model": mk, "state": "waiting"})
        per_group.append({"group": gid, "n_subj": g["n_subj"], "cells": cells})

    # 结果文件是否落盘（= 整批完成）
    finished = (out_dir / "stage8_results.json").exists()

    # 进行中的那个模型已经跑了多久（用日志 mtime 与最近一次「开始」的时间差上级）
    mean_dur = (sum(durations) / len(durations)) if durations else 1000.0
    running = sum(1 for g in per_group for c in g["cells"] if c["state"] == "running")
    remaining = max(0.0, (total_models - done_models - 0.5 * running) * mean_dur)
    eta_seconds = remaining

    if finished:
        state, headline = "done", "✅ 全部完成"
    elif alive:
        state = "running"
        headline = f"⏳ 运行中（{done_models}/{total_models} 个模型拟合完成）"
    elif restarts:
        state, headline = "restarted", f"🔁 进程曾中断，已自动重启 {len(restarts)} 次"
    else:
        state, headline = "dead", "⛔ 进程不在，且未重启（作业已中断）"

    now = datetime.now()
    beat = None
    if info["mtime"]:
        beat = int((now - info["mtime"]).total_seconds() // 60)
    stale = beat is not None and beat > 90 and state == "running"

    return {
        "generated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "state": state, "headline": headline,
        "pid": pid, "alive": alive, "finished": finished,
        "done_models": done_models, "total_models": total_models,
        "progress": (done_models / total_models) if total_models else 0.0,
        "mean_model_seconds": mean_dur if durations else None,
        "eta_seconds": eta_seconds,
        "log_mtime": info["mtime"].strftime("%Y-%m-%d %H:%M:%S") if info["mtime"] else None,
        "log_size": info["size"],
        "heartbeat_min": beat, "stale": stale,
        "restarts": restarts, "relaunch": str(relaunch) if relaunch else None,
        "groups": per_group, "tail": info["tail"],
    }


# --------------------------------------------------------------------------- #
# 渲染
# --------------------------------------------------------------------------- #
def fmt_dur(sec: float | None) -> str:
    if sec is None:
        return "—"
    sec = int(sec)
    h, m = divmod(sec // 60, 60)
    return f"{h} h {m:02d} min" if h else f"{m} min"


CELL_STYLE = {
    "done":    ("#d6f5d6", "#1a7f37", "✅"),
    "running": ("#fff4cc", "#9a6700", "⏳"),
    "waiting": ("#f2f3f5", "#8b949e", "⬜"),
}


def render_html(st: dict) -> str:
    color = {"done": "#1a7f37", "running": "#9a6700",
             "restarted": "#bc4c00", "dead": "#cf222e"}[st["state"]]
    rows = []
    for g in st["groups"]:
        cells = []
        for c in g["cells"]:
            bg, fg, icon = CELL_STYLE[c["state"]]
            detail = ""
            if c["state"] == "done":
                detail = (f"ELPD {c['elpd']:.1f}±{c['elpd_se']:.1f}<br>"
                          f"<span style='font-size:11px;color:#57606a'>"
                          f"耗时 {fmt_dur(c['seconds'])}・p_loo {c['p_loo']:.0f}</span>")
            elif c["state"] == "running":
                detail = "<span style='font-size:11px;color:#9a6700'>拟合中…</span>"
            cells.append(
                f"<td style='background:{bg};color:{fg};border-radius:10px;"
                f"padding:10px 12px;text-align:center;min-width:150px'>"
                f"<b>{icon} {c['model']}</b><br>{detail}</td>")
        rows.append(
            f"<tr><td style='padding:8px 12px;font-weight:600'>组 {g['group']}"
            f"<br><span style='font-size:11px;color:#57606a'>"
            f"{g['n_subj'] or '—'} 人</span></td>"
            + "".join(cells) + "</tr>")

    pct = int(st["progress"] * 100)
    eta = fmt_dur(st["eta_seconds"]) if st["eta_seconds"] is not None else "—"
    beat = (f"{st['heartbeat_min']} 分钟前" if st["heartbeat_min"] is not None else "—")
    stale = ("<div style='background:#fff1f0;border:1px solid #ffcecb;color:#cf222e;"
             "padding:10px;border-radius:8px;margin:10px 0'>⚠️ 日志超过 90 分钟没有新行，"
             "进程虽然还在，但可能已经卡住 —— 建议人工看一眼。</div>") if st["stale"] else ""
    log_tail = "<br>".join(
        f"<span style='color:{'#cf222e' if ('ERROR' in ln or 'Traceback' in ln) else '#57606a'}'>"
        f"{ln.replace('<', '&lt;')[:150]}</span>" for ln in st["tail"]) or "（日志还没有内容）"
    restart_rows = "".join(f"<li>{t}</li>" for t in st["restarts"]) or "<li>无</li>"

    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta http-equiv="refresh" content="15">
<title>Stage 8 进度看板</title>
<style>
 body{{font-family:"Microsoft YaHei",system-ui,sans-serif;margin:0;padding:24px;background:#f6f8fa;color:#1f2328}}
 .wrap{{max-width:1060px;margin:0 auto}}
 .card{{background:#fff;border:1px solid #d0d7de;border-radius:14px;padding:20px;margin-bottom:16px}}
 h1{{font-size:19px;margin:0 0 4px}}
 .big{{font-size:26px;font-weight:700;color:{color};margin:6px 0 2px}}
 .bar{{height:14px;background:#eaeef2;border-radius:7px;overflow:hidden;margin:12px 0 6px}}
 .bar>div{{height:100%;width:{pct}%;background:{color};transition:width .4s}}
 .kv{{font-size:13px;color:#57606a}}
 table{{border-collapse:separate;border-spacing:8px}}
 pre{{background:#0d1117;color:#c9d1d9;padding:12px;border-radius:10px;overflow-x:auto;
      font-size:12px;line-height:1.55}}
 .foot{{font-size:12px;color:#8b949e;text-align:center}}
</style></head><body><div class="wrap">
<div class="card">
  <h1>Stage 8 全量拟合・实时看板（17 人 × 2 模型，quick 档）</h1>
  <div class="big">{st['headline']}</div>
  <div class="bar"><div></div></div>
  <div class="kv">进度 <b>{st['done_models']}/{st['total_models']}</b> 个模型拟合　·　
    预计剩余 <b>{eta}</b>　·　单模型均 <b>{fmt_dur(st['mean_model_seconds'])}</b>　·　
    进程 PID {st['pid'] or '—'}（{'存活' if st['alive'] else '不在'}）</div>
  <div class="kv">日志心跳：{beat}　·　日志大小 {st['log_size']:,} 字节　·　
    最近写入 {st['log_mtime'] or '—'}</div>
  {stale}
</div>

<div class="card">
  <h1>8 个模型拟合的完成矩阵</h1>
  <table>{''.join(rows)}</table>
  <div class="kv">组文件（<code>stage8_group_&lt;g&gt;.json</code>）只在整组两个模型都跑完后才落盘；
    因此「组 1 的 M-T1 完成」时磁盘上仍是空的，这是正常的。</div>
</div>

<div class="card">
  <h1>中断与自动重启</h1>
  <ul class="kv">{restart_rows}</ul>
  <div class="kv">重启命令：<code>{st['relaunch'] or '（未配置）'}</code>（带 <code>--resume</code>，已完成的组直接复用）</div>
</div>

<div class="card">
  <h1>日志尾部</h1>
  <pre>{log_tail}</pre>
</div>

<div class="foot">每 15 秒自动刷新　·　生成时间 {st['generated_at']}<br>
本页由 <code>1_Code/Experiment/stage8_watch.py</code> 生成，不需要联网</div>
</div></body></html>"""


def render_md(st: dict) -> str:
    lines = [f"# Stage 8 进度（{st['generated_at']}）", "",
             f"**{st['headline']}**", "",
             f"- 进度 {st['done_models']}/{st['total_models']}，预计剩余 "
             f"{fmt_dur(st['eta_seconds'])}，单模型均 {fmt_dur(st['mean_model_seconds'])}",
             f"- 进程 PID {st['pid']}（{'存活' if st['alive'] else '不在'}），"
             f"日志心跳 {st['heartbeat_min']} 分钟前",
             f"- 自动重启次数：{len(st['restarts'])}", "", "| 组 | 人数 | M-T1 | M-T3 |",
             "|---|---|---|---|"]
    for g in st["groups"]:
        cells = []
        for c in g["cells"]:
            if c["state"] == "done":
                cells.append(f"✅ {c['elpd']:.1f}（{fmt_dur(c['seconds'])}）")
            elif c["state"] == "running":
                cells.append("⏳ 拟合中")
            else:
                cells.append("⬜ 等待")
        lines.append(f"| {g['group']} | {g['n_subj']} | " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- #
# 主流程
# --------------------------------------------------------------------------- #
def relaunch_run(relaunch: Path) -> int | None:
    """用启动脚本拉起一次（分离进程），返回 pid。"""
    if not relaunch.exists():
        return None
    p = subprocess.Popen(["cmd", "/c", str(relaunch)],
                         cwd=str(ROOT), creationflags=0x08000000)  # CREATE_NO_WINDOW
    return p.pid


def emit_generic(st: dict, restarts: list[str], args) -> Path:
    """把看板状态同步成「作业面板」认的通用格式（`$DSH_HOME/jobboard/jobs/<id>/status.json`）。

    约定见 `1_Code/Tools/jobstatus.py`：面板只读这一个文件，所以别的长作业照着写就行。
    """
    sys.path.insert(0, str(ROOT / "1_Code" / "Tools"))
    import jobstatus  # noqa: E402

    state = "done" if st["finished"] else ("stalled" if not st["alive"] else "running")
    running = [(g.get("group"), c.get("model"))
               for g in st.get("groups", []) for c in g.get("cells", [])
               if c.get("state") == "running"]
    step = (f"组 {running[0][0]} · {running[0][1]} 拟合中" if running
            else f"{st['done_models']}/{st['total_models']} 个模型完成")
    payload = {
        "id": args.job_id,
        "title": f"Stage 8 真实数据（{args.n_subjects} 人）",
        "state": state,
        "step": step,
        "done": st["done_models"],
        "total": st["total_models"],
        "pid": st.get("pid"),
        "started_at": st.get("started_at") or st.get("generated_at"),
        "updated_at": st.get("generated_at"),
        "eta_seconds": st.get("eta_seconds"),
        "relaunch": str(args.relaunch) if args.relaunch else None,
        "log": str(args.log),
        "tail": (st.get("tail") or [])[-6:],
        "meta": {
            "心跳": f"{st.get('heartbeat_min')} 分钟",
            "自动重启": f"{len(restarts)} 次",
            "看板": str(args.out_dir / "status.html"),
        },
    }
    d = jobstatus.job_dir(args.job_id)
    d.mkdir(parents=True, exist_ok=True)
    tmp = d / "status.json.tmp"
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8", newline="\n")
    tmp.replace(d / "status.json")
    return d / "status.json"


def one_cycle(args, restarts: list[str]) -> dict:
    st = build_status(args.log, args.out_dir, args.pid_file, restarts, args.relaunch,
                      n_groups=args.n_groups)
    st["generated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "status.json").write_text(
        json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.out_dir / "status.html").write_text(render_html(st), encoding="utf-8")
    (args.out_dir / "status.md").write_text(render_md(st), encoding="utf-8")
    if args.job_id:
        emit_generic(st, restarts, args)
    return st


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Stage 8 实时看板 + 断线自动重启")
    ap.add_argument("--log", type=Path, default=DEFAULT_LOG)
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--pid-file", type=Path, default=DEFAULT_PID)
    ap.add_argument("--relaunch", type=Path, default=DEFAULT_RELAUNCH,
                    help="掉线时执行的启动脚本（.cmd）；不传则不自动重启")
    ap.add_argument("--max-restart", type=int, default=5)
    ap.add_argument("--n-groups", type=int, default=4,
                    help="预期组数（用于把尚未出现在日志里的组也画成「等待」）")
    ap.add_argument("--job-id", default="stage8_d123",
                    help="同步到「作业面板」的作业 id；传空串则不写通用 status.json")
    ap.add_argument("--n-subjects", type=int, default=17,
                    help="面板标题里显示的被试数")
    ap.add_argument("--every", type=int, default=30, help="轮询间隔（秒）")
    ap.add_argument("--once", action="store_true", help="只生成一次快照")
    args = ap.parse_args(argv)

    restarts: list[str] = []
    if args.once:
        st = one_cycle(args, restarts)
        print(render_md(st))
        return 0 if st["state"] in ("done", "running") else 1

    print(f"[watch] 每 {args.every} s 刷新一次；日志 {args.log}")
    print(f"[watch] 看板 {args.out_dir / 'status.html'}")
    while True:
        st = one_cycle(args, restarts)
        if st["finished"]:
            print(f"[watch] ✅ 已完成（{st['generated_at']}）")
            return 0
        if not st["alive"]:
            if len(restarts) >= args.max_restart:
                print(f"[watch] ⛔ 进程不在，且已达重启上限 {args.max_restart} 次")
                return 1
            pid = relaunch_run(args.relaunch)
            if pid is None:
                print(f"[watch] ⛔ 进程不在，且启动脚本缺失：{args.relaunch}")
                return 1
            args.pid_file.write_text(str(pid), encoding="ascii")
            stamp = datetime.now().strftime("%m-%d %H:%M:%S")
            restarts.append(f"{stamp}　检测到进程不在 ⇒ 重启（新 PID {pid}）")
            print(f"[watch] 🔁 {stamp} 重启，PID {pid}（第 {len(restarts)} 次）")
            one_cycle(args, restarts)
        else:
            print(f"[watch] {st['generated_at']} 进度 {st['done_models']}/"
                  f"{st['total_models']}，心跳 {st['heartbeat_min']} min，PID {st['pid']}")
        time.sleep(args.every)


if __name__ == "__main__":
    sys.exit(main())
