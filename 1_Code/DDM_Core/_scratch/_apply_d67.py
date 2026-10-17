# -*- coding: utf-8 -*-
"""D67 落纸脚本：Stage 1 验收的机器判据 + 合成生成器的一处「与 MATLAB 程序不符」缺陷。

为什么要有这个脚本而不是手改：
  1. 四份文档要同时改 6 处（主计划 4 + Stage1 2 + DDM README 2），手改必然漏一处；
  2. 表格行有列数/竖线数要求，手改会把表写歪（`check_table_integrity.py` 当场报错）；
  3. 幂等：重复跑不会插出两行 —— 每一处插入前先查「守卫文本」是否已在文件里。

用法：
    python -X utf8 -u _apply_d67.py            # 干跑（只打印，不写盘）
    python -X utf8 -u _apply_d67.py --apply    # 真改
"""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
PLAN = ROOT / "5_Reference/08_工作流/工作流_主计划.md"
STAGE1 = ROOT / "5_Reference/08_工作流/Stage1_技术验证记录.md"
DDM = ROOT / "1_Code/DDM_Core/README.md"

APPLY = "--apply" in sys.argv


# --------------------------------------------------------------------------
# 基础设施：读、写、按内容定位、插行
# --------------------------------------------------------------------------
def load(p: Path) -> list[str]:
    return p.read_text(encoding="utf-8").split("\n")


def save(p: Path, lines: list[str], st: dict) -> None:
    if not APPLY:
        st["dry"] += 1
        return
    p.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    st["written"] += 1


def n_sep(line: str) -> int:
    """表格行的竖线数（=| 分隔的列数 + 1）。"""
    return line.count("|")


def idx_of(lines: list[str], prefix: str, start: int = 0) -> int:
    for i in range(start, len(lines)):
        if lines[i].startswith(prefix):
            return i
    return -1


def ins_after(lines: list[str], anchor_prefix: str, new: list[str],
              st: dict, tag: str, at: int = 0) -> None:
    i = idx_of(lines, anchor_prefix, at)
    if i < 0:
        raise SystemExit(f"[{tag}] 找不到锚点：{anchor_prefix!r}")
    # 幂等：新行的第一行已经在文件里，就不再插
    if new and new[0] in lines:
        print(f"  [{tag}] 已在，跳过")
        return
    n_anchor = n_sep(lines[i])
    for k, row in enumerate(new):
        if row.startswith("|") and n_sep(row) != n_anchor:
            raise SystemExit(
                f"[{tag}] 第 {k + 1} 行竖线数 {n_sep(row)} != 锚点 {n_anchor}")
    lines[i + 1:i + 1] = new
    st["edits"] += 1
    print(f"  [{tag}] 插在 L{i + 1} 之后，{len(new)} 行")


def patch_row(lines: list[str], prefix: str, old: str, new: str,
              st: dict, tag: str, at: int = 0) -> None:
    """把以 `prefix` 开头的那一行里的 `old` 子串替换成 `new`（必须恰好一处）。"""
    i = idx_of(lines, prefix, at)
    if i < 0:
        raise SystemExit(f"[{tag}] 找不到锚点：{prefix!r}")
    if new in lines[i]:
        print(f"  [{tag}] 已是新文，跳过")
        return
    if lines[i].count(old) != 1:
        raise SystemExit(f"[{tag}] L{i + 1} 里 {old!r} 出现 {lines[i].count(old)} 次")
    lines[i] = lines[i].replace(old, new)
    st["edits"] += 1
    print(f"  [{tag}] L{i + 1} 已改")


