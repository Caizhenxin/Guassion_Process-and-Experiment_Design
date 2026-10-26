import re
from pathlib import Path

ASAR = Path(r"D:\DSH\DSH Desktop\resources\app.asar")
data = ASAR.read_bytes()

print("=== 计数 ===")
for n in ["持久终端", "terminal_list", "terminal", "persistent", "任务列表",
          "后台", "monitor", "watchdog", "重启"]:
    print(f"{n:14s} {data.count(n.encode('utf-8'))}")

print("\n=== 持久终端 上下文 ===")
for m in re.finditer("持久终端".encode("utf-8"), data):
    i = m.start()
    txt = data[max(0, i - 300): i + 300].decode("utf-8", "replace")
    print(re.sub(r"[\x00-\x08\x0b-\x1f]", "·", txt))
    print("-" * 60)
