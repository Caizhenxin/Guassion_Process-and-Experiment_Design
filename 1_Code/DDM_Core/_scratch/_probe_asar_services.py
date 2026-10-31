"""在 app.asar 里找「服务目录」和「HTTP 路由」，判断作业/会话能否被插件读到。"""
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(r"C:\Users\蔡振辛\AppData\Local\Programs\DSH Desktop\resources")
ASAR = ROOT / "app.asar"

data = ASAR.read_bytes()
print(f"asar = {len(data)/1e6:.1f} MB")

# 只看 ASCII 文本片段，避免把二进制当字符串
text = data.decode("latin-1")

pats = {
    "ctx.get(\"X\")": re.compile(r"ctx\.get\(\"([A-Za-z][A-Za-z0-9_]{1,30})\"\)"),
    "provide(\"X\")": re.compile(r"provide\(\"([A-Za-z][A-Za-z0-9_]{1,30})\""),
    "getService(\"X\")": re.compile(r"getService\(\"([A-Za-z][A-Za-z0-9_]{1,30})\""),
    "inject [..]": re.compile(r"inject\s*[:=]\s*\[([^\]]{0,200})\]"),
}

for label, pat in pats.items():
    hits = Counter(pat.findall(text))
    print(f"\n=== {label} 共 {sum(hits.values())} 次，{len(hits)} 种 ===")
    for name, n in hits.most_common(45):
        print(f"  {n:4d}  {name}")

# 客户端/宿主可能已有的 HTTP 路由
routes = Counter(re.findall(r"\"/api/[a-zA-Z0-9_/\-]{1,40}\"", text))
print(f"\n=== /api/ 路由 {len(routes)} 种 ===")
for name, n in routes.most_common(40):
    print(f"  {n:4d}  {name}")

# 关键词命中，帮助判断有没有现成的「作业」视图
for kw in ("backgroundTasks", "backgroundJob", "jobList", "taskList", "subagentList",
           "activeJobs", "runningTasks"):
    n = text.count(kw)
    if n:
        print(f"[kw] {kw}: {n}")
