import re
from pathlib import Path

ASAR = Path(r"D:\DSH\DSH Desktop\resources\app.asar")
data = ASAR.read_bytes()

def show(needle: bytes, before=300, after=700, limit=3, tag=""):
    print(f"\n=== {tag or needle.decode()} ===")
    for k, m in enumerate(re.finditer(needle, data)):
        if k >= limit:
            break
        i = m.start()
        txt = data[max(0, i - before): i + after].decode("utf-8", "replace")
        print(re.sub(r"[\x00-\x08\x0b-\x1f]", "·", txt))
        print("-" * 70)

show(b'"dsh-plugin"', tag='"dsh-plugin"')
show(b'"contributes"', tag='"contributes"')
