"""按 `PANEL_ID = "plugins"` 锚点抽 pluginManager 客户端源码，作为侧边栏面板插件模板。"""
import re
from pathlib import Path

ASAR = Path(r"D:\DSH\DSH Desktop\resources\app.asar")
OUT = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design"
           r"\1_Code\DDM_Core\_scratch\_plugin_ref")
data = ASAR.read_bytes()

i = data.find(b'const PANEL_ID = "plugins"')
print(f"anchor {i}")
chunk = data[max(0, i - 4000): i + 40000].decode("utf-8", "replace")
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "pluginManager_client.js").write_text(chunk, encoding="utf-8")
print(f"wrote {len(chunk)} chars")

lines = chunk.splitlines()
keys = ("PANEL_ID", "inject", "slots", "NS =")
shown = 0
for k, ln in enumerate(lines):
    if any(s in ln for s in keys) and len(ln) < 200:
        print(f"{k:6d}| {ln[:150]}")
        shown += 1
        if shown > 45:
            break
