from pathlib import Path

idx = Path(r"D:\GitHub_programe\GitHub\Self-Repo\AI_Self_Improvement\INDEX.md")
text = idx.read_text(encoding="utf-8")
row = ("| 2026-10-25 | 批处理启动脚本写成 LF 换行 ⇒ cmd 静默失败；自动重启无冷却，2 分钟烧光 5 次额度 | "
       "`#批处理` `#CRLF` `#cmd静默失败` `#自动重启` `#无冷却` `#pid文件不可信` `#缓存粒度` | "
       "[2026-10-25_批处理脚本LF换行导致cmd静默失败与重启烧光额度.md]"
       "(./2026-10-25_批处理脚本LF换行导致cmd静默失败与重启烧光额度.md) |")
if "批处理脚本LF换行" in text:
    print("已存在，跳过")
else:
    if not text.endswith("\n"):
        text += "\n"
    text += row + "\n"
    idx.write_text(text, encoding="utf-8", newline="\n")
    print(f"已追加；现 {len(text.splitlines())} 行")
