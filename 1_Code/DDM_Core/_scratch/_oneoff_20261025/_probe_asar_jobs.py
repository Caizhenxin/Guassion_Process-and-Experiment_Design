"""在 app.asar 里按字节找 UI 侧「后台作业」相关字符串，判断 DSH 自带面板到什么程度。"""
from pathlib import Path

ASAR = Path(r"D:\DSH\DSH Desktop\resources\app.asar")
NEEDLES = [
    b"job_list", b"job_output", b"backgroundJobs", b"BackgroundJob",
    b"background jobs", b"\xe5\x90\x8e\xe5\x8f\xb0\xe4\xbd\x9c\xe4\xb8\x9a",  # 后台作业
    b"jobsPanel", b"JobPanel", b"task_list", b"subagent",
]

data = ASAR.read_bytes()
print(f"size {len(data)/1e6:.0f} MB")
for n in NEEDLES:
    c = data.count(n)
    try:
        label = n.decode("utf-8")
    except Exception:
        label = n.decode("latin-1")
    print(f"{label!r:26s} {c}")
