import re
from pathlib import Path

ASAR = Path(r"D:\DSH\DSH Desktop\resources\app.asar")
data = ASAR.read_bytes()

print("=== 插件契约关键词计数 ===")
for n in ["contributes", "activationEvents", "clientPlugin", "client plugin",
          "webview", "sidebar", "panel", "dsh-plugin", "plugin.json",
          "dshPlugin", "commands", "views", "statusBar"]:
    print(f"{n:18s} {data.count(n.encode('utf-8'))}")

print("\n=== 'client plugin' 上下文（前 3 处）===")
for k, m in enumerate(re.finditer("client plugin".encode("utf-8"), data)):
    if k >= 3:
        break
    i = m.start()
    txt = data[max(0, i - 400): i + 500].decode("utf-8", "replace")
    print(re.sub(r"[\x00-\x08\x0b-\x1f]", "·", txt))
    print("-" * 70)
