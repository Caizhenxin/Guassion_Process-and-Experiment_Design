# -*- coding: utf-8 -*-
"""D87 落纸：Stage1 §6 回填（v4.6 那场）+ 主计划 D87/进度行 + README §8.60/§9-71 + 失败记录追加。

幂等：每处替换都断言命中 1 次；已存在则跳过。
"""
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
STAGE1 = ROOT / "5_Reference" / "08_工作流" / "Stage1_技术验证记录.md"
PLAN = ROOT / "5_Reference" / "08_工作流" / "工作流_主计划.md"
README = ROOT / "1_Code" / "DDM_Core" / "README.md"
FAIL = Path(r"D:\GitHub_programe\GitHub\Self-Repo\AI_Self_Improvement\2026-10-18_Stage1验收检查器判据只在60Hz成立.md")

changed = []


def read(p):
    return io.open(p, encoding="utf-8", newline="").read()


def write(p, s):
    with io.open(p, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(s)
    changed.append(p.name)


def rep(p, old, new):
    s = read(p)
    if new in s:
        print("SKIP(already)", p.name, old[:24])
        return
    n = s.count(old)
    if n != 1:
        sys.exit("HIT %d != 1 in %s :: %s" % (n, p.name, old[:60]))
    write(p, s.replace(old, new))
    print("OK", p.name, "::", old[:40])


# ---------------- Stage 1 §6 回填 ----------------
rep(STAGE1,
    "| T=33.33 ms 单元里 `Response` 为 `f`/`j`（不是 `NA`） | 至少 1 例 | **19 例**（2026-10-18，59.111 Hz 屏，576 试次） |",
    "| T=33.33 ms 单元里 `Response` 为 `f`/`j`（不是 `NA`） | 至少 1 例 | **15 例**（2026-10-18 **v4.6**，59.988 Hz 屏，组 2，576 试次）；v4.5 那场 19 例 |")

rep(STAGE1,
    "| 该行 `RT` < 0.0333 | ✅ | ✅ 19/19 全部 < 0.0333 |",
    "| 该行 `RT` < 0.0333 | ✅ | ✅ v4.6 15/15、v4.5 19/19，全部 < 0.0333 |")

rep(STAGE1,
    "| 注视期抢按被记为 `premature_press = 1`，且**不**影响该试次 RT | ✅ | ✅ 431 行 `premature_press = 1`；有 RT 的行 **全部为正**（v4.5 兜底后无负值） |",
    "| 注视期抢按被记为 `premature_press = 1`，且**不**影响该试次 RT | ✅ | ✅ v4.5 431 行、**v4.6 502 行** `premature_press = 1`；有 RT 的行 **全部为正**（无负值） |")

rep(STAGE1,
    "| 掩蔽期内按键仍被记录（`RT` 落在 T ~ T+200 ms 之间） | ✅ | ✅ **142 例**（含 T 档内 0.033–0.45 s 全区间） |",
    "| 掩蔽期内按键仍被记录（`RT` 落在 T ~ T+200 ms 之间） | ✅ | ✅ v4.5 142 例、**v4.6 225 例**（含 T 档内 0.033–0.45 s 全区间） |")

rep(STAGE1,
    "| `responded_by_deadline` / `timeout` 两列互补、无第三态 | ✅ | ✅ `timeout` 135 / `responded_by_deadline` 441（和 = 576，无第三态） |",
    "| `responded_by_deadline` / `timeout` 两列互补、无第三态 | ✅ | ✅ v4.5：135 / 441；**v4.6：41 / 535**；两场和都 = 576，无第三态 |")

rep(STAGE1,
    "| 启动打印的帧量化对照表 | 每个 T/W 偏离名义 ≤ 1 帧 | ✅ 59.111 Hz 下 T = 33.83 / 84.59 / 152.26 / 253.76 ms（2/5/9/15 帧），偏离 ≤ 4.3 ms；W 三档 132 / 198 / 297 帧 |",
    "| 启动打印的帧量化对照表 | 每个 T/W 偏离名义 ≤ 1 帧 | ✅ **v4.6 / 59.988 Hz**：T = 33.331 / 83.328 / 149.990 / 249.984 ms（**2/5/9/15 帧**），偏离 ≤ **0.005 ms**；W = 799.948 / 1199.922 / 1799.882 ms（48/72/108 帧）。（v4.5 那场 59.111 Hz：T = 33.83 / 84.59 / 152.26 / 253.76 ms，偏离 ≤ 4.3 ms） |")

rep(STAGE1,
    "| 全部无刺激期按键试次的 `stimulus_frames` | 分别 ≈ 2 / 5 / 9 / 15（±1 帧） | ✅ 297 行里 291 行落在 0 / 2 / 5 / 9 / 15，另有 5 行抢按截断（见下行）与 1 行 +1 帧余量 |",
    "| 全部无刺激期按键试次的 `stimulus_frames` | 分别 ≈ 2 / 5 / 9 / 15（±1 帧） | ✅ **v4.6：341 行全部落在 2 / 5 / 9 / 15**（v4.5：297 行里 291 行落位，另 5 行抢按截断） |")

rep(STAGE1,
    "| `max (stimulus_dur_actual − T) / FlipIntv` | ∈ [−0.5, +1.5) | ❌ **5 行越界**：−1.37 / −1.61 / −4.35 / −13.95 / −14.15 帧；其余 292 行 ∈ [−0.02, +1.16]（max 1.16 帧 = vsync 余量） |",
    "| `max (stimulus_dur_actual − T) / FlipIntv` | ∈ [−0.5, +1.5) | ✅ **v4.6：0 行越界**，341 行 ∈ [+0.06, +0.51] 帧（vsync 余量）。（v4.5 那场曾有 5 行越界：−1.37 / −1.61 / −4.35 / −13.95 / −14.15 帧，已由 v4.6 的 `tFloor` 收口） |")

rep(STAGE1,
    "> ⚠ **6-C 的 5 行越界（D83）**：",
    "> ✅ **已收口（D87，2026-10-18）**：同一判据在 v4.6 那一场（576 试次）上 **0 行越界**，`frames == round(dur/FlipIntv)` 全部成立，\n> 说明 v4.6 的 `tFloor` 修法把「onset 之前的键」彻底挡在反应窗口之外。下面这段是当时（v4.5）的现场记录，保留备查：\n>\n> ⚠ **6-C 的 5 行越界（D83）**：")

rep(STAGE1,
    "| 漏答行的 `Response` 是 `NA`（不是空、不是 `0`） | ✅ | ✅ 135 行全部为 `NA` |",
    "| 漏答行的 `Response` 是 `NA`（不是空、不是 `0`） | ✅ | ✅ v4.5：135 行；**v4.6：41 行**，全部为 `NA` |")

rep(STAGE1,
    "| 漏答行的 `Correct` 是 `NaN`、`timeout = 1`、`responded_by_deadline = 0` | ✅ | ✅ 135/135 |",
    "| 漏答行的 `Correct` 是 `NaN`、`timeout = 1`、`responded_by_deadline = 0` | ✅ | ✅ v4.5 135/135、**v4.6 41/41** |")

rep(STAGE1,
    "| 练习行 `block = 0`，正式行 `block ∈ {1,2,3}` | ✅ | ✅ 本场组 1（P=0）无练习行；正式 `block` 1/2/3 各 192 |",
    "| 练习行 `block = 0`，正式行 `block ∈ {1,2,3}` | ✅ | ✅ 两场均无练习行（CSV 只落正式段）；正式 `block` 1/2/3 各 192 |")

rep(STAGE1,
    "5. **实机证据空缺**：§6 的四张表全空。",
    "5. **实机证据空缺**：§6 中 `6-B` / `6-C` / `6-D` 已按 **v4.6 那场**（2026-10-18，59.988 Hz，组 2，576 试次）逐项回填（D87），**`6-A` 与 `6-E` 仍空**。")

# ---------------- 主计划：D87 决策行 ----------------
D87 = ("| **D87** | 2026-10-18 | ✅ **v4.6 的 60 Hz 实机数据把「程序对了」与「判据对了」分开："
       "时序 576/576 命中，同时抓出检查器自己的两个缺陷（flip 反推、W 归组）**。① 触发：用户交回 `EXP_data_group1_99.csv`（576 正式试次、25 列、无练习行）；"
       "② 数据侧结论：T = 33.331 / 83.328 / 149.990 / 249.984 ms（**2/5/9/15 帧**，偏离 ≤ 0.005 ms）、W = 799.948 / 1199.922 / 1799.882 ms（48/72/108 帧）、"
       "`premature_press` 502 行、漏答 41、`responded_by_deadline` 535（和 = 576）、掩蔽期按键 225 例、T=33.33 档 RT<T 15 例、"
       "`stimulus_offset == mask_onset` 576/576、`mask_onset == onset + dur` 576/576、txt 577 行**无重复 trialID**（v4.5 补 `fclose` 的现场证据）；"
       "③ 判据侧缺陷 A：`check_stage1_acceptance.py` 的 `estimate_flip()` 用 `dur/T × 名义帧数` 反推，假定 `dur ≈ T`，"
       "而实际必带 0~1 帧 vsync 余量 ⇒ 16.625 ms 被算成 16.8615 ms（59.988 Hz 算成 59.3 Hz），"
       "于是「正常的 +1 帧余量」被算成「偏离」；改为**带先验的网格搜索**（flip ∈ 名义值 ±10%，步长 0.001 ms，取 Σ|dur − frames·flip| 最小）；"
       "④ 判据侧缺陷 B：`check_manipulation.py` 用 `round(W_ms, 0)` 归组，W=799.948 / 1199.922 / 1799.882 三档在数据里就取不到 800/1200/1800 这三个键，"
       "分组直接丢空 ⇒ 改为按 `int(round(W×1000))` 建键、报告里同时打名义值；"
       "⑤ 修后复查：环境门 ✅（59.988 Hz ∈ 60.004±1）、**6-B 3/3、6-C 5/5、6-D 5/5 全部 ✅**（此前 6-C 是 ❌），"
       "`--self-test` 6 → **7/7**（新增「+1 帧余量不得被算成偏离」的健壮性用例）；"
       "⑥ 判读：这是一场**按着玩**的试跑（RT<T 43.9%、操纵检查 800 档 7.3% vs 1800 档 3.6%、差 3.6 pp < 10 pp ⇒ 未通过，符合乱按预期），"
       "**不是被试数据、不计入 Pilot 的 N=8**；但「程序 v4.6 在 60 Hz 机上时序全中」这一条已由它证明 | "
       "`1_Code/Experiment/exp_Check/check_stage1_acceptance.py`（516 → **533 行**，grid search）、`1_Code/Experiment/check_manipulation.py`（183 → **190 行**，W 键）、"
       "`5_Reference/08_工作流/Stage1_技术验证记录.md`（6-B/6-C/6-D 回填）、主计划 D87、README §8.60 | "
       "① 6-A（启动回显）与 6-E（刺激内/后按键延时可比性）仍需人看；② 用 v4.6 在实验室机跑**真被试** Pilot（N≈8） |\n")

s = read(PLAN)
if "| **D87** |" not in s:
    lines = s.split("\n")
    idx = [i for i, ln in enumerate(lines) if ln.startswith("| **D85** |")]
    if len(idx) != 1:
        sys.exit("D85 row not unique: %d" % len(idx))
    lines.insert(idx[0] + 1, D87.rstrip("\n"))
    write(PLAN, "\n".join(lines))
    print("OK plan D87 row")
else:
    print("SKIP plan D87 row")

PROG = ("| 2026-10-18 | **6**（检查器自身缺陷 → D87） | **把「程序对了」与「判据对了」分开**：v4.6 那场 576 试次里时序 576/576 命中（T 2/5/9/15 帧、偏离 ≤ 0.005 ms），"
        "但检查器自己两处错——`estimate_flip` 假定 `dur ≈ T`（忽略 0~1 帧 vsync 余量）把 59.988 Hz 算成 59.3 Hz、`check_manipulation` 用 `round(W_ms)` 归组导致分组丢空；"
        "改成网格搜索 + 整数毫秒键后 6-B/6-C/6-D 全 ✅（此前 6-C ❌） | 主计划 D87、Stage1 §6 回填、README §8.60 | 6-A/6-E 需人看；换实验室机跑真被试 Pilot |\n")

s = read(PLAN)
if "（检查器自身缺陷 → D87）" not in s:
    lines = s.split("\n")
    idx = [i for i, ln in enumerate(lines) if ln.startswith("| 2026-10-18 | **6**（v4.6 修法的契约测试 → D84） |")]
    if len(idx) != 1:
        sys.exit("progress row not unique: %d" % len(idx))
    lines.insert(idx[0] + 1, PROG.rstrip("\n"))
    write(PLAN, "\n".join(lines))
    print("OK plan progress row")
else:
    print("SKIP plan progress row")

# ---------------- README §8.60 + §9 第 71 项 ----------------
SEC = """### 8.60 判据自己也会错：flip 反推与 W 归组（2026-10-18，D87）

v4.6 的 60 Hz 实机那一场，数据侧 576/576 命中设计（T 2/5/9/15 帧、偏离 ≤ 0.005 ms、`mask_onset == onset + dur` 576/576），
检查器却报 6-C 有偏离。**这一次红的是判据，不是数据**：

- 缺陷 A：`estimate_flip()` 用 `dur / T × 名义帧数` 反推帧长，隐含「实际时长 ≈ 名义时长」。
  而实际时长**必然**带 0~1 帧 vsync 余量（§7 第 2 条），于是 16.625 ms 被算成 16.8615 ms（59.988 Hz → 59.3 Hz），
  正常的 +1 帧余量反而变成「偏离」。改法：**带先验的网格搜索**（flip ∈ 名义值 ±10%，步长 0.001 ms，取 Σ|dur − frames·flip| 最小）。
- 缺陷 B：`check_manipulation.py` 用 `round(W_ms, 0)` 归组。W 在数据里是 799.948 / 1199.922 / 1799.882，
  取整后建出的键和查表用的键对不上，分组直接丢空。改法：按 `int(round(W × 1000))` 建键，报告里同时打名义值。

两侧都修的收益是清楚的：6-B 3/3、6-C 5/5、6-D 5/5 全过，且 `--self-test` 从 6 例加到 **7 例**
（新增「+1 帧余量不得被算成偏离」的健壮性用例）——**判据也要有它自己的反例**。

边界：这修的是判据，不是给我一个「能过」的结论。同一套检查器在那场数据上仍然把 RT 中位 126.6 ms、
RT<T 43.9% 判成异常（正确定性为「按着玩的试跑」），操纵检查仍未通过。

"""
s = read(README)
if "### 8.60 判据自己也会错" not in s:
    lines = s.split("\n")
    idx = [i for i, ln in enumerate(lines) if ln.startswith("## 9.")]
    if len(idx) != 1:
        sys.exit("## 9. not unique: %d" % len(idx))
    lines.insert(idx[0], SEC.rstrip("\n"))
    write(README, "\n".join(lines))
    print("OK README 8.60")
else:
    print("SKIP README 8.60")

ITEM = ("| 71 | ✅ **判据自己也会错：flip 反推与 W 归组（D87，§8.60）** | "
        "`estimate_flip` 假定 `dur ≈ T` ⇒ 把 0~1 帧 vsync 余量算成偏离（59.988 Hz 报成 59.3 Hz）；`check_manipulation` 用 `round(W_ms)` 归组 ⇒ 分组丢空。"
        "改网格搜索 + 整数毫秒键后 6-B/6-C/6-D 全 ✅，`--self-test` 6 → 7。 |\n")

s = read(README)
if "| 71 | ✅ **判据自己也会错" not in s:
    lines = s.split("\n")
    idx = [i for i, ln in enumerate(lines) if ln.startswith("| 69 | ✅ ")]
    if len(idx) != 1:
        sys.exit("item 69 not unique: %d" % len(idx))
    lines.insert(idx[0] + 1, ITEM.rstrip("\n"))
    write(README, "\n".join(lines))
    print("OK README item 71")
else:
    print("SKIP README item 71")

# ---------------- 失败记录：再次触发 ----------------
APPEND = """
## 再次触发记录（2026-10-18，D87，同一根因第三次）

- **触发场景**：用户交回 v4.6 在 60 Hz 机上的 576 试次实机数据，检查器仍报 6-C 偏离。
- **新发现的原因（两条，都在判据侧）**：
  1. `estimate_flip()` 用 `dur / T × 名义帧数` 反推帧长，隐含「实际时长 ≈ 名义时长」；实际必带 0~1 帧 vsync 余量
     ⇒ 16.625 ms 被算成 16.8615 ms（59.988 Hz 报成 59.3 Hz），正常余量被算成偏离。
  2. `check_manipulation.py` 用 `round(W_ms, 0)` 归组；数据里 W = 799.948 / 1199.922 / 1799.882 ⇒ 取整键与查表键不一致，分组丢空。
- **是否换方案**：是。flip 估算改**带先验的网格搜索**（±10%，步长 0.001 ms，目标 Σ|dur − frames·flip| 最小）；
  W 归组改 `int(round(W×1000))` 并同时打印名义值。`--self-test` 6 → 7 例（新增「+1 帧余量不得被算成偏离」）。
- **仍然有效的教训**：判据里每个隐含常量都是未验证假设；「检查器报红」≠「数据不合格」，先证明判据本身对。
  这次连「修好的判据」也仍需自证——所以健壮性用例必须包含「合法但非理想」的真实形态（+1 帧余量就是一种）。
"""
s = read(FAIL)
if "再次触发记录（2026-10-18，D87" not in s:
    write(FAIL, s.rstrip("\n") + "\n" + APPEND)
    print("OK failure append")
else:
    print("SKIP failure append")

print("changed:", changed)
