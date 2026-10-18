# -*- coding: utf-8 -*-
"""补 D86 的缺口：主计划 D86 决策行 + README §8.59 + §9 第 70 项；
并把 `exp_group1_subject1_keyflip.txt`（运行时生成的负样例夹具）加进追溯性检查器的白名单。

背景：D86（文档可追溯性检查器）当时只落了进度行与部分 §9，决策行/§8.59/§9-70 三个位置都漏了；
D90 落纸后 `check_traceability.py` 报「README §9 编号不连续（缺 70）」「主计划 D 编号缺 86」，
正好把这三处缺口暴露出来（检查器抓到了它自己那条决策的落纸不全）。
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PLAN = ROOT / "5_Reference" / "08_工作流" / "工作流_主计划.md"
README = ROOT / "1_Code" / "DDM_Core" / "README.md"
CHECKER = ROOT / "1_Code" / "DDM_Core" / "_scratch" / "check_traceability.py"

D86_ROW = (
    "| **D86** | 2026-10-18 | ✅ **把「文档说过的话是否都有落地物」变成可执行检查（`check_traceability.py`）**。"
    "① 动机：同类漂移已两次靠人肉发现（README §9 停在 63 项、§8.5x 停在 §8.54，D80–D84 落了纸但索引没加），"
    "而 `check_files.py`（只管裸 LF/BOM/ast）与 `check_table_integrity.py`（只管表格结构）都拓不到。"
    "② 五项检查：T1 主计划里反引号包住的路径必须存在（三级解析：仓库根 / `1_Code/DDM_Core` / `1_Code/Experiment` / "
    "`…/exp_matlab` / `…/test` / `5_Reference/08_工作流` + 同名文件索引）；T2 README §9 编号从 1 连续不重复；"
    "T3 README 里 `§8.x` 引用必须有对应标题；T4 主计划 `Dn` 编号唯一且连续；T5 文档间 `[文字](相对路径)` 链接必须存在。"
    "③ 首跑 44 条「README 引用了 §8.23–§8.44 但没有这个标题」全是**假红**：早期节是 `## 8.23`（h2）、后期是 `### 8.57`（h3）、"
    "子节是 `#### 8.22.1` ⇒ 判据改 `^#{2,6} (8\\.\\d+)[ ：:.、]`。"
    "④ 首跑报「D 编号缺 [1,2,3,4,21]」也是假红：早期决策行不加粗（`| D1 | … |`）、被撤回的是删除线（`| ~~D21~~ | … |`）"
    "⇒ 判据改 `^\\| (?:\\*\\*|~~)?D(\\d+)(?:\\*\\*|~~)? \\|`。"
    "⑤ 修完后 **1172 项检查、只剩 2 个真问题**（同一文件 `exp_group1_subject1_keyflip.txt`，实为运行时生成的夹具）。"
    "⑥ `--self-test` **5/5**（跳号被抓 / 连续放行 / 悬空 §8.99 判红 / §8.1 放行 / 不存在路径判红） | "
    "`1_Code/DDM_Core/_scratch/check_traceability.py`（**新建**，零依赖、只读，约 291 行） | "
    "把 D86/D90 的编号缺口补齐后复跑；后续每次落纸都跑一次 |"
)

README_SECTION = """### 8.59 文档说过的话，有没有落地物（2026-10-18，D86）

**问题**：这条工作流已经两次在同一类地方翻车，且都是人肉发现的——README §9 的编号停在**第 63 项（D79）**、§8.5x 停在 **§8.54**，而 D80–D84 的决策落了纸、索引没加。这类漂移不报错、不影响程序，`check_files.py`（裸 LF / BOM / ast）与 `check_table_integrity.py`（表格结构）都拓不到，伤的是「后来的人能不能顺着文档找到东西」。