# --------------------------------------------------------------------------
# 一、主计划：决策行 / 进度行 / 变更日志 / 附录证据
# --------------------------------------------------------------------------
D67_ROW = (
    "| **D67** | 2026-10-17 | ✅ **Stage 1 的验收从「手工回填四张表」变成「一条命令给出 6-A–6-E 的机器判据」，"
    "并顺带抓出合成生成器一处「与 MATLAB 程序不符」的缺陷**。① 缺口：`Stage1_技术验证记录.md` §6 的四张表全空，"
    "而 6-C（实际 T 与名义 T 的差 < 1 帧）与 6-D（输出列与缺失值）的判据**全部机械可判**，"
    "人工在实验机上手算 `stimulus_frames` 期望值（2 / 5 / 9 / 15）必错。② 新建 `1_Code/Experiment/exp_Check/check_stage1_acceptance.py`"
    "（**408 行**，零依赖，复用 `read_formal_data.read_one` 的列名口径）："
    "6-A 掩蔽纹理预加载（靠命令行回显文本）、6-B `KbQueue` 能记录刺激期按键（要求指定 T 档至少 1 例 `Response != NA` 且 `RT < T`，"
    "并把最紧余量 `T − max(RT)` 印出来供人判「边缘还是真快」）、6-C 帧量化（`stimulus_frames` 期望由 `_frames(t, fi)` 现算、"
    "`|stimulus_dur_actual − T| < FlipIntv`、`stimulus_offset_actual == mask_onset_actual`）、"
    "6-D 五条（25 列名逐字比对 / `NA` 约定：`Response=NA` 时 `RT`、`Correct` 必须 NaN 且 `timeout=1`、`responded_by_deadline=0`，"
    "反之必须有限 0-1 / `block` 编号 / 按字节搜 `0x00` / `timestamp` 列只做存在性检查）、6-E 按钮延时可比性（**不可机器判**，只能手测）。"
    "③ **不假装覆盖**：`6-A` 与 `6-E` 明确标为「需手测 2 项」，检查器不把它们算进 6 项判据的通过率。"
    "④ **自测 5/5**：干净数据（`make_fake_pilot.py` 现生成）通过；`--defect-1f` 拦住 6-C；`--defect-mismatch` 拦住 6-D；"
    "`Response=NA 但 RT 有值` 拦住 6-D；注入 `0x00` 字节拦住 6-D。"
    "⑤ **顺带修掉的生成器缺陷**：`1_Code/DDM_Core/_scratch/make_fake_pilot.py` 的练习行原本把 `Correct` 写成 `0`，"
    "而 `Exp_Design_Formal.m` 在练习行（`isPractice`）写 **NaN** ⇒ 生成器自己造了一行**不合规**的数据，"
    "于是「干净数据应当通过」这一例失败。已改为 `None if rt is None else ...`（练习行恒为 NaN）。"
    "**这条缺陷只在「用生成器去验检查器」时才现形** —— 拿真实文件是被试数据，练习行的 `Correct` 是程序写的 NaN，碰不到。"
    "⑥ 尚未做：真实文件未在手（需用户实机跑完 N=2–3）；`6-A`/`6-E` 两项仍必须人执行。 |"
)

D67_PROG = (
    "| 2026-10-17 | **1**（验收的机器判据 → D67） | **把「Stage 1 算不算完成」从「四张空表手工回填」变成「一条命令给判据」**。"
    "新建 `1_Code/Experiment/exp_Check/check_stage1_acceptance.py`（408 行）：6-A–6-D 全部机器可判，6-A/6-E 如实标为需手测；"
    "自测 5 例（干净 / 帧量化缺陷 / 响应矛盾 / `NA` 约定 / `0x00` 字节）**5/5**；"
    "顺带修掉 `make_fake_pilot.py` 练习行 `Correct` 应为 NaN 的缺陷。 | "
    "`1_Code/Experiment/exp_Check/check_stage1_acceptance.py` + `1_Code/DDM_Core/_scratch/make_fake_pilot.py` | "
    "用户在实验机跑 N=2–3 并回填（只剩 6-A/6-E 两行要人判） |"
)

