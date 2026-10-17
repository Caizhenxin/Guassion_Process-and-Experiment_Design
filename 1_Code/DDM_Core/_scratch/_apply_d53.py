# -*- coding: utf-8 -*-
"""把决策 D53 写进 `5_Reference/08_工作流/工作流_主计划.md`，并就地更正 D52 进度行里已过期的一小句。

体例照 `_apply_d47.py` … `_apply_d52.py`：**按前缀定位**（决策行是数千字符的单行，用
`edit` 追加必须一字不差匹配行尾）+ **断言分隔符个数** + **断表断言** + **幂等守卫**。
⚠️ 与 `_apply_d47`–`_apply_d51` 的差别：本轮**每个锚点只插一行**，所以**绝不触碰空行**
（"摘除锚点之后所有空行再插入"是为一次连续追加多行设计的，D52 就因照抄它而吃掉了 3 处空行
与文件末尾换行）。

用法：
    python 1_Code/DDM_Core/_scratch/_apply_d53.py            # 干跑
    python 1_Code/DDM_Core/_scratch/_apply_d53.py --apply    # 写回
"""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

P = Path("5_Reference/08_工作流/工作流_主计划.md")

# ---------------------------------------------------------------- 1. 就地更正
STALE = ("**(4)** Stage 9 剩余文件 `stage9_loop.py` / `check_stage9.py` / `stage9_report.md`")
FIXED = ("**(4)** Stage 9 剩余文件 ~~`stage9_loop.py` /~~ `check_stage9.py` / `stage9_report.md`"
         "（`stage9_loop.py` 已于 **D53** 交付，见下）")

# ---------------------------------------------------------------- 2. 四处插入
DEC_PREFIX = "| **D52** |"
DEC_ROW = (
    "| **D53** | 2026-10-14 | ✅ **Stage 9 的优化循环已交付；同时实测出一条会改变结论口径的事实："
    "内环的 MC 噪声可能大于设计之间的差异**。① 循环**必须用 M-T1**（冻结 Objective 的 (B) 项只在 "
    "M-T1 下有定义，`rho` 取冻结值 `FROZEN[\"rho_mu\"] = 0.6`，传 M-T3 一律 `ValueError`）；"
    "② **CRN 种子必须由设计内容导出**（本条用设计名字的 `sha256` 前 12 位），**不得由候选表下标导出**"
    "—— 否则候选表一被过滤/截断/重排，同一设计就静默换了种子，CRN 名存实亡；"
    "③ **四路消融必须同预算**（不同预算下的「最好臂」没有意义），且臂间差异**必须大于噪声带**"
    "才允许宣称最好，否则照实报「不可分辨」；④ **单位只在一处换算**（`levels_sec()`）"
    "—— 毫秒与秒在同一套代码里混用**不报错**，只静默给出垃圾。 | "
    "新建 `1_Code/AutoRA_SPE/stage9_loop.py`（617 行）与 `1_Code/AutoRA_SPE/check_stage9_loop.py`"
    "（261 行，A–G 七组，**21/21 通过、exit 0、67.2 s**）。候选空间枚举实测 **174 个可行设计 / "
    "186 个被 C3 否决（C1 一个都没否决）**；`run_arms` 的同预算断言有牙齿（D2b 人为让一臂超支 ⇒ "
    "确实抛 `RuntimeError`）；CRN 实测：完整表（下标 0）与截断表（下标 20）里同一设计种子与读数"
    "**逐位相同**，174 个设计 → 174 个不同种子。冒烟（budget 12、`n_fim=1`、`rho = 0.6`，40 次评估 / "
    "182 s）四臂 best J = `grid 0.4673 < manual 0.5112 < random 0.5405 < bo 0.6382` ⇒ "
    "**该预算下 BO 没赢过空间填充网格**。**`n_fim=1` 时把锚点在不同种子下重算两次得 "
    "`J = 9.5112 / 13.6474` ⇒ `sd_J = 2.92`，大于臂间差异 0.47–0.64**；B2 实测「毫秒当秒」"
    "Δ遗漏 = 0.361、`cond` 8.91e15 vs 5.4e4（**不报错**）。 | "
    "① 新增 `1_Code/AutoRA_SPE/stage9_loop.py`、`1_Code/AutoRA_SPE/check_stage9_loop.py`；"
    "② `5_Reference/08_工作流/Stage9_设计空间优化与论文整合方案.md` 四处（§9 工具表 `stage9_loop.py` "
    "🔨 → ✅ 并新增 `check_stage9_loop.py` 行；§5.3.1 第 (3) 件 🔨 → ✅；§11 **新增第 12–15 条**；"
    "§12 加行）；③ `1_Code/DDM_Core/README.md` §9 **第 34 项**；④ `1_Code/AutoRA_SPE/README.md` §7 "
    "文件清单补 5 行；⑤ **进论文的四路消融必须先提高 `n_fim`、`--noise-repeats ≥ 5`，并重复整个消融"
    "（R 个种子组）**才能得到配对误差棒；⑥ **「Objective 没有会话总时长成本项」必须与任何把 W 推向"
    "池上限的推荐一起报**，不得只报 J 最小者。 |"
)

