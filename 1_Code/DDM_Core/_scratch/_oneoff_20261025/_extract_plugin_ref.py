"""把 asar 里 pluginManager 客户端插件的源码区抽出来，作为面板插件的模板参考。

只落盘 + 打印关键片段（注册侧边栏/主面板的那几行），避免刷屏。
"""
import re
from pathlib import Path

ASAR = Path(r"D:\DSH\DSH Desktop\resources\app.asar")
OUT = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design"
           r"\1_Code\DDM_Core\_scratch\_plugin_ref")
data = ASAR.read_bytes()

anchor = b"//#region lib/types/client/index.js"
i = data.find(anchor)
print(f"anchor at {i}")
if i < 0:
    raise SystemExit("not found")

# 向前找最近的 region 边界，向后取 60 KB
start = max(0, i - 2000)
chunk = data[start: i + 60000].decode("utf-8", "replace")
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "pluginManager_client.js.txt").write_text(chunk, encoding="utf-8")
print(f"wrote {len(chunk)} chars -> {OUT / 'pluginManager_client.js.txt'}")

# 打印 PANEL_ID 之后 60 行，看它怎么注册
lines = chunk.splitlines()
for k, ln in enumerate(lines):
    if "PANEL_ID" in ln or "slots" in ln.lower():
        lo, hi = max(0, k - 3), min(len(lines), k + 22)
        print(f"\n----- around line {k} -----")
        for t in lines[lo:hi]:
            print(t[:160])
        if k > 40:
            break