D67_LOG = (
    "| 2026-10-17 | **新增 D67：Stage 1 验收的机器判据（`check_stage1_acceptance.py`，408 行）+ 合成生成器练习行 `Correct` 应为 NaN 的缺陷修复**。"
    "① 缺口：`Stage1` §6 四张表全空，而 6-C/6-D 的判据机械可判，手算 `stimulus_frames` 必错。"
    "② 检查器覆盖 6-A–6-D（6-A/6-E 标为需手测 2 项），`6-C` 的期望帧数由 `_frames(t, fi)` 现算而不是写死。"
    "③ 6-D 五条含「`Response=NA` ⇒ `RT`、`Correct` 必须 NaN」与「按字节搜 `0x00`」。"
    "④ 自测 5/5：干净数据过、`--defect-1f` 拦 6-C、`--defect-mismatch` 拦 6-D、`NA` 带 RT 拦 6-D、`0x00` 拦 6-D。"
    "⑤ 缺陷：`make_fake_pilot.py` 练习行写 `Correct = 0`，而 `Exp_Design_Formal.m` 写 NaN ⇒ 改为 NaN。"
    "⑥ 交叉确认未破别人：`check_read_formal_data.py` 仍 **30/30**、`check_qc_group.py` 仍 **10/10**。"
    "⑦ 文档：`Stage1` §6 加「先跑这条命令」的指引、§7 第 5 条改写（缺口从「四张表」缩到「6-A/6-E 两行」）；"
    "`1_Code/DDM_Core/README.md` 新增 §8.42 与 §9 第 51 项。 |"
)

D67_APPENDIX = (
    "| `1_Code/Experiment/exp_Check/check_stage1_acceptance.py`（**新建**，408 行，零依赖）+ "
    "`1_Code/DDM_Core/_scratch/make_fake_pilot.py`（练习行 `Correct` 改 NaN） | "
    "6-A–6-D 机器判据、6-A/6-E 标为需手测；自测 **5/5**（干净 / `--defect-1f` / `--defect-mismatch` / "
    "`NA` 带 RT / `0x00` 字节）；6-C 期望帧数由 `_frames(t, fi)` 现算；6-D 按字节搜 `0x00`；"
    "生成器练习行 `Correct` 由 `0` 改 NaN（与 `Exp_Design_Formal.m` 一致） |"
)


def do_master_plan(st: dict) -> None:
    lines = load(PLAN)
    ins_after(lines, "| **D66** |", [D67_ROW], st, "主计划 §5 D67")
    ins_after(lines, "| 2026-10-17 | **8**（输入契约 → D66）", [D67_PROG], st, "主计划 §6")
    ins_after(lines, "| 2026-10-17 | **新增 D66", [D67_LOG], st, "主计划 §7")
    if D67_APPENDIX in lines:
        print("  [主计划 §附] 已在，跳过")
    else:
        i = len(lines) - 1
        while i >= 0 and not lines[i].startswith("|"):
            i -= 1
        lines[i + 1:i + 1] = [D67_APPENDIX]
        st["edits"] += 1
        print(f"  [主计划 §附] 追加在 L{i + 2}")
    save(PLAN, lines, st)


# --------------------------------------------------------------------------
# 二、Stage1 文档：§6 指引 + §7 遗留改写
# --------------------------------------------------------------------------
S1_NOTE = [
    "> **先跑这条命令**（D67）：把实机产出的逐被试 `.txt` 直接喂给验收检查器，6-C/6-D 不必手算 ——",
    ">",
    "> ```",
    "> python -X utf8 -u 1_Code\\Experiment\\exp_Check\\check_stage1_acceptance.py <被试1.txt> <被试2.txt> ...",
    "> ```",
    ">",
    "> 它逐条打印 `6-A`–`6-E` 的实测值（含 `stimulus_frames` 应有帧数、`max |ΔT| / FlipIntv`、"
    "`NA` 约定的违例行数、`0x00` 字节数、指定 T 档的 `T − max(RT)` 余量），末行给出「本机可判 4 项、需手测 2 项」。"
    "`6-A`（掩蔽纹理预加载）与 `6-E`（刺激内与刺激后按键的延时可比性）**不可机器判**，仍需人看。"
    "判据由 `1_Code/Experiment/exp_Check/check_stage1_acceptance.py::self_test` 的 5 个用例守住（干净数据 + 4 种人为缺陷）。",
]

