"""探 DSH 从哪里加载第三方插件（安装根目录），用于决定我们面板插件放哪。"""
import re
from pathlib import Path

ASAR = Path(r"D:\DSH\DSH Desktop\resources\app.asar")
data = ASAR.read_bytes()

def show(needle: str, before=350, after=550, limit=3, tag=""):
    print(f"\n=== {tag or needle} ===")
    pat = re.compile(re.escape(needle.encode("utf-8")))
    n = 0
    for m in pat.finditer(data):
        if n >= limit:
            break
        n += 1
        i = m.start()
        txt = data[max(0, i - before): i + after].decode("utf-8", "replace")
        print(re.sub(r"[\x00-\x08\x0b-\x1f]", "·", txt))
        print("-" * 70)

show("pluginRoot", limit=2)
show("installPlugin", limit=2)
show("dsh-market", limit=2)
