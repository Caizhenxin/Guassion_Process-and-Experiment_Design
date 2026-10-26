from pathlib import Path

p = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design"
         r"\1_Code\Experiment\stage8_watch.py")
s = p.read_text(encoding="utf-8")

# 1) build_status 预置组数与组表
old = """def build_status(log_path: Path, out_dir: Path, pid_file: Path,
                 restarts: list[str], relaunch: Path | None) -> dict:
    info = parse_log(log_path)"""
new = """def build_status(log_path: Path, out_dir: Path, pid_file: Path,
                 restarts: list[str], relaunch: Path | None,
                 n_groups: int = 4) -> dict:
    info = parse_log(log_path)
    # 预置组表：日志里还没出现的组也要显示成「等待」，否则进度分母会随日志变大
    for gid in [str(i) for i in range(1, n_groups + 1)]:
        info["groups"].setdefault(gid, {"n_subj": 0, "models": {}})"""
assert s.count(old) == 1
s = s.replace(old, new)

# 2) ETA 始终可算（无已完成模型时用 1000 s/模型 的兜底）
old = """    if durations:
        eta_seconds = remaining
    else:
        eta_seconds = None"""
new = """    eta_seconds = remaining"""
assert s.count(old) == 1
s = s.replace(old, new)

# 3) one_cycle 传递 n_groups
old = """    st = build_status(args.log, args.out_dir, args.pid_file, restarts, args.relaunch)"""
new = """    st = build_status(args.log, args.out_dir, args.pid_file, restarts, args.relaunch,
                      n_groups=args.n_groups)"""
assert s.count(old) == 1
s = s.replace(old, new)

# 4) CLI 增加 --n-groups
old = """    ap.add_argument("--max-restart", type=int, default=5)"""
new = """    ap.add_argument("--max-restart", type=int, default=5)
    ap.add_argument("--n-groups", type=int, default=4,
                    help="预期组数（用于把尚未出现在日志里的组也画成「等待」）")"""
assert s.count(old) == 1
s = s.replace(old, new)

# 5) 组号为 0 人时显示 —
old = """f"<br><span style='font-size:11px;color:#57606a'>{g['n_subj']} 人</span></td>\""""
new = """f"<br><span style='font-size:11px;color:#57606a'>"
            f"{g['n_subj'] or '—'} 人</span></td>\""""
assert s.count(old) == 1
s = s.replace(old, new)

p.write_text(s, encoding="utf-8", newline="\n")
print("patched stage8_watch.py")
