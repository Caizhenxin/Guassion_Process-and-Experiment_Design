# -*- coding: utf-8 -*-
"""D86 缺口收尾（第二轮）：§9-70 用更严的锚点插入；把两处 T5 自身描述里的
`[文字](相对路径)` 改成不会自我命中的写法；白名单补 keyflip 夹具。"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
README = ROOT / "1_Code" / "DDM_Core" / "README.md"
PLAN = ROOT / "5_Reference" / "08_工作流" / "工作流_主计划.md"
CHECKER = ROOT / "1_Code" / "DDM_Core" / "_scratch" / "check_traceability.py"

ITEM70 = (
    "| 70 | ✅ **文档可追溯性检查器 T1–T5（D86，§8.59）** | "
    "`check_traceability.py`（零依赖、1172 项检查）抓住 README §9 断号与 D 编号断号；"
    "首跑 44 条假红靠「先怀疑判据」纠正（标题层级 + 加粗/删除线格式），`--self-test` 5/5 | "
    "`1_Code/DDM_Core/_scratch/check_traceability.py`（约 291 行） |"
)


def main():
    # ---- README：§9 第 70 项 ----
    rd = README.read_text(encoding="utf-8")
    lines = rd.split("\n")
    n71 = [i for i, ln in enumerate(lines) if ln.startswith("| 71 | ✅")]
    assert len(n71) == 1, "§9 第 71 项锚点命中 %d 次" % len(n71)
    have70 = any(ln.startswith("| 70 | ✅") for ln in lines)
    if not have70:
        lines.insert(n71[0], ITEM70)
        print("readme: §9-70 已插入")
    rd = "\n".join(lines)

    # ---- 两处 T5 描述：改成不会自我命中的写法 ----
    old = "文档间 `[文字](相对路径)` 链接必须存在"
    new = "文档间的方括号文字 + 圆括号路径（相对路径）必须指向真实文件"
    if old in rd:
        rd = rd.replace(old, new)
        print("readme: T5 描述已改写")
    README.write_text(rd, encoding="utf-8", newline="\n")

    pl = PLAN.read_text(encoding="utf-8")
    old2 = "T5 文档间 `[文字](相对路径)` 链接必须存在"
    new2 = "T5 文档间的方括号文字 + 圆括号路径（相对路径）必须指向真实文件"
    if old2 in pl:
        pl = pl.replace(old2, new2)
        PLAN.write_text(pl, encoding="utf-8", newline="\n")
        print("plan: T5 描述已改写")

    # ---- 白名单：运行时生成的 keyflip 夹具 ----
    ck = CHECKER.read_text(encoding="utf-8")
    if "keyflip" not in ck:
        anchor = 'RUNTIME_WHITELIST = (\n'
        assert ck.count(anchor) == 1, "白名单锚点未命中"
        ck = ck.replace(
            anchor,
            anchor
            + '    # 由 check_read_formal_data.py 运行时生成的负样例夹具（第 13 列 f↔j 互换），不入仓\n'
            + '    "exp_group1_subject1_keyflip.txt",\n',
            1,
        )
        CHECKER.write_text(ck, encoding="utf-8", newline="\n")
        print("checker: 白名单已补 keyflip")
    print("done")


if __name__ == "__main__":
    main()
