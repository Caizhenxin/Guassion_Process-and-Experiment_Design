# -*- coding: utf-8 -*-
"""把决策 D49 与 Stage 9 方案的行写进 `5_Reference/08_工作流/工作流_主计划.md`。

为什么用脚本而不是 `edit`：决策表 / 进度表的每一行都是数千字符的长行，
用 `edit` 追加必须一字不差匹配行尾（含可能的尾随空格）。脚本按**前缀**定位、
按**分隔符个数**断言列数，不依赖行尾形状。

三件必须做的事（都是前几次踩过的坑）：
1. 写回前先**摘掉附录表格末行之后的所有空行**，再连续插入——否则第 1 行插到
   空行前、第 2 行插到空行后，表格内部会多出一个空行（`check_table_integrity.py`
   会报 `split_rows = 1`）。
2. 写回后做**断表断言**：任何"空行的前后都是表格行"⇒ 拒绝写回。
3. **幂等守卫**：已存在 `| **D49** |` 就报错退出，不重复插入。

用法：
    python 1_Code/DDM_Core/_scratch/_apply_d49.py [--apply]
不给 `--apply` 时只做干跑（打印四处锚点与将插入的行）。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TARGET = Path("5_Reference/08_工作流/工作流_主计划.md")

# ---- 四处插入的锚点（前缀，唯一）与要插入的行 ------------------------------

ANCHORS = [
    # (锚点前缀, 插入位置 after, 该表的列数, 新行)
    (
        "| **D48** |",
        "after",
        5,
        "| **D49** | 2026-10-14 | ✅ **设计比较的「参数集口径」必须显式标注；Stage 9 "
        "Objective 用 D24 确证集 `C6`（6 参数），`design_fim.PRIMARY`（5 参数、含 "
        "`beta_ST`）不得单独用于可用性判定** | 同一份 `design_fim.py` 的实测 SE 表上"
        "**三套聚合共存且给出相反结论**：① `design_fim.PRIMARY` = {`d_ref`,`beta_T`,"
        "`tau_T`,`beta_S`,`beta_ST`} ⇒ D4 = **0.835「❌不可用」**；② D39 / Stage 4 = "
        "{`d_ref`,`beta_T`,`beta_S`,`beta_ST`}（**只做名次、不做可用性判定**）；③ 本方案 "
        "`C6` = {`d_ref`,`beta_T`,`beta_S`,`a_ref`,`delta_a`,`t0`} ⇒ D4 = **0.268「✅可用」**。"
        "根因：`beta_ST` 的相对 SE 是 4.1–5.8，独自把 `PRIMARY` 的几何平均抬过判定线 | "
        "**新文档** `5_Reference/08_工作流/Stage9_设计空间优化与论文整合方案.md`（310 行、"
        "68 表格行）；**新脚本** `1_Code/DDM_Core/_scratch/_c6_baseline.py`（按 `C6` 重新"
        "聚合 `design_fim` 的相对 SE 表）。**两条直接后果**：① **D4 在 `C6` 与 D39 两套"
        "口径下都是第 4 名** ⇒ D39「D4 在三个 ρ 下恒为第 4 名」获得一次独立交叉验证；"
        "② 但周边名次不稳 —— `T-wide` 第 1→第 6、`W-wide` 第 5→第 2、`D4-3T` 第 8→第 5 "
        "⇒ **只有「D4 是第 4 名」可以跨口径引用，其余名次必须带上参数集** |",
    ),
    (
        "| 2026-10-14 | **9**（时序口径桥 → D48） |",
        "after",
        5,
        "| 2026-10-14 | **9**（设计空间优化方案 → D49） | **把主计划里只有一行字的 "
        "Stage 9 展开成可执行方案，并在取证过程中抓到两条缺口与一处口径冲突**。① **新文档 "
        "`5_Reference/08_工作流/Stage9_设计空间优化与论文整合方案.md`**（12 节，体例照 "
        "Stage 8）：把 Stage 9 拆成 **9A 局部审计**（已知 D4 用已定稿设计，必须交付）与 "
        "**9B 全局优化**（重开一轮的推荐设计，方法学演示）；② **核心工程决定：内环不用 "
        "Stage 8 的完整拟合**（实测 420·N / 544·N 次众数搜索，小时级），改用**期望信息量**"
        "（`design_fim.design_se`，实测 0.08 s/评估，对照 Hessian 28.5 s）⇒ 正是 "
        "`AutoRA_SPE/README.md` §6 处方⑤「预计算充分统计量、内环退化为查表」的落地；"
        "③ **可行使域改坐标**：`W > T + 200 ms` 让 `(T, W)` 平面是梯形 ⇒ 换成 "
        "`(t, u) = (T, W − T − 0.2)` 后是矩形，且 `u` 就是程序 L22 的「真正可按键时长」；"
        "④ **冻结 Objective 三式**：(A) `C6` 相对 SE 的几何平均、(B) `rho` 的组层期望 "
        "t 值（事前登记 `μ_ρ = 0.6`、`σ_ρ = 0.25`，须报敏感性网格）、(C) 遗漏率事前登记带 "
        "`[0.05, 0.20]` 的二次罚 + (D) `cond`/`RT`/试次数的硬闸门；⑤ **四路消融与判据事前"
        "登记**：BO vs 随机 vs 网格 vs 人工补点，同预算 200 次，判据必须比 **`se_sd` 折算的 "
        "MC 噪声带**大，否则照实报「不可分辨」甚至「GP 不配」 | 新文档 "
        "`5_Reference/08_工作流/Stage9_设计空间优化与论文整合方案.md`；新脚本 "
        "`1_Code/DDM_Core/_scratch/_c6_baseline.py`；原始输出 "
        "`1_Code/DDM_Core/_scratch/design_fim_out.txt`（`design_fim.py` 全量实测，8 个有效"
        "设计、exit 0） | 🔨 **内环尚未动工**：`1_Code/AutoRA_SPE/stage9_inner.py`"
        "（含 **M-T1 分支**，内环现在的生成器只有 M-T3）、`stage9_objective.py`"
        "（`FROZEN` 字典 + `sha256` 哈希锁定）、`stage9_loop.py`（CRN 表 + 四路消融）、"
        "`check_stage9.py`。**第一件必须做的**：给内环补 M-T1 生成器（复用 "
        "`1_Code/DDM_Core/twophase.py::sample_step`），否则 Objective 的 (B) 判别项"
        "算不出来 |",
    ),
    (
        "| 2026-10-14 | **新增 D48：",
        "after",
        2,
        "| 2026-10-14 | **新增 D49：设计比较的「参数集口径」必须显式标注 —— 三套聚合"
        "共存且给出相反结论；Stage 9 用 D24 确证集 `C6`**。① 新建 "
        "`5_Reference/08_工作流/Stage9_设计空间优化与论文整合方案.md`（310 行、68 表格行、"
        "裸 LF、无 BOM，三判据扫描 `internal_breaks`/`mangled_rows`/`split_rows` 全 0）；"
        "② **同一份 SE 表上的三套聚合**：`1_Code/DDM_Core/design_fim.py::PRIMARY`"
        "（5 参数、含 `beta_ST`）⇒ D4 = 0.835「❌」；D39/Stage 4 的四参数集（只做名次）；"
        "D24 确证集 `C6` ⇒ D4 = 0.268「✅」—— **8 个设计里 7 个的绑定约束是 `delta_a`**；"
        "③ 新增 `1_Code/DDM_Core/_scratch/_c6_baseline.py` 落地这个重聚合，并跑出**交叉验证**："
        "D4 在 `C6` 与 D39 两套口径下**都是第 4 名**，但周边名次互换（`T-wide` 第 1→第 6、"
        "`W-wide` 第 5→第 2）；④ 记下 **Stage 9 内环的生成器只有 M-T3** 这个缺口"
        "（`design_fim.py` 第 281–282 行自述「因决策 D5，严格应换 M-T1 … M-T1 列为 "
        "Stage 4 待办」），而 Objective 的判别项恰恰需要 M-T1 ⇒ 内环必须先补该分支，"
        "补法是复用已有的 `1_Code/DDM_Core/twophase.py::sample_step`，**不新写仿真器** |",
    ),
    (
        "| `1_Code/AutoRA_SPE/README.md`（新增 §3.0；§7 文件清单补 2 行） |",
        "after",
        2,
        "| `5_Reference/08_工作流/Stage9_设计空间优化与论文整合方案.md`（**新建**，310 行 / "
        "68 表格行） + `1_Code/DDM_Core/_scratch/_c6_baseline.py`（**新建**） + "
        "`1_Code/DDM_Core/_scratch/design_fim_out.txt`（**新建**，`design_fim.py` 全量实测"
        "日志，exit 0） | **D49 的一手证据（设计比较的参数集口径）**。`_c6_baseline.py` 只做"
        "聚合、不重算 SE（SE 取自 `design_fim.py` 的实测「② 相对 SE」表），输出两套口径的"
        "逐设计几何平均与判定：`PRIMARY` D4 = 0.835「❌不可用」vs `C6` D4 = **0.268「✅可用」**，"
        "并给出**新口径排序** `D4-rep16(0.226) > W-wide(0.228) > W-low(0.253) > D4(0.268) > "
        "D4-3T(0.269) > W-high(0.290) > T-wide(0.292) > D4-rep8(0.321)`。同时实测记录 "
        "`design_fim.py` 的行为诊断（D4 遗漏 0.314 / 正确率 0.828 / RT 761 ms / cond 1.1e+05；"
        "W-wide 遗漏 0.400；W-low 遗漏 **0.476**）⇒ 把「`delta_a` 精度 vs 遗漏率是同一个旋钮」"
        "这个冲突写进 Stage 9 方案第 6 节 |",
    ),
]


def n_sep(line: str) -> int:
    """该行在 Markdown 表格意义上的分隔符个数（`\\|` 不算）。"""
    return line.count("|") - line.count("\\|")


def main() -> int:
    apply = "--apply" in sys.argv
    raw = TARGET.read_bytes()
    assert raw[:3] != b"\xef\xbb\xbf", "目标文件有 BOM"
    assert b"\r\n" not in raw, "目标文件不是裸 LF"
    text = raw.decode("utf-8")
    lines = text.split("\n")

    if any(l.startswith("| **D49** |") for l in lines):
        print("❌ 已存在 `| **D49** |` ⇒ 幂等守卫拒绝重复插入")
        return 1

    # ---- 1. 逐处定位并断言列数 ----
    plan = []
    for prefix, where, cols, newline in ANCHORS:
        hits = [i for i, l in enumerate(lines) if l.startswith(prefix)]
        if len(hits) != 1:
            print(f"❌ 锚点不唯一：{prefix!r} 命中 {len(hits)} 次")
            return 1
        i = hits[0]
        assert where == "after"
        got = n_sep(lines[i])
        want = cols + 1
        if got != want:
            print(f"❌ 锚点列数不符：{prefix!r} 实测 {got} 个分隔符，"
                  f"期望 {want}（{cols} 列）")
            return 1
        if n_sep(newline) != want:
            print(f"❌ 新行列数不符：期望 {want} 个分隔符，"
                  f"实测 {n_sep(newline)}")
            return 1
        plan.append((i, prefix, cols, newline))
        print(f"✅ 锚点 L{i+1}（{cols} 列 / {got} 分隔符）：{prefix!r}")

    # ---- 2. 摘除"末行之后的所有空行"（附录表在 EOF 前有空行）----
    #     只对最后一处（附录）做：把其后的空行收掉，再把新行连续插入。
    last_i = plan[-1][0]
    tail = lines[last_i + 1:]
    n_blank = 0
    while tail and tail[0].strip() == "":
        tail.pop(0)
        n_blank += 1
    if n_blank:
        print(f"ℹ️  附录末行之后有 {n_blank} 个空行 ⇒ 收掉后再插入（防断表）")
        lines = lines[:last_i + 1] + tail

    # ---- 3. 从后往前插入（避免行号漂移）----
    for i, prefix, cols, newline in sorted(plan, key=lambda p: -p[0]):
        print(f"   ↳ 在 L{i+1} 之后插入 1 行（{cols} 列）")
        lines.insert(i + 1, newline)

    # ---- 4. 断表断言：空行前后都是表格行 ⇒ 拒绝 ----
    def is_row(s: str) -> bool:
        return s.lstrip().startswith("|")

    for k, l in enumerate(lines):
        if l.strip() != "":
            continue
        prev = next((lines[j] for j in range(k - 1, -1, -1) if lines[j].strip()), None)
        nxt = next((lines[j] for j in range(k + 1, len(lines)) if lines[j].strip()), None)
        if prev is not None and nxt is not None and is_row(prev) and is_row(nxt):
            print(f"❌ 断表断言失败：L{k+1} 是空行，但其前后都是表格行")
            return 1

    # ---- 5. 写回（裸 LF，文件末尾保留单个换行）----
    if not lines or lines[-1] != "":
        lines.append("")
    out = "\n".join(lines).encode("utf-8")
    assert out[:3] != b"\xef\xbb\xbf"
    assert b"\r\n" not in out
    print(f"\n行数 {len(text.split(chr(10)))} → {len(lines)}；"
          f"字节 {len(raw)} → {len(out)}")
    if not apply:
        print("（干跑，未写回；加 --apply 才写）")
        return 0
    TARGET.write_bytes(out)
    print("✅ 已写回")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