PROG_PREFIX = "| 2026-10-14 | **8/9**（N=4 干跑判读 → D52）"
PROG_ROW = (
    "| 2026-10-14 | **9**（优化循环交付 → D53） | "
    "**把 Stage 9 从「有内环仪器」推进到「有完整优化循环」，并在交付时抓到两处自己的缺陷与一条"
    "会改变结论口径的实测**。① **候选空间定形**：`T_POOL_MS`（2/5/9/15/21/27 帧）× `W_POOL_MS`"
    "（48/72/108/144 帧）× `n_rep ∈ {8,12,16,18,24}`，受 `len(T)·len(W)·n_rep = 576/4 = 144` 与"
    "程序自检 C3（`W − T − 200 ms ≥ 300 ms`）双约束 ⇒ **174 个可行设计、186 个被 C3 否决**；"
    "② **CRN 与消融纪律**：种子由设计内容导出、四臂同预算（有守卫）、差异必须大于噪声带；"
    "③ ❗ **交付时改掉两处自己的缺陷**：`arm_grid` 原取「候选表前 N 个」而候选表按字典序排 ⇒ "
    "前 6 个全是 `r24` / `T` 最短 / `W` 最短的**不可行角落**（把有偏角落样本冒充网格）；"
    "`inner_eval` 收**秒**而候选表存**毫秒** ⇒ 首跑把毫秒当秒喂进去，**不报错**、只是静默给出"
    "`omission = 0.0` / `cond = 3.96e+17` / `relative_se` 量级 10⁴，直到冻结 Objective 三道闸门"
    "**全部拒绝**才暴露；④ **锚点 D4 被 `T[33.33/83.33/249.98]ms × W[799.98/1199.90/2399.80]ms × r16` "
    "在 (A,B) 两维上同时支配** ⇒ 「D4 不是 Pareto 最优」与遗漏率罚分无关；"
    "⑤ ❗ **`n_fim=1` 的内环 MC 噪声（`sd_J = 2.92`）大于设计之间的差异（0.47–0.64）** ⇒ "
    "该配置下的臂间比较不可解释，消融必须换到更大的 `n_fim` 且重复种子组。 | "
    "`1_Code/AutoRA_SPE/stage9_loop.py`（新建，617 行）；`1_Code/AutoRA_SPE/check_stage9_loop.py`"
    "（新建，261 行，**21/21、exit 0**）；日志 `1_Code/AutoRA_SPE/_scratch_check_stage9_loop_u8.txt`、"
    "`1_Code/AutoRA_SPE/_scratch_stage9_loop_smoke12_u8.txt`；`1_Code/DDM_Core/README.md` §9 第 34 项；"
    "`5_Reference/08_工作流/Stage9_设计空间优化与论文整合方案.md` §9 / §5.3.1 / §11 / §12 | "
    "🔨 **仍开放**：**(1)** 把 `n_fim` 提到使 `2·sd_J` 小于设计差异，`--noise-repeats ≥ 5`；"
    "**(2)** 重复整个消融（R 个种子组）以得到配对误差棒 —— 在那之前不得宣称「BO 优于随机/网格」；"
    "**(3)** 是否给冻结 Objective 补一条「会话总时长」成本项（补则须重新冻结哈希，不能事后加权）；"
    "**(4)** Stage 9 剩余文件 `check_stage9.py` / `stage9_report.md` |"
)

LOG_PREFIX = "| 2026-10-14 | **新增 D52：LOO 可用性必须同时看"
LOG_ROW = (
    "| 2026-10-14 | **新增 D53：Stage 9 的优化循环已交付；CRN 种子由设计内容导出、四臂必须同预算、"
    "臂间差异必须大于噪声带；并实测出 `n_fim=1` 的 MC 噪声大于设计差异**。① 新建 "
    "`1_Code/AutoRA_SPE/stage9_loop.py`（617 行）与 `1_Code/AutoRA_SPE/check_stage9_loop.py`"
    "（261 行，**21/21、exit 0、67.2 s**）；② **候选空间实测 174 可行 / 186 被 C3 否决**；"
    "③ 交付时改掉两处自己的缺陷（`arm_grid` 取「候选表前 N 个」其实是有偏角落样本；"
    "`inner_eval` 收秒而候选表存毫秒 ⇒ 首跑静默给出垃圾，闸门全部拒绝才发现）；"
    "④ 冒烟四臂 best J = `grid 0.4673 < manual 0.5112 < random 0.5405 < bo 0.6382`；"
    "⑤ **锚点 D4 被 `T[33.33/83.33/249.98]ms × W[799.98/1199.90/2399.80]ms × r16` 在 (A,B) 两维上"
    "同时支配** ⇒ 与遗漏率罚分无关；⑥ **`n_fim=1` 的 `sd_J = 2.92` 大于设计差异 0.47–0.64** ⇒ "
    "该配置下臂间比较不可解释 |"
)

