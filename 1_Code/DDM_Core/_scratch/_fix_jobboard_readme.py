from pathlib import Path
p = Path(r"1_Code/Tools/dsh-jobboard/README.md")
s = p.read_text(encoding="utf-8")
s = s.replace("node 1_Code/Tools/dsh-jobboard/test_host.mjs     # 13 项：导出、路由注册、JSON 形状、404/405",
              "node 1_Code/Tools/dsh-jobboard/test_host.mjs     # 20 项：导出、路由、/jobs、/state、404/405")
s = s.replace("├─ lib/index.mjs                       宿主侧：/jobboard-api/jobs",
              "├─ lib/index.mjs                       宿主侧：/jobboard-api/{jobs,state,health}")
p.write_text(s, encoding="utf-8", newline="\n")
print("readme updated")
