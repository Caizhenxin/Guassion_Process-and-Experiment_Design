#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""卸载作业面板：从 desired.json 里去掉本插件那一条（generation 目录留着，便于回滚）。

跑法：python -X utf8 1_Code/Tools/dsh-jobboard/uninstall.py [--apply]
之后重启 DSH Desktop。
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from install import DESIRED, generation_name, package_version  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    entry = generation_name(package_version())
    desired = json.loads(DESIRED.read_text(encoding="utf-8"))
    if entry not in desired:
        print(f"[=] desired.json 里没有 {entry}，无需卸载")
        return 0
    desired = [x for x in desired if x != entry]
    print(f"[-] 将移除 {entry}，剩余 {len(desired)} 个插件")
    if not args.apply:
        print("这是预演，加 --apply 真卸。")
        return 0
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    shutil.copy2(DESIRED, DESIRED.with_name(f"desired.json.bak-uninstall-{stamp}"))
    DESIRED.write_text(json.dumps(desired, indent=2, ensure_ascii=False) + "\n",
                       encoding="utf-8", newline="\n")
    print("[ok] 已移除；重启 DSH Desktop 生效。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
