import sys
from pathlib import Path
asar = Path(r"C:\Users\蔡振辛\AppData\Local\Programs\DSH Desktop\resources\app.asar")
blob = asar.read_bytes()
print("asar bytes:", len(blob))
needles = [b"provide(\"sessions\")", b"provide('sessions')", b"remote.call", b"defineRemote",
           b"ctx.webServer", b"ctx.get('webServer')", b"ctx.get(\"webServer\")",
           b"registerHttp", b"addRoute", b"handleHttp"]
for n in needles:
    i = blob.find(n)
    print(f"--- {n!r} -> {i}")
    if i >= 0:
        s = blob[max(0, i - 260): i + 320].decode("utf-8", "replace")
        print(s.replace("\n", " ")[:580])
