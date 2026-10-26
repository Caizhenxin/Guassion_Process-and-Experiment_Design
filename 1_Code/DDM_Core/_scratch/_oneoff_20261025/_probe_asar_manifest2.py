import re
from pathlib import Path

ASAR = Path(r"D:\DSH\DSH Desktop\resources\app.asar")
data = ASAR.read_bytes()

def show(needle: str, before=1200, after=200, limit=2, tag=""):
    print(f"\n=== {tag or needle} ===")
    pat = re.compile(re.escape(needle.encode("utf-8")))
    for k, m in enumerate(pat.finditer(data)):
        if k >= limit:
            break
        i = m.start()
        txt = data[max(0, i - before): i + after].decode("utf-8", "replace")
        print(re.sub(r"[\x00-\x08\x0b-\x1f]", "·", txt))
        print("-" * 70)

show('"keywords": [\n    "dsh-plugin"', before=1600, after=60, limit=1,
     tag="dsh-ppt package.json 前半")
show('"dsh":', before=80, after=700, limit=2, tag='"dsh": 字段')
print("\n=== 插件加载相关字符串 ===")
for n in ["plugins directory", "pluginDir", "installPlugin", "loadPlugin",
          "pluginRoot", "contributes.panels", "contributesPanels",
          "client-plugins", "clientPlugins"]:
    print(f"{n:22s} {data.count(n.encode('utf-8'))}")
