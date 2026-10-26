"""看 asar 里「后台作业」附近的字符串上下文 + 是否有持久化文件名。"""
import re
from pathlib import Path

ASAR = Path(r"D:\DSH\DSH Desktop\resources\app.asar")
data = ASAR.read_bytes()

key = "后台作业".encode("utf-8")
i = data.find(key)
print("=== 后台作业 上下文 ===")
chunk = data[max(0, i - 600): i + 600]
txt = chunk.decode("utf-8", "replace")
print(re.sub(r"[\x00-\x08\x0b-\x1f]", "·", txt))

print("\n=== 持久化候选 ===")
for n in [b"jobs.json", b"job-store", b"jobs/", b"jobRegistry", b"job_history",
          b"jobEvents", b"jobManager", b"JobManager"]:
    print(f"{n.decode():14s} {data.count(n)}")
