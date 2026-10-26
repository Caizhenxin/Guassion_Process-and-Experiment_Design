from pathlib import Path

p = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design"
         r"\1_Code\Experiment\stage8_watch.py")
s = p.read_text(encoding="utf-8")

start = s.index('def find_stage8_pids() -> list[int]:')
end = s.index('def read_pid(path: Path) -> int | None:')
new = '''def find_stage8_pids() -> list[int]:
    """从 OS 找**真正在跑**的 `stage8_run.py` 进程（不信 pid 文件）。

    ❗ 为什么需要这层：pid 文件是「我们自己写的约定」，而进程可能被会话回收、
    被手工杀掉、或由别的方式拉起（`Start-Process`、看板重启）。2026-10-25 的
    事故里，pid 文件写的是 cmd 包装器的 PID、包装器退出后 python 子进程还活着，
    于是看板误判「进程不在」并拉起第二个运行。直接问 OS 更可靠。

    实现上先用 `wmic`（老系统），再用 PowerShell 的 `Get-CimInstance`
    （Windows 11 起 `wmic` 已被移除，2026-10-25 实测本机就是 False）。
    """
    ps_cmd = ("Get-CimInstance Win32_Process -Filter \\"Name='python.exe'\\" | "
              "Where-Object { $_.CommandLine -match 'stage8_run' } | "
              "ForEach-Object { $_.ProcessId }")
    for cmd in (["wmic", "process", "where", "name='python.exe'",
                 "get", "processid,commandline", "/format:csv"],
                ["powershell", "-NoProfile", "-Command", ps_cmd]):
        try:
            out = subprocess.run(cmd, capture_output=True, text=True,
                                 errors="ignore", timeout=40).stdout
        except Exception:                                        # noqa: BLE001
            continue
        pids = []
        for line in out.splitlines():
            line = line.strip()
            if not line:
                continue
            if "stage8_run" in line:            # wmic 的 CSV 形态
                tail = line.rsplit(",", 1)[-1].strip()
                if tail.isdigit():
                    pids.append(int(tail))
            elif line.isdigit():                # powershell 的纯数字形态
                pids.append(int(line))
        if pids:
            return pids
    return []


'''
s = s[:start] + new + s[end:]
p.write_text(s, encoding="utf-8", newline="\n")
print("rewrote find_stage8_pids with powershell fallback")
