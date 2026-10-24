# New_Design 真实数据（20 人，2026-10-24 交付）

日期：2026-10-24
状态：✅现行（首轮分析口径）
依据：`1_Code/Experiment/real_data_check.py` 实跑产物；`2_Data/Generate_Data/_real_check/`
权威性：本目录数据的**唯一入口说明**。数字以 `_real_check/*.csv` 为准，本文只给字典与口径。

---

## 一、文件结构

```
New_Design/
├── Condition 1/   P = 0     5 人 × 576 试次
├── Condition 2/   P = 8     5 人 × 584 试次
├── Condition 3/   P = 32    5 人 × 608 试次
├── Condition 4/   P = 120   5 人 × 696 试次
│   ├── EXP_data_group{k}_{i}.csv     ← 分析用
│   └── exp_group{k}_subject{i}.txt   ← 同内容制表符版，不参与分析
```

合计 **20 人 / 12,320 试次**。`P` 是**组间**变量（每人只做一个 P），T × W × Label 是组内。

## 二、列字典（24 列，CSV 为 UTF-8 BOM）

| 列 | 含义 | 备注 |
|---|---|---|
| `groupID` / `subjectID` | 组号 / 组内编号 | 合成 `subject_id = groupID-subjectID`（如 `3-1`） |
| `P` | 练习量（组间剂量） | 0 / 8 / 32 / 120 |
| `T` | 刺激呈现时长 | **存的是该试次实际值**（如 0.0333287），非设计标称 |
| `W` | 反应期限 | 同上，实际值（799.9 / 1199.9 / 1799.9 ms） |
| `Label` | `self` / `stranger` | 自我 / 他人 |
| `Shape` | `circle` / `square` | 与 Label 交叉平衡 |
| `CorrectKey` | 正确键 | **与 Label 无固定对应**（self 的 j/f 各半）⇒ 按键偏好不构成身份混淆 |
| `Response` | 实际按键 | `NA` 表示未按键 |
| `RT` | 反应时（**秒**） | 实验里存秒，分析一律 ×1000 转 ms |
| `Correct` | 正确 | 0/1 |
| `premature_press` | 提前按键 | 0/1，窗口未开就按 |
| `timeout` / `responded_by_deadline` | 超时 / 期限内响应 | 互补 |
| `stimulus_*_actual` / `stimulus_dur_actual` / `stimulus_frames` | 实际时序与帧数 | 质检用（掉帧检测） |

## 三、清洗口径（`real_data_check.clean`）

```python
responded_by_deadline == 1  且  120 ms < RT <= W + 50 ms
```

- 下界 120 ms：剔除提前按键与"手滑连击"；
- 上界 `W + 50 ms`：容一帧误差（实际 W 有 ±0.1 ms 抖动）。
- 结果：12,320 → **8,992 试次（72.9%）**。被剔除的 3,328 试次中，超时 3,211、提前按键 1,186（有重叠）。

**T / W 必须先归到设计档位再分组**：`T_lvl ∈ {33.3, 83.3, 150, 250} ms`、`W_lvl ∈ {800, 1200, 1800} ms`（脚本里 `_nearest`）。直接按 `T` 的浮点值 `groupby` 会把 20 人拆成 80 个"伪档位"——第一版踩过这个坑。

## 四、质检结果

| 指标 | 数值 | 判读 |
|---|---|---|
| 超时率 | **26.1%**（3,211/12,320） | 偏高；W=800 ms 对这批被试偏紧（该档 30.1%） |
| 提前按键率 | 9.6%（1,186/12,320） | 需按期剔除 |
| 正确率（响应试次内） | 0.741 | — |
| 正确率（全部试次） | 0.548 | 超时按错算 |
| RT 中位（清洗后） | ~690 ms | 相对该任务的文献值偏慢 |
| 刺激时长偏差（均值） | **2.71 ms** | 正常 |
| 刺激时长偏差（最大） | **240 ms** | 每场 1–2 个掉帧试次，不是整场坏 |

**异常场次 `3-1`**（`Condition 3/EXP_data_group3_1.csv`）：RT q10/q50/q90 = 150/230/388 ms、自我 0.484 / 他人 0.500 正确率（≈ 猜测水平）、84 个试次 `|dur−T| > 20 ms`、各 T 档 meanRT 240–261 ms 与 T 无关 ⇒ 疑似"不看刺激就按"。**处置**：主统计保留（n=20），另出敏感性（剔除后 n=19，见 `_real_check/spe_summary_drop.csv`）——剔除后 SPE **更强**（Δacc 0.059→0.062、ΔRT 38.2→40.3 ms），说明它不是效应的来源，只是稀释。

## 五、产物位置

- 脚本：`1_Code/Experiment/real_data_check.py`
- 表格：`2_Data/Generate_Data/_real_check/{trial_clean,qc_session,qc_cell,desc_cell,spe_per_subject,spe_summary,spe_summary_drop,spe_by_p,tradeoff_point}.csv` + `meta.json`
- 图：`3_Figures/_real_check/fig_r1..r6`
- 结论备忘：`5_Reference/03_论文写作/真实数据分析_首轮结果_20261024.md`
