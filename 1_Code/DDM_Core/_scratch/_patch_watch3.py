from pathlib import Path

p = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design"
         r"\1_Code\Experiment\stage8_watch.py")
s = p.read_text(encoding="utf-8")

old = '''def read_pid(path: Path) -> int | None:'''
new = '''def find_stage8_pids() -> list[int]:
    """从 OS 找**真正在跑**的 `stage8_run.py` 进程（不信 pid 文件）。

    ❗ 为什么需要这层：pid 文件是「我们自己写的约定」，而进程可能被会话回收、
    被手工杀掉、或由别的方式拉起（`Start-Process`、看板重启）。2026-10-25 的
    事故里，pid 文件写的是 cmd 包装器的 PID、包装器退出后 python 子进程还活着，
    于是看板误判「进程不在」并拉起第二个运行。直接问 OS 更可靠。
    """
    try:
        out = subprocess.run(
            ["wmic", "process", "where", "name='python.exe'",
             "get", "processid,commandline", "/format:csv"],
            capture_output=True, text=True, errors="ignore", timeout=25).stdout
    except Exception:                                            # noqa: BLE001
        return []
    pids = []
    for line in out.splitlines():
        if "stage8_run" not in line:
            continue
        tail = line.rsplit(",", 1)[-1].strip()
        if tail.isdigit():
            pids.append(int(tail))
    return pids


def read_pid(path: Path) -> int | None:'''
assert s.count(old) == 1
s = s.replace(old, new)

old = '''    pid = read_pid(pid_file)
    alive = pid_alive(pid)'''
new = '''    pid = read_pid(pid_file)
    alive = pid_alive(pid)
    adopted = None
    if not alive:
        # pid 文件不可信时以 OS 为准（见 find_stage8_pids 的说明）
        live = find_stage8_pids()
        if live:
            pid, alive, adopted = live[0], True, live[0]
            try:
                pid_file.write_text(str(pid), encoding="ascii")
            except Exception:                                    # noqa: BLE001
                pass'''
assert s.count(old) == 1
s = s.replace(old, new)

p.write_text(s, encoding="utf-8", newline="\n")
print("patched: OS-level process discovery")