S1_ITEM_OLD = (
    "5. **实机证据空缺**：§6 的四张表全空。这是本文件目前唯一的缺口，也是 Stage 1 是否算\"完成\"的唯一判据。"
)
S1_ITEM_NEW = (
    "5. **实机证据空缺**：§6 的四张表全空。这是本文件目前唯一的缺口，也是 Stage 1 是否算\"完成\"的唯一判据。"
    "**已缩窄（D67）**：`6-B`–`6-D` 改由 `1_Code/Experiment/exp_Check/check_stage1_acceptance.py` 机器判定"
    "（自测 5/5），人手只剩 `6-A` 与 `6-E` 两行 —— 但**这两行不填，Stage 1 仍然不算完成**。"
)


def do_stage1(st: dict) -> None:
    lines = load(STAGE1)
    i = idx_of(lines, "## 6. 实机验证步骤")
    if i < 0:
        raise SystemExit("[Stage1 §6] 找不到锚点")
    if S1_NOTE[0] in lines:
        print("  [Stage1 §6 指引] 已在，跳过")
    else:
        # 插在 §6 开头那段 blockquote（「本机无 MATLAB…」）之后，而不是之前
        j = i + 1
        while j < len(lines) and (lines[j].strip() == "" or lines[j].startswith(">")):
            j += 1
        while j > 0 and lines[j - 1].strip() == "":
            j -= 1
        lines[j + 1:j + 1] = [""] + S1_NOTE
        st["edits"] += 1
        print(f"  [Stage1 §6 指引] 插在 L{j + 2}")
    patch_row(lines, "5. **实机证据空缺**", S1_ITEM_OLD.strip(), S1_ITEM_NEW.strip(),
              st, "Stage1 §7 第 5 条")
    save(STAGE1, lines, st)


# --------------------------------------------------------------------------
# 三、DDM README：§8.42 + §9 第 51 项
# --------------------------------------------------------------------------
RM_842 = [
    "## 8.42 Stage 1 验收的机器判据，与合成生成器练习行的一处不符（2026-10-17，D67）",
    "",
    "### 动了什么",
    "",
    "1. `1_Code/Experiment/exp_Check/check_stage1_acceptance.py`（**新建**，408 行，零依赖，复用",
    "   `read_formal_data.read_one` 的列名口径）：把 `Stage1_技术验证记录.md` §6 的四张手填表变成 6-A–6-E",
    "   五组判据。`6-A`（掩蔽纹理预加载）与 `6-E`（刺激内/刺激后按键的延时可比性）**不可机器判**，",
    "   检查器如实标为「需手测 2 项」，不把它们算进通过率。",
    "2. `1_Code/DDM_Core/_scratch/make_fake_pilot.py` 的练习行 `Correct` 由 `0` 改为 `NaN`。",
    "",
    "### 为什么（判据为什么必须机器判）",
    "",
    "`6-C` 要判 `stimulus_frames == T / FlipIntv` —— 期望值是 **2 / 5 / 9 / 15**（四个 T 档）。",
    "在实验机上手算 2 名被试 × 4 个 T 档、还要逐行比对 `stimulus_offset_actual == mask_onset_actual`，",
    "**必错且不可复核**。检查器改为用 `_frames(t, fi) = max(1, int(round(t / fi)))` **现算**期望值，",
    "于是期望值本身也能被自测断言（注入 `--defect-1f` 的帧量化缺陷必须被拦住）。",
    "",
    "### 6-D 的五条，以及为什么「按字节搜 `0x00`」",
    "",
    "| 判据 | 期望 |",
    "|---|---|",
    "| 表头 | 25 列逐字比对 |",
    "| `NA` 约定 | `Response=NA` ⇒ `RT`、`Correct` 必须 NaN，`timeout=1`、`responded_by_deadline=0`；反之必须有限 0-1 |",
    "| `block` 编号 | 练习 0、正式 1-3 |",
    "| `0x00` 字节 | 按**字节**搜（文本解码会把 NUL 变成替换符而看不出） |",
    "| `timestamp` | 只做存在性检查（其值不作判据） |",
    "",
    "### 自测 5 例（`--self-test`）",
    "",
    "| 用例 | 期望 | 实测 |",
    "|---|---|---|",
    "| 干净数据（`make_fake_pilot.py` 现生成） | 通过 | ✅ |",
    "| `--defect-1f`（帧量化缺陷） | 拦住 6-C | ✅ |",
    "| `--defect-mismatch`（响应与 RT 矛盾） | 拦住 6-D | ✅ |",
    "| 变异：`Response=NA` 但 `RT` 有值 | 拦住 6-D | ✅ |",
    "| 变异：文件里混进 `0x00` 字节 | 拦住 6-D | ✅ |",
    "",
    "### 顺带修掉的缺陷：练习行的 `Correct` 不是 0，是 NaN",
    "",
    "`make_fake_pilot.py` 原来把练习行写成 `Correct = 0`，而 `1_Code/Experiment/exp_matlab/Exp_Design_Formal.m`",
    "在 `isPractice` 分支写 **NaN**（练习行没有对错）。于是「用生成器造干净数据去验检查器」这一例**必然失败**",
    "—— 生成器自己造了一行不合规的数据。已改为 `None if rt is None else ...`。",
    "**这条缺陷只在「生成器 × 检查器」这条闭环里现形**：真实文件的练习行由 MATLAB 程序写 NaN，碰不到。",
    "",
    "### 尚未做",
    "",
    "1. 真实文件未在手（需用户实机跑 N=2–3 名技术被试）。",
    "2. `6-A`（掩蔽纹理预加载）与 `6-E`（按钮延时可比性）两项**不可机器判**，必须人执行。",
    "3. 检查器不做**刺激时序**层面的复算（只看记录下来的列是否自洽）：真实时序要靠 MATLAB 打印的帧量化对照表。",
    "",
]