APP_PREFIX = "| `1_Code/DDM_Core/stage8_run.py`（修改：`render_group` 的判据）"
APP_ROW = (
    "| `1_Code/AutoRA_SPE/stage9_loop.py`（**新建**，617 行） + "
    "`1_Code/AutoRA_SPE/check_stage9_loop.py`（**新建**，261 行，**21/21、exit 0**） | "
    "**D53**：Stage 9 优化循环（174 个可行设计的有限候选集 + 按需 CRN 缓存 + 四路消融 + Pareto 前沿）；"
    "CRN 种子由设计内容导出；四臂同预算有守卫；实测 `n_fim=1` 的 `sd_J = 2.92` 大于设计差异 ⇒ "
    "消融须换更大 `n_fim` 并重复种子组 |"
)


def n_sep(line: str) -> int:
    """表格行的列分隔符数（不把 `\\|` 转义算进去）。"""
    return line.count("|") - line.count("\\|")


def main() -> int:
    apply = "--apply" in sys.argv
    text = P.read_text(encoding="utf-8")
    if not text.endswith("\n"):
        print("❌ 输入文件不以换行结尾，拒绝写回")
        return 2
    if "| **D53** |" in text:
        print("❌ 已存在 `| **D53** |`，本脚本已跑过（幂等守卫）")
        return 2
    lines = text[:-1].split("\n")
    print(f"读入 {P}：{len(lines)} 行")

    # ---- 就地更正 D52 进度行里已过期的一小句
    hits = [i for i, s in enumerate(lines) if STALE in s]
    if len(hits) != 1:
        print(f"❌ 待更正的句子命中 {len(hits)} 次（期望 1 次），拒绝写回")
        return 2
    i = hits[0]
    if n_sep(lines[i]) != n_sep(lines[i].replace(STALE, FIXED)):
        print("❌ 更正前后分隔符数变化，拒绝写回")
        return 2
    lines[i] = lines[i].replace(STALE, FIXED)
    print(f"✅ 就地更正：L{i + 1}（分隔符数不变）")

    # ---- 四处插入
    for prefix, row, cols in ((DEC_PREFIX, DEC_ROW, 5),
                              (PROG_PREFIX, PROG_ROW, 5),
                              (LOG_PREFIX, LOG_ROW, 2),
                              (APP_PREFIX, APP_ROW, 2)):
        hits = [i for i, s in enumerate(lines) if s.startswith(prefix)]
        if len(hits) != 1:
            print(f"❌ 锚点 {prefix!r} 命中 {len(hits)} 次（期望 1 次），拒绝写回")
            return 2
        i = hits[0]
        want = cols + 1
        if n_sep(lines[i]) != want or n_sep(row) != want:
            print(f"❌ 分隔符数不一致：锚点 L{i + 1} 有 {n_sep(lines[i])}、"
                  f"新行有 {n_sep(row)}、期望 {want}，拒绝写回")
            return 2
        lines.insert(i + 1, row)
        if lines[i + 1] != row:
            print("❌ 插入后断言失败")
            return 2
        print(f"✅ 插入 {cols} 列行：L{i + 2}（锚点 {prefix[:28]}…）")

    # ---- 断表断言：任何紧邻两行里不得出现"空行夹在两条表格行之间"的新情况
    for i in range(1, len(lines) - 1):
        if not lines[i].strip():
            if (lines[i - 1].lstrip().startswith("|") and n_sep(lines[i - 1]) >= 2
                    and lines[i + 1].lstrip().startswith("|") and n_sep(lines[i + 1]) >= 2):
                print(f"❌ 断表：L{i + 1} 是空行而两侧都是表格行，拒绝写回")
                return 2

    out = "\n".join(lines) + "\n"
    if apply:
        P.write_text(out, encoding="utf-8", newline="\n")
        print(f"✍️ 已写回：{P}（{len(lines)} 行）")
    else:
        print(f"（干跑）将写回 {P}（{len(lines)} 行）—— 加 --apply 才落盘")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
