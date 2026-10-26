from pathlib import Path

p = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design"
         r"\1_Code\Experiment\stage8_watch.py")
s = p.read_text(encoding="utf-8")

# 1) 新增 --min-gap
old = """    ap.add_argument("--max-restart", type=int, default=5)"""
new = """    ap.add_argument("--max-restart", type=int, default=5)
    ap.add_argument("--min-gap", type=int, default=180,
                    help="两次重启之间的最小间隔（秒）。防止启动脚本本身坏掉时"
                         "在 2 分钟内把重启额度烧光（2026-10-25 踩过）")"""
assert s.count(old) == 1
s = s.replace(old, new)

# 2) 冷却逻辑：不到间隔就先等，不消耗额度
old = """        if not st["alive"]:
            if len(restarts) >= args.max_restart:"""
new = """        if not st["alive"]:
            if last_restart[0] is not None and (time.time() - last_restart[0]) < args.min_gap:
                wait = int(args.min_gap - (time.time() - last_restart[0]))
                print(f"[watch] 冷却中（{wait}s 后才允许再次重启），不消耗重启额度")
                time.sleep(args.every)
                continue
            if len(restarts) >= args.max_restart:"""
assert s.count(old) == 1
s = s.replace(old, new)

# 3) 记录最近一次重启时间
old = """            restarts.append(f"{stamp}　检测到进程不在 ⇒ 重启（新 PID {pid}）")"""
new = """            restarts.append(f"{stamp}　检测到进程不在 ⇒ 重启（新 PID {pid}）")
            last_restart[0] = time.time()"""
assert s.count(old) == 1
s = s.replace(old, new)

# 4) 初始化 last_restart
old = """    restarts: list[str] = []
    if args.once:"""
new = """    restarts: list[str] = []
    last_restart: list[float | None] = [None]
    if args.once:"""
assert s.count(old) == 1
s = s.replace(old, new)

p.write_text(s, encoding="utf-8", newline="\n")
print("patched: --min-gap cooldown")
