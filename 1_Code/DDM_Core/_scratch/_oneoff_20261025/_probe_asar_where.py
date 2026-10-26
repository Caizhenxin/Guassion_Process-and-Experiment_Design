import re
from pathlib import Path

ASAR = Path(r"D:\DSH\DSH Desktop\resources\app.asar")
data = ASAR.read_bytes()

def show(needle: str, before=400, after=600, limit=2, tag=""):
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

show('"plugins"', before=250, after=350, limit=3, tag='"plugins" 目录名')
show('plugin-recovery', before=200, after=300, limit=2, tag='plugin-recovery')
