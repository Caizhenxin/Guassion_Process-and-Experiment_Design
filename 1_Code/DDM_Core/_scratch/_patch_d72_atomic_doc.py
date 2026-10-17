# -*- coding: utf-8 -*-
"""把 D72 的「原子写」加固写进三份文档（计数 30 → 31）。幂等。

注意：三份文档里 `30/30` 有多个主人（`check_read_formal_data.py` 也是 30/30），
所以**只改与 `check_stage8_run.py` 相邻**的那几个 —— 逐个用带上下文的锚点替换。
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
APPLY = "--apply" in sys.argv

MP = REPO / "5_Reference" / "08_工作流" / "工作流_主计划.md"
S8 = REPO / "5_Reference" / "08_工作流" / "Stage8_建模与验证方案.md"
RD = REPO / "1_Code" / "DDM_Core" / "README.md"

EDITS_MP = [
    ("**26 → 30 项**（E13 落盘且报告含该组结果、",
     "**26 → 31 项**（E13 落盘且报告含该组结果、"),
    ("E15 换 `n_em` 必须报配置不一致、E14b 坏缓存报错）。",
     "E15 换 `n_em` 必须报配置不一致、E14b 坏缓存报错、**E16 缓存走 `*.tmp` + `os.replace` 原子写**）。"),
    ("（缓存绑定配置，损坏/不一致都报错），`check_stage8_run.py` **30/30**。 |",
     "（缓存绑定配置，损坏/不一致都报错、写盘原子），`check_stage8_run.py` **31/31**。 |"),
    ("坏缓存也报错。`check_stage8_run.py` **26 → 30/30**（E13",
     "坏缓存也报错；缓存走 `*.tmp` + `os.replace` 原子写。`check_stage8_run.py` **26 → 31/31**（E13"),
    ("+ `_scratch/check_stage8_run.py`（**30/30**，E13–E15）",
     "+ `_scratch/check_stage8_run.py`（**31/31**，E13–E16）"),
]

EDITS_S8 = [
    ("`_scratch/check_stage8_run.py` **30/30**（E13 落盘与报告内容",
     "`_scratch/check_stage8_run.py` **31/31**（E13 落盘与报告内容"),
    ("E14b 坏缓存报错）；E 组原 26 项仍全绿 |",
     "E14b 坏缓存报错、E16 缓存走 `*.tmp` + `os.replace` 原子写）；E 组原 26 项仍全绿 |"),
]

EDITS_RD = [
    ("3. **证据**：`_scratch/check_stage8_run.py` **30/30**（E13",
     "3. **证据**：`_scratch/check_stage8_run.py` **31/31**（E13"),
    ("坏缓存/配置不一致都`ValueError`；`check_stage8_run.py` **30/30**（E13",
     "坏缓存/配置不一致都`ValueError`；`check_stage8_run.py` **31/31**（E13"),
    ("）：每组拟合完立刻写 `stage8_group_<组>.json`",
     "）：每组拟合完立刻**原子**写 `stage8_group_<组>.json`（`*.tmp` + `os.replace`："
     "长跑被杀时半截文件不会冒充完整缓存）"),
    ("E14b 坏缓存报错）。",
     "E14b 坏缓存报错、E16 缓存走 `*.tmp` + `os.replace`）。"),
]


def run(path: Path, edits: list) -> None:
    t = path.read_text(encoding="utf-8")
    assert "\r" not in t
    if "E16" in t and "31/31" in t:
        print(f"  [跳过] {path.name}（已加固）")
        return
    for old, new in edits:
        n = t.count(old)
        assert n == 1, f"{path.name}：锚点命中 {n} 处 :: {old[:50]}"
        t = t.replace(old, new)
    if APPLY:
        path.write_text(t, encoding="utf-8", newline="\n")
    print(f"  [{'写入' if APPLY else '干跑'}] {path.name}：{len(edits)} 处")


def main() -> int:
    print(f"模式：{'真写' if APPLY else '干跑'}")
    run(MP, EDITS_MP)
    run(S8, EDITS_S8)
    run(RD, EDITS_RD)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