RM_9_51 = (
    "| 51 | ✅ **Stage 1 验收的机器判据 + 合成生成器练习行 `Correct` 的缺陷（D67，§8.42）** | "
    "`check_stage1_acceptance.py` 覆盖 6-A–6-D（6-A/6-E 标为需手测）、自测 **5/5**；"
    "`make_fake_pilot.py` 练习行 `Correct` 由 `0` 改 NaN。**还需**：真实文件（用户侧）+ `6-A`/`6-E` 人判。 |"
)


def do_ddm_readme(st: dict) -> None:
    lines = load(DDM)
    i9 = idx_of(lines, "## 9. 尚未做")
    if RM_842[0] in lines:
        print("  [DDM §8.42] 已在，跳过")
    else:
        lines[i9:i9] = RM_842
        st["edits"] += 1
        print(f"  [DDM §8.42] 插在 L{i9 + 1} 之前，{len(RM_842)} 行")
    i = len(lines) - 1
    while i >= 0 and not lines[i].startswith("| 50 |"):
        i -= 1
    if i < 0:
        raise SystemExit("[DDM §9] 找不到第 50 项")
    if lines[i + 1].startswith("| 51 |"):
        print("  [DDM §9 第 51 项] 已在，跳过")
    else:
        lines[i + 1:i + 1] = [RM_9_51]
        st["edits"] += 1
        print(f"  [DDM §9 第 51 项] 插在 L{i + 2}")
    save(DDM, lines, st)


def main() -> int:
    st = {"edits": 0, "written": 0, "dry": 0}
    print(f"{'✅ 真改' if APPLY else '⚠️ 干跑（不写盘）'}")
    for name, fn in (("主计划", do_master_plan), ("Stage1", do_stage1), ("DDM README", do_ddm_readme)):
        print(f"\n== {name} ==")
        fn(st)
    print(f"\n合计：编辑 {st['edits']} 处、写盘 {st['written']} 个文件、干跑 {st['dry']} 个")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
