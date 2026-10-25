#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把 `1_Code/Tools/dsh-jobboard` 装成 DSH 的一个「generation」，并挂进 desired.json。

DSH 的插件是按 **generation 目录**管理的（`$DSH_HOME/profiles/.generations/live/<pub>+<name>+<ver>+<hash>/`），
`desired.json` 是当前生效的 generation 列表。本脚本：

1. 按 DSH 自己的目录约定生成一个 generation（`node-linker=hoisted` ⇒ 直接拷真目录，不需要 pnpm）；
2. **备份** `desired.json` 后再追加自己这一条；
3. 打印回滚命令。

安全性：默认 dry-run，只看不写；`--apply` 才真装。回滚只需把备份的 desired.json 盖回去（或跑 `uninstall.py`）。

跑法：
    python -X utf8 1_Code/Tools/dsh-jobboard/install.py            # 预演
    python -X utf8 1_Code/Tools/dsh-jobboard/install.py --apply    # 真装（之后需重启 DSH）
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PKG_NAME = "@local/dsh-jobboard"
HERE = Path(__file__).resolve().parent
DSH_HOME = Path(os.environ.get("DSH_HOME") or
                Path.home() / "AppData" / "Roaming" / "dsh-desktop" / "harness")
GENS = DSH_HOME / "profiles" / ".generations"
LIVE = GENS / "live"
DESIRED = GENS / "desired.json"

NPMRC = """node-linker=hoisted
side-effects-cache=false
registry=https://mirrors.cloud.tencent.com/npm/
"""


def package_version() -> str:
    return json.loads((HERE / "package.json").read_text(encoding="utf-8"))["version"]


def generation_name(version: str) -> str:
    blob = (HERE / "package.json").read_bytes()
    digest = hashlib.sha256(blob + (HERE / "lib" / "client.js").read_bytes()).hexdigest()[:12]
    return f"local+dsh-jobboard+{version}+{digest}"


def load_desired() -> list[str]:
    return json.loads(DESIRED.read_text(encoding="utf-8"))


def build(gen: Path, version: str, apply: bool) -> None:
    target = gen / "node_modules" / "@local" / "dsh-jobboard"
    print(f"[gen] {gen}")
    print(f"[pkg] {target}")
    if not apply:
        return
    gen.mkdir(parents=True, exist_ok=True)
    (gen / "package.json").write_text(json.dumps({
        "name": "dsh-generation", "private": True, "version": "0.0.0",
        "dependencies": {PKG_NAME: version},
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    (gen / "generation.json").write_text(json.dumps({
        "pluginName": PKG_NAME, "version": version,
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    (gen / ".npmrc").write_text(NPMRC, encoding="utf-8", newline="\n")
    if target.exists():
        shutil.rmtree(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(HERE, target, ignore=shutil.ignore_patterns(
        "__pycache__", "*.py", "*.pyc", ".git"))
    print(f"[ok] 已写入 {target}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="真的写入（默认只预演）")
    args = ap.parse_args()

    if not DESIRED.exists():
        print(f"[x] 找不到 {DESIRED}（DSH_HOME 对不对？）")
        return 2

    version = package_version()
    gen = LIVE / generation_name(version)
    desired = load_desired()
    entry = gen.name

    # 同一个插件的旧 generation（改了代码 ⇒ 哈希变 ⇒ 新目录）从生效列表里摘掉，避免装两份。
    stale = [d for d in desired if d.startswith("local+dsh-jobboard+") and d != entry]

    print(f"DSH_HOME = {DSH_HOME}")
    print(f"版本     = {version}")
    print(f"已装插件 = {len(desired)} 个")
    if entry in desired:
        print("[=] desired.json 里已经有这一条，不重复追加")
    if stale:
        print(f"[~] 会摘掉旧版本：{', '.join(x.split('+')[2] + '+' + x.split('+')[3] for x in stale)}")

    build(gen, version, args.apply)

    if args.apply and (entry not in desired or stale):
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = DESIRED.with_name(f"desired.json.bak-jobboard-{stamp}")
        shutil.copy2(DESIRED, backup)
        print(f"[bak] {backup.name}")
        desired = [d for d in desired if d not in stale]
        if entry not in desired:
            desired.append(entry)
        DESIRED.write_text(json.dumps(desired, indent=2, ensure_ascii=False) + "\n",
                           encoding="utf-8", newline="\n")
        print(f"[ok] desired.json 现在是 {len(desired)} 个插件，末条 = {entry}")

    if not args.apply:
        print("\n这是预演。确认无误后加 --apply 真装，然后**重启 DSH Desktop**。")
    else:
        print("\n装好了。**重启 DSH Desktop** 后：左侧边栏出现「作业」条目 → 点开是面板。")
        print("回滚：把 desired.json.bak-jobboard-* 盖回 desired.json，再重启一次；"
              "或跑 uninstall.py --apply。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
