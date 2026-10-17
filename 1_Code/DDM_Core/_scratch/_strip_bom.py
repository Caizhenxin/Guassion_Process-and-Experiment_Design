# -*- coding: utf-8 -*-
"""剥掉 UTF-8 BOM（本项目全线裸 LF、无 BOM）。

用法：
    python 1_Code/DDM_Core/_scratch/_strip_bom.py            # 干跑，列被 BOM 污染的文件
    python 1_Code/DDM_Core/_scratch/_strip_bom.py --apply    # 写回（同时把 CRLF 规范化成 LF）
"""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOTS = (Path("1_Code"), Path("5_Reference"))
SKIP_DIRS = {"__pycache__", ".git", "_历史版本", "_旧稿", "_抽取文本", "99_归档"}


def main() -> int:
    apply = "--apply" in sys.argv
    hits = []
    for root in ROOTS:
        for p in sorted(root.rglob("*")):
            if not p.is_file() or p.suffix.lower() not in (".py", ".md", ".txt", ".csv", ".json"):
                continue
            if any(s in p.parts for s in SKIP_DIRS):
                continue
            raw = p.read_bytes()
            if raw.startswith(b"\xef\xbb\xbf"):
                hits.append(p)
    print(f"发现 {len(hits)} 个带 UTF-8 BOM 的文件：")
    for p in hits:
        raw = p.read_bytes()
        body = raw[3:].replace(b"\r\n", b"\n")
        print(f"  {p}（{len(raw)} B → {len(body)} B）")
        if apply:
            p.write_bytes(body)
    if not hits:
        print("（无）")
        return 0
    print(f"{'已写回' if apply else '（干跑，未写回）'}：{len(hits)} 个")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
