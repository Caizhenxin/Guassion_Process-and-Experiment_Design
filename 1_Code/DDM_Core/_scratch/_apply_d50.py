# -*- coding: utf-8 -*-
"""把决策 D50（Stage 9 内环仪器提升）写进 `5_Reference/08_工作流/工作流_主计划.md`。

为什么用脚本而不是 `edit`：决策表 / 进度表的每一行都是数千字符的长行，
用 `edit` 追加必须一字不差匹配行尾（含可能的尾随空格）。脚本按**前缀**定位、
按**分隔符个数**断言列数，不依赖行尾形状。

与 `_apply_d47.py` / `_apply_d48.py` / `_apply_d49.py` 同体例，四件必须做的事：
1. 写回前先**摘掉附录表格末行之后的所有空行**，再连续插入——否则第 1 行插到
   空行前、第 2 行插到空行后，表格内部会多出一个空行（`check_table_integrity.py`
   会报 `split_rows = 1`）。
2. 写回后做**断表断言**：任何"空行的前后都是表格行"⇒ 拒绝写回。
3. **幂等守卫**：已存在 `| **D50** |` 就报错退出，不重复插入。
4. **就地更正 D49 进度行里那句已被证伪的话**（"第一件必须做的：给内环补 M-T1
   生成器（复用 `twophase.py::sample_step`）"）。这一处不是追加而是**替换**，
   用 `~~删除线~~` 保留原文以便追溯——本项目吃过"过时断言留在文档里被继续引用"
   的亏（`5_Reference/AGENTS.md` §六）。

用法：
    python 1_Code/DDM_Core/_scratch/_apply_d50.py [--apply]
不给 `--apply` 时只做干跑（打印四处锚点、将插入的行、以及就地更正的前后对照）。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TARGET = Path("5_Reference/08_工作流/工作流_主计划.md")

# ---- 就地更正：D49 进度行里那句已被证伪的话 --------------------------------
STALE = ("**第一件必须做的**：给内环补 M-T1 生成器（复用 "
         "`1_Code/DDM_Core/twophase.py::sample_step`），否则 Objective 的 "
         "(B) 判别项算不出来")
FIXED = ("~~**第一件必须做的**：给内环补 M-T1 生成器（复用 "
         "`1_Code/DDM_Core/twophase.py::sample_step`）~~ —— ❌ **2026-10-14 "
         "更正（见 D50）**：M-T1 仪器**早已存在**于 "
         "`1_Code/DDM_Core/_scratch/check_mt1_fim.py`，且用的是 "
         "`twophase.simulate_euler_subject`（**6 s/被试**）而不是 "
         "`sample_step`（70 s/被试）；该件真正剩下的动作是**提升为生产文件**"
         "`1_Code/AutoRA_SPE/stage9_inner.py`（已完成，自检 26/26、exit 0）")

# ---- 四处插入的锚点（前缀，唯一）与要插入的行 ------------------------------

ANCHORS = [
    # (锚点前缀, 插入位置 after, 该表的列数, 新行)
    (
        "| **D49** |",
        "after",
        5,
        "| **D50** | 2026-10-14 | ✅ **Stage 9 内环的仪器不重写、直接提升；生产版必须"
        "比原型更严；引用绝对 SE 必须写明生成模型** | 主计划 D49 的进度行写着"
        "「第一件必须做的：给内环补 M-T1 生成器（复用 "
        "`1_Code/DDM_Core/twophase.py::sample_step`）」——**这句被取证证伪**："
        "`1_Code/DDM_Core/_scratch/check_mt1_fim.py`（434 行）**早已**实现 M-T1 内环"
        "仪器并自检通过（自检 A = 8.795e-08、自检 B 相对差 0.000%），且它用的是 "
        "`twophase.simulate_euler_subject`（**6 s/被试**）而不是 `sample_step`"
        "（**70 s/被试**）。提升过程中抓到**两处原型真缺陷**：① `rho` 的越界守卫"
        "**只挡下界**——实测 `per_trial_loglik_step` 在 `rho = 3.003 / 3.01 / 5.0` "
        "处**全部返回有限值**，只有 `rho = -0.003` 返回 `None`，因此上界越界会被"
        "**静默算成一个数**；② 批次向量化路径把**平铺后**的设计传给行为诊断 ⇒ "
        "`is_match` 长度与模拟结果不符 | **新文件** `1_Code/AutoRA_SPE/"
        "stage9_inner.py`（551 行、裸 LF，M-T3/M-T1 双分支 + CRN 表 + 批次向量化）"
        "与 `1_Code/AutoRA_SPE/check_stage9_inner.py`（460 行、裸 LF，A–F 六组，"
        "**两档都 26/26、exit 0**）。**三条后果**：① M-T3 分支对 "
        "`design_fim.design_se` 逐位复现、M-T1 分支对 `check_mt1_fim.py::"
        "design_se_step` 逐位复现（均 **0.000e+00**，判据 <1e-12）⇒ 内环的两条"
        "分支都钉在已验证的实现上；② 批次向量化的加速比**实测只有 1.32×"
        "（n_fim=2）/ 1.26×（n_fim=4）**，不是原估的 4×（OPG 有限差分摊薄不掉）；"
        "③ 「M-T1 下 SE 约为 M-T3 的 **1.7–2.5 倍**」⇒ **凡在 M-T3 下报出的绝对 "
        "SE、以及由它推出的样本量结论，乐观约 2 倍**，引用必须写明生成模型 |",
    ),
    (
        "| 2026-10-14 | **9**（设计空间优化方案 → D49） |",
        "after",
        5,
        "| 2026-10-14 | **9**（内环仪器提升 → D50） | **把 Stage 9 内环从"
        "「方案里的一个文件名」变成可运行、自证过的生产文件**。① 取证发现"
        "**方案 v1 把已完成写成规划**（镜像版 `5_Reference/AGENTS.md` §六，见 "
        "`5_Reference/08_工作流/Stage9_设计空间优化与论文整合方案.md` §5.3.1）："
        "M-T1 内环仪器早已存在于 `1_Code/DDM_Core/_scratch/check_mt1_fim.py`；"
        "② 新建 `1_Code/AutoRA_SPE/stage9_inner.py`，对外只暴露 "
        "`inner_eval` / `build_table` / `save_table` / `load_table` / "
        "`geomean_relative_se` 五个入口，模型名 `M-T3`/`M-T1` 与 "
        "`1_Code/DDM_Core/stage8_run.py::MODELS` 一致；③ 新建 "
        "`1_Code/AutoRA_SPE/check_stage9_inner.py`，A–F 六组。**判据全部来自"
        "实测的抽样分布**：C1 用两支各自的 `se_sd` 折算出差值标准误再判 "
        "`\\|z\\| <= 4`；C3 用合并 MC 标准误当尺子 | 新文件 "
        "`1_Code/AutoRA_SPE/stage9_inner.py`、`1_Code/AutoRA_SPE/"
        "check_stage9_inner.py`；日志 `1_Code/AutoRA_SPE/"
        "_scratch_check_stage9_inner_u8.txt`（n_fim=2，73.9 s）与 "
        "`1_Code/AutoRA_SPE/_scratch_check_stage9_inner_n4_u8.txt`"
        "（n_fim=4，118.3 s） | 🔨 **内环还剩两件**：**(1)** "
        "`stage9_objective.py`（冻结 Objective + `FROZEN` 字典 + `sha256` 哈希锁"
        "定 + `assert_frozen()`）；**(2)** `stage9_loop.py`（按 §5.4 的 CRN 把 "
        "`design × truth × rep` 铺成预计算表 + 四路消融 + Pareto 前沿）。"
        "存/取设施已在 `stage9_inner.build_table`/`save_table`/`load_table` 里"
        "通过往返自测，但**还没按真正的设计网格铺开**。另有一条**未查清的观察**"
        "（方案 §9 末）：4 人 analytic 干跑在 M-T1 拟合一开始出现 scipy "
        "`_numdiff` 的 `invalid value encountered in subtract` ⇒ **目标函数"
        "在某个扰动点上返回了非有限值**，待复现定位 |",
    ),
    (
        "| 2026-10-14 | **新增 D49：",
        "after",
        2,
        "| 2026-10-14 | **新增 D50：Stage 9 内环的仪器不重写、直接提升；生产版必须"
        "比原型更严；引用绝对 SE 必须写明生成模型**。① 主计划 D49 进度行里那句"
        "「第一件必须做的：给内环补 M-T1 生成器（复用 `twophase.py::sample_step`）」"
        "**已被证伪并就地标删**（用 `~~…~~` 保留原文以便追溯）；② 新建 "
        "`1_Code/AutoRA_SPE/stage9_inner.py`（551 行、裸 LF）——`inner_eval` 一次"
        "调用给出 `se` / `se_rho` / `se_sd` / `corr` / `cond` / 遗漏率 / 正确率 / "
        "RT，并通过 `geomean_relative_se(res, focus=C6)` 直接喂 Objective (A)；"
        "③ 新建 `1_Code/AutoRA_SPE/check_stage9_inner.py`（460 行、裸 LF），"
        "**n_fim=2 与 n_fim=4 两档都 26/26 通过、exit 0**；④ 提升时抓到两处原型"
        "真缺陷（`rho` 守卫只挡下界；批次路径的 `is_match` 形状），并把自己写的"
        "**第 4 次同族错误**（「两分支应当一致」却混用了 10 参数与 9 参数口径、"
        "还各自只跑 1 次）写进方案 §9 的第 3 条硬规矩 |",
    ),
    (
        "| `5_Reference/08_工作流/Stage9_设计空间优化与论文整合方案.md`"
        "（**新建**，310 行 /",
        "after",
        2,
        "| `1_Code/AutoRA_SPE/stage9_inner.py`（**新建**，551 行 / 裸 LF） + "
        "`1_Code/AutoRA_SPE/check_stage9_inner.py`（**新建**，460 行 / 裸 LF） + "
        "`1_Code/AutoRA_SPE/_scratch_check_stage9_inner_u8.txt`（**新建**，自检日志，"
        "exit 0） + `1_Code/AutoRA_SPE/_scratch_check_stage9_inner_n4_u8.txt`"
        "（**新建**，n_fim=4 档，exit 0） | **D50 的一手证据（Stage 9 内环仪器"
        "提升）**。`check_stage9_inner.py` 把两条分支都钉在已验证的实现上："
        "**B1** M-T3 分支 vs `design_fim.design_se`（同 seed）`max 相对差 = "
        "0.000e+00`（判据 <1e-12）；**B2** M-T1 分支（`batch=False`）vs "
        "`_scratch/check_mt1_fim.py::design_se_step` 参数与 `rho` 均 "
        "`0.000e+00`（判据 <1e-12）；**B3** `rho = 1` 时在**同一份试次**上 "
        "M-T1（rho 固定）与 M-T3 差 `0.000%`（归一化逐试次对数似然最大绝对差 "
        "9.260e-07）。**B4（报告项，不是错误）**：把 `rho` 当自由参数会让 "
        "`d_ref` 的边际 SE **+116.8%**、其余 8 个参数只涨 0–8.1% ⇒ 与 M-T3 做"
        "实现比对时**必须** `include_rho=False`。**C1** 批次 vs 逐份最大 "
        "`\\|z\\| = 3.86`（n_fim=2）/ `2.79`（n_fim=4），加速比 **1.32× / 1.26×**；"
        "**C3** `rho = 1` 下 Euler+step 路径与解析路径同分布，最大 "
        "`\\|z\\| = 2.34 @ beta_S`（两支各 4 份）。**D** CRN 规则 `seed + 1000·k` "
        "被钉住；**E** `.npz` 往返后 `se` 逐位不变；**F** D49 回归钉：同一份 SE 上 "
        "`g_pri = 0.850` 判「❌不可用」而 `g_c6 = 0.270` 判「✅可用」 |",
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

    if any(l.startswith("| **D50** |") for l in lines):
        print("❌ 已存在 `| **D50** |` ⇒ 幂等守卫拒绝重复插入")
        return 1

    # ---- 0. 就地更正 D49 进度行里那句已被证伪的话 ----
    hit = [i for i, l in enumerate(lines) if STALE in l]
    if len(hit) != 1:
        print(f"❌ 待更正句命中 {len(hit)} 次（应为 1 次）：{STALE[:40]!r}…")
        return 1
    i_fix = hit[0]
    before = lines[i_fix]
    lines[i_fix] = before.replace(STALE, FIXED)
    if n_sep(lines[i_fix]) != n_sep(before):
        print(f"❌ 就地更正改变了分隔符个数：{n_sep(before)} → "
              f"{n_sep(lines[i_fix])}")
        return 1
    print(f"✅ 就地更正 L{i_fix+1}（D49 进度行的「第一件必须做的」标删）")

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
