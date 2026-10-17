# -*- coding: utf-8 -*-
"""把 D67 文档里的「自测 5/5」更新为「6/6」（新增历史 16 列口径守卫一例）。

为什么要脚本：同一句数字散在 5 份文档的 7 个位置，手改必漏；
每一步都断言「替换真的发生了」，否则当场失败而不是静默跳过。
"""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
APPLY = "--apply" in sys.argv

EDITS = [
    # (文件, 旧串, 新串)
    (ROOT / "5_Reference/08_工作流/工作流_主计划.md",
     "④ **自测 5/5**：干净数据（`make_fake_pilot.py` 现生成）通过；`--defect-1f` 拦住 6-C；"
     "`--defect-mismatch` 拦住 6-D；`Response=NA 但 RT 有值` 拦住 6-D；注入 `0x00` 字节拦住 6-D。",
     "④ **自测 6/6**：干净数据（`make_fake_pilot.py` 现生成）通过；`--defect-1f` 拦住 6-C；"
     "`--defect-mismatch` 拦住 6-D；`Response=NA 但 RT 有值` 拦住 6-D；注入 `0x00` 字节拦住 6-D；"
     "历史 16 列口径被「0 口径」守卫一句话拦住（不是喷一墙「缺列」）。"),
    (ROOT / "5_Reference/08_工作流/工作流_主计划.md",
     "自测 5 例（干净 / 帧量化缺陷 / 响应矛盾 / `NA` 约定 / `0x00` 字节）**5/5**",
     "自测 6 例（干净 / 帧量化缺陷 / 响应矛盾 / `NA` 约定 / `0x00` 字节 / 历史 16 列口径）**6/6**"),
    (ROOT / "5_Reference/08_工作流/工作流_主计划.md",
     "④ 自测 5/5：干净数据过、`--defect-1f` 拦 6-C、`--defect-mismatch` 拦 6-D、`NA` 带 RT 拦 6-D、`0x00` 拦 6-D。",
     "④ 自测 6/6：干净数据过、`--defect-1f` 拦 6-C、`--defect-mismatch` 拦 6-D、`NA` 带 RT 拦 6-D、"
     "`0x00` 拦 6-D、历史 16 列口径被「0 口径」守卫拦住。"),
    (ROOT / "5_Reference/08_工作流/工作流_主计划.md",
     "自测 **5/5**（干净 / `--defect-1f` / `--defect-mismatch` / `NA` 带 RT / `0x00` 字节）",
     "自测 **6/6**（干净 / `--defect-1f` / `--defect-mismatch` / `NA` 带 RT / `0x00` 字节 / 历史 16 列口径）"),
    (ROOT / "5_Reference/08_工作流/Stage1_技术验证记录.md",
     "判据由 `1_Code/Experiment/exp_Check/check_stage1_acceptance.py::self_test` 的 5 个用例守住"
     "（干净数据 + 4 种人为缺陷）。",
     "判据由 `1_Code/Experiment/exp_Check/check_stage1_acceptance.py::self_test` 的 6 个用例守住"
     "（干净数据 + 5 种人为缺陷，含「历史 16 列口径」被「0 口径」守卫拦住）。"),
    (ROOT / "1_Code/DDM_Core/README.md",
     "### 自测 5 例（`--self-test`）",
     "### 自测 6 例（`--self-test`）"),
    (ROOT / "1_Code/DDM_Core/README.md",
     "| 变异：文件里混进 `0x00` 字节 | 拦住 6-D | ✅ |",
     "| 变异：文件里混进 `0x00` 字节 | 拦住 6-D | ✅ |\n"
     "| 变异：历史 16 列口径（v2/v3 表头） | 拦住「0 口径」，一句话说明不适用 | ✅ |"),
    (ROOT / "1_Code/DDM_Core/README.md",
     "`check_stage1_acceptance.py` 覆盖 6-A–6-D（6-A/6-E 标为需手测）、自测 **5/5**；",
     "`check_stage1_acceptance.py` 覆盖 6-A–6-D（6-A/6-E 标为需手测）、自测 **6/6**（含历史 16 列口径守卫）；"),
]


def main() -> int:
    st: dict[Path, str] = {}
    for p, old, new in EDITS:
        if p not in st:
            st[p] = p.read_text(encoding="utf-8")
        # 幂等判据：用**新增的最后一**行是否已在文件里（而不是旧的锚点串，
        # 因为有的新串把旧串包含在内 ⇒ 用旧串判会把已经改好的文件再改一遍、插出重复行）。
        added = [ln for ln in new.split("\n") if ln and ln not in old]
        if added and all(ln in st[p] for ln in added):
            print(f"  [跳过] {p.name}：已是新文")
            continue
        n = st[p].count(old)
        if n != 1:
            raise SystemExit(f"❌ {p.name}：旧串出现 {n} 次（应为 1）\n   {old[:60]!r}")
        st[p] = st[p].replace(old, new)
        print(f"  [改] {p.name}：1 处")
    if APPLY:
        for p, text in st.items():
            p.write_text(text, encoding="utf-8", newline="\n")
        print(f"\n✅ 写盘 {len(st)} 个文件")
    else:
        print(f"\n⚠️ 干跑（涉及 {len(st)} 个文件）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
