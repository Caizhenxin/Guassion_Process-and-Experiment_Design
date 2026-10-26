# -*- coding: utf-8 -*-
"""D123 落纸：t0 上界与「刺激期内按键」剔除（B 路线）。

幂等：每处插入前断言只命中一次，重复运行不会写第二遍。
"""
from pathlib import Path

ROOT = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
PLAN = ROOT / "5_Reference/08_工作流/工作流_主计划.md"
README = ROOT / "1_Code/DDM_Core/README.md"
SOP = ROOT / "5_Reference/08_工作流/数据快速筛查SOP.md"

D_ROW = (
    "| **D123** | 2026-10-25 | **`t0` 上界被快反应压死，选 B（剔除）而不是 A（污染项）**。"
    "把 `RT_FLOOR` 0.15 → **0.20**（依据：150–200 ms 带正确率 **0.486**＝机会水平、"
    "该带 28.1% 是刺激期内按键），并新增 `dev_mask`：`|stimulus_dur_actual − T| > 一帧"
    "（16.7 ms）` ⇒ 该试次在刺激呈现期内就按了键（程序把刺激截到按键后一帧，`dur − rt` "
    "中位 3 ms，151 个已响应试次里 99.3% 是这个合法签名；真掉帧全数据集只有 1 个）。"
    "`fit_ready(tr, rt_floor, rec, dev_max)` 两条口径合并剔除，未传 `rec` 时 dev 口径不生效"
    "（向后兼容）。代价：剔 110/7574＝**1.45%**，Δacc +0.0651→+0.0695、ΔRT 37.26→38.08 ms、"
    "斜率 30.42→30.64 ms（全部远小于 SE）⇒ **既不制造也不削弱 SPE**。"
    "收益：17 人的 `t0` 上界 0.135–0.376（2-5 由 0.135 抬到 0.191、3-4→0.290、4-4→0.224），"
    "13/18 人抬 30–142 ms。A（`λ·Uniform(0,W)` 污染项）暂不上，判据：Stage 8 重跑后 PPC 的 "
    "RT 中位欠估缩到 ±20 ms 即判 B 够用。 | "
    "`_scratch/_probe_fast_rt.py`、`_probe_rt_floor.py`、`_probe_dev_sign.py`、`_probe_drop_effect.py`；"
    "`check_read_formal_data.py` 31 项全过 | "
    "`read_formal_data.py`（RT_FLOOR/dev_mask/fit_ready 签名）+ `stage8_run.py`（传 `rec`）+ "
    "SOP §十；`plan-only` 读数 17 人 / 被拒 0 / ≈2.23 h |"
)

PROG_ROW = (
    "| 2026-10-25 | **20（t0 上界与快反应剔除 → D123）** | "
    "**把「为什么一条 150 ms 的抢按能顶死整份拟合」查清并修掉了**：150–200 ms 带正确率 0.486"
    "（机会水平）⇒ 该带不含辨识信息；151 个计时偏差试次里 99.3% 是「刺激期内按键被程序截短」"
    "的合法签名（真掉帧只有 1 个）⇒ 剔除 1.45% 即可把 13/18 人的 `t0` 上界抬高 30–142 ms，"
    "而 SPE 三个端点量几乎不动（远小于 SE）。未做：Stage 8 重跑（进行中，17 人）、A 路线的 "
    "`λ·Uniform(0,W)` 评估。 | 用户 2026-10-25「先做 B，再看要不要做 A」 | "
    "`read_formal_data.py`（`dev_mask`/`RT_FLOOR=0.20`）；`check_read_formal_data.py` 31 项；"
    "SOP §十 |"
)

CHG_ROW = (
    "| 2026-10-25 | **新增 D123（`t0` 上界与「刺激期内按键」剔除）**：`RT_FLOOR` 0.15→0.20、"
    "新增 `DEV_MAX=0.0167` 与 `dev_mask()`、`fit_ready` 支持 `rec`；`stage8_run` 传 `rec` 并逐人"
    "打印刺激期内按键条数；剔除 1.45%、SPE 端点量不变、13/18 人 `t0` 上界抬 30–142 ms。 |"
)

