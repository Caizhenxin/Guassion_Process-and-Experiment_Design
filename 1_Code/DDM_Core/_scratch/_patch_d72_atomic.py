# -*- coding: utf-8 -*-
"""D72 加固：单组缓存改成**原子写**（`*.tmp` + `os.replace`），并补 E16 牙齿。

原因：`Path.write_text` 不是原子的 —— 写到一半被杀（长跑最常见的死法）会留下**半截 JSON**。
`_load_group` 会把它当损坏缓存报错（好），但用户得手工删文件才能继续；而且半截文件与完整
文件在目录列表里长得一样。原子写让「存在」= 「完整」。

用法：python -X utf8 -u _patch_d72_atomic.py [--apply]
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
APPLY = "--apply" in sys.argv
SR = REPO / "1_Code" / "DDM_Core" / "stage8_run.py"
CK = REPO / "1_Code" / "DDM_Core" / "_scratch" / "check_stage8_run.py"

HELPER = '''

def _write_json_atomic(path: Path, obj) -> None:
    """原子写 JSON：先写 `<path>.tmp` 再 `os.replace`。
    ❗ 长跑被杀是常态，而 `Path.write_text` 写到一半会留下**半截 JSON**；
    原子写让「文件存在」= 「内容完整」，`--resume` 才不会读到残片。"""
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)
'''


def main() -> int:
    t = SR.read_text(encoding="utf-8")
    assert "\r" not in t
    if "_write_json_atomic" in t:
        print("  [跳过] stage8_run.py（已加固）")
    else:
        assert t.count("import json\n") == 1
        t = t.replace("import json\n", "import json\nimport os\n", 1)
        anchor = "\n\ndef main(argv=None) -> int:"
        assert t.count(anchor) == 1
        t = t.replace(anchor, HELPER + anchor, 1)
        old = ('        # ❗ 单组一落盘 ⇒ 长跑（真实 N 下几十小时）中途崩掉只丢当前组，不丢全部\n'
               '        gf.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")')
        assert t.count(old) == 1, "落盘锚点不唯一"
        t = t.replace(old,
                      '        # ❗ 单组一落盘 ⇒ 长跑（真实 N 下几十小时）中途崩掉只丢当前组，不丢全部；\n'
                      '        #    写盘走原子路径（D72）：半截文件不会冒充完整缓存\n'
                      '        _write_json_atomic(gf, obj)')
        if APPLY:
            SR.write_text(t, encoding="utf-8", newline="\n")
        print(f"  [{'写入' if APPLY else '干跑'}] stage8_run.py")

    c = CK.read_text(encoding="utf-8")
    assert "\r" not in c
    if "E16" in c:
        print("  [跳过] check_stage8_run.py（已加固）")
    else:
        old = '            ok13c = "FAKE-GROUP-1" in rep and "命中缓存" not in buf1.getvalue()'
        assert c.count(old) == 1
        c = c.replace(old, old + '\n            ok13d = not list(outd.glob("*.tmp"))')
        old = ("        check(\"E13 每组拟合完立刻落盘 `stage8_group_<组>.json`（长跑崩溃只丢当前组）\",\n"
               "              ok13a and ok13b and ok13c,")
        assert c.count(old) == 1
        c = c.replace(old,
                      "        check(\"E13 每组拟合完立刻落盘 `stage8_group_<组>.json`（长跑崩溃只丢当前组）\",\n"
                      "              ok13a and ok13b and ok13c and ok13d,")
        old = '        check("E14b 缓存损坏 ⇒ 报 ValueError（不静默重拟合）", ok14b, det14b)'
        assert c.count(old) == 1
        c = c.replace(old, old + '''

    # E16（D72 加固）：缓存必须**原子**落盘 —— `Path.write_text` 写到一半被杀会留下
    # 半截 JSON，`--resume` 就会把它当损坏缓存（用户得手工删）；原子写让「存在」=「完整」。
    src2 = inspect.getsource(SR)
    ok16 = ("_write_json_atomic" in src2 and "os.replace(tmp, path)" in src2
            and "gf.write_text(" not in src2 and "import os" in src2)
    check("E16 静态：单组缓存走 `*.tmp` + `os.replace`（原子写，半截文件不冒充完整缓存）", ok16)''')
        if APPLY:
            CK.write_text(c, encoding="utf-8", newline="\n")
        print(f"  [{'写入' if APPLY else '干跑'}] check_stage8_run.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