**做法**：`1_Code/DDM_Core/_scratch/check_traceability.py`（零依赖、只读）五项检查——T1 主计划里反引号包住的路径必须存在；T2 README §9 编号从 1 连续不重复；T3 README 里 `§8.x` 引用必须有对应标题；T4 主计划 `Dn` 编号唯一且连续；T5 文档间 `[文字](相对路径)` 链接必须存在。路径解析做了三级兜底（仓库根 / `1_Code/DDM_Core` / `1_Code/Experiment` / `…/exp_matlab` / `…/test` / `5_Reference/08_工作流`，再加一个同名文件索引），命中不到时区分 `ok` / `shorthand`（信息项）/ `missing`（真问题）；运行期目录（`test/_full_session_out`、`test/_kq_floor_tmp`、`_scratch/...`）逐条打印原因，不静默跳过。

**两次判据自身的修正**（都是先怀疑检查器，而不是先改文档）：① 44 条「README 引用了 §8.23–§8.44 但没有这个标题」全是假红——早期节用 `## 8.23`（h2）、后期用 `### 8.57`、子节用 `#### 8.22.1`，而判据只认 `^### (8\\.\\d+) `；② 「D 编号缺 [1,2,3,4,21]」也是假红——早期决策行不加粗、被撤回的用删除线。

**牙齿**：`--self-test` **5/5**；修完后 1172 项检查只剩 2 个真问题。**它在 D90 落纸后立刻抓到了自己的缺口**——D86 当时只落了进度行，决策行、§8.59、§9 第 70 项三处都漏了，被它报成「README §9 缺 70」「主计划 D 编号缺 86」。

**边界**：它检查的是「引用能不能落地」，不检查「落地物的内容对不对」；写得好不好、说得对不对仍要靠人读。

"""

README_ITEM70 = (
    "| 70 | ✅ **文档可追溯性检查器 T1–T5（D86，§8.59）** | "
    "`check_traceability.py`（零依赖、1172 项检查）抓住 README §9 断号与 D 编号断号；"
    "首跑 44 条假红靠「先怀疑判据」纠正（标题层级 + 加粗/删除线格式），`--self-test` 5/5 | "
    "`1_Code/DDM_Core/_scratch/check_traceability.py`（约 291 行） |\n"
)


def main():
    plan = PLAN.read_text(encoding="utf-8")
    if "| **D86** |" not in plan:
        lines = plan.split("\n")
        h = next(i for i, ln in enumerate(lines) if ln.startswith("| **D87** |"))
        lines.insert(h, D86_ROW)
        plan = "\n".join(lines)
        PLAN.write_text(plan, encoding="utf-8", newline="\n")
        print("plan: D86 行已插入")
    else:
        print("plan: D86 已存在")

    rd = README.read_text(encoding="utf-8")
    if "### 8.59" not in rd:
        lines = rd.split("\n")
        h = next(i for i, ln in enumerate(lines) if ln.startswith("### 8.60"))
        lines[h:h] = README_SECTION.rstrip("\n").split("\n") + [""]
        rd = "\n".join(lines)
        print("readme: §8.59 已插入")
    if "| 70 |" not in rd:
        lines = rd.split("\n")
        h = next(i for i, ln in enumerate(lines) if ln.startswith("| 71 |"))
        lines.insert(h, README_ITEM70.rstrip("\n"))
        rd = "\n".join(lines)
        print("readme: §9-70 已插入")
    README.write_text(rd, encoding="utf-8", newline="\n")

    ck = CHECKER.read_text(encoding="utf-8")
    if "exp_group1_subject1_keyflip.txt" not in ck:
        anchor = 'RUNTIME_WHITELIST = {'
        assert ck.count(anchor) == 1, "白名单锚点未命中"
        note = (
            'RUNTIME_WHITELIST = {\n'
            '    # 由 check_read_formal_data.py 运行时生成的负样例夹具（第 13 列 f↔j 互换），不入仓\n'
            '    "1_Code/Experiment/exp_matlab/exp_group1_subject1_keyflip.txt",\n'
        )
        ck = ck.replace(anchor + "\n", note, 1)
        CHECKER.write_text(ck, encoding="utf-8", newline="\n")
        print("checker: 白名单已补 keyflip 夹具")
    print("done")


if __name__ == "__main__":
    main()