EV_ROW = (
    "| `1_Code/Experiment/read_formal_data.py`（`RT_FLOOR=0.20` / `DEV_MAX` / `dev_mask` / "
    "`fit_ready(rec=)`）+ `1_Code/DDM_Core/stage8_run.py`（传 `rec`）+ "
    "`1_Code/Experiment/exp_Check/check_read_formal_data.py`（31 项）+ "
    "`5_Reference/08_工作流/数据快速筛查SOP.md` §十 | "
    "D123 证据：150–200 ms 带 acc 0.486＝机会水平；151 个计时偏差试次 99.3% 是刺激期内按键"
    "（`dur−rt` 中位 3 ms），真掉帧仅 1 个；剔除 110/7574＝1.45%，Δacc/ΔRT/斜率变动 0.4 pp / "
    "0.8 ms / 0.2 ms（远小于 SE）；17 人 `t0` 上界 0.135–0.376、13/18 人抬 30–142 ms |"
)

README_ROW = (
    "| 104 | ✅ **`t0` 上界与「刺激期内按键」剔除（D123）**：`read_formal_data.RT_FLOOR` 0.15→0.20、"
    "新增 `DEV_MAX=0.0167` 与 `dev_mask()`、`fit_ready(tr, rt_floor, rec, dev_max)`；"
    "`stage8_run` 传 `rec` 后 17 人全部可拟合（`t0` 上界 0.135–0.376）。自检 31 项全过。 | "
    "D123 |"
)


def insert_after(lines: list[str], anchor_prefix: str, new_row: str, tag: str) -> None:
    hits = [i for i, ln in enumerate(lines) if ln.startswith(anchor_prefix)]
    assert len(hits) == 1, f"{tag}: 命中 {len(hits)} 次（{anchor_prefix[:40]}）"
    lines.insert(hits[0] + 1, new_row)


def insert_before(lines: list[str], anchor_prefix: str, new_row: str, tag: str) -> None:
    hits = [i for i, ln in enumerate(lines) if ln.startswith(anchor_prefix)]
    assert len(hits) == 1, f"{tag}: 命中 {len(hits)} 次（{anchor_prefix[:40]}）"
    lines.insert(hits[0], new_row)


def main() -> None:
    # ---- 主计划 ----
    text = PLAN.read_text(encoding="utf-8")
    lines = text.split("\n")
    if "**D123**" not in text:
        insert_before(lines, "| **D122** | 2026-10-25 |", D_ROW, "D123 决策行")
        insert_after(lines, "| 2026-10-25 | **19（定编两条腿 → D122）** |", PROG_ROW, "进度行")
        insert_after(lines, "| 2026-10-25 | **新增 D122（定编两条腿：N_精度 + N_区分）**",
                     CHG_ROW, "变更日志行")
        # 证据行：追加到表格末尾（跳过结尾空行）
        while lines and lines[-1].strip() == "":
            lines.pop()
        lines.append(EV_ROW)
        lines.append("")
        PLAN.write_text("\n".join(lines), encoding="utf-8", newline="\n")
        print(f"[plan] {PLAN.name}: {len(lines)} 行（含新增 4 行）")
    else:
        print("[plan] D123 已存在，跳过")

    # ---- README §9 ----
    text = README.read_text(encoding="utf-8")
    if "（D123）" not in text:
        lines = text.split("\n")
        insert_after(lines, "| 103 | ", README_ROW, "README 第 104 项")
        README.write_text("\n".join(lines), encoding="utf-8", newline="\n")
        print(f"[readme] {README.name}: {len(lines)} 行")
    else:
        print("[readme] D123 已存在，跳过")

    # ---- SOP §十：把三条路线改成「已选 B」 ----
    text = SOP.read_text(encoding="utf-8")
    marker = "**已选 B（2026-10-25，D123）**"
    if marker not in text:
        old = "三条路线："
        assert text.count(old) == 1, "SOP 里没有唯一的『三条路线：』锚点"
        add = (
            "**已选 B（2026-10-25，D123）**：`RT_FLOOR` 0.15 → **0.20**（150–200 ms 带正确率 "
            "0.486＝机会水平），并按 `dev_mask`（`|stimulus_dur_actual − T| > 16.7 ms`）剔除"
            "刺激期内按键的试次；合计剔除 **1.45%**，`t0` 上界 13/18 人抬 30–142 ms，"
            "SPE 三个端点量变动远小于 SE。A 路线（`λ·Uniform(0,W)` 污染项）留作后备。\n\n"
            "三条路线（原始备选）："
        )
        text = text.replace(old, add, 1)
        SOP.write_text(text, encoding="utf-8", newline="\n")
        print(f"[sop] 已标注选 B（{len(text.splitlines())} 行）")
    else:
        print("[sop] 已标注，跳过")


if __name__ == "__main__":
    main()
