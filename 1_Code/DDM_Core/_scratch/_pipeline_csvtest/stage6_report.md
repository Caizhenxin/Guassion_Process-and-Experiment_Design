# Stage 6 ｜Pilot 达标报告

- 目录：`D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\1_Code\Experiment\exp_matlab\test\_full_session_out`
- 场次：3（计入 N = **0**，不计入 = 3）
- 覆盖 P 档：0 / 4（—）
- 目标 N：8 ⇒ **不足**

## 1. 逐场次

| 组 | 编号 | 判定 | 正式/练习 | 去重 | 正确率 | timeout | 复核标记／不计入原因 |
|---|---|---|---|---|---|---|---|
| 1 | 1 | EXCLUDE | — | — | — | — | 6-C 帧量化（核心）：无刺激期按键的 297 行：stimulus_dur_actual − T ∈ [−0.5, +1.5) 帧（5 处：['L8 (dur−T)/FlipIntv=-14.37 帧（239.40 ms）', 'L142 (dur−T)/FlipIntv=-4.41 帧（73.51 ms）', 'L275 (dur−T)/FlipIntv=-1.39 帧（23.12 ms）']）；裁决：S6-2 WARN、S6-1 FAIL、S6-6 WARN、S6-5 FAIL |
| 1 | 99 | EXCLUDE | — | — | — | — | 6-B KbQueue 刺激期按键：最小 T 档（33.33 ms）里至少 1 例 `Response` 非 NA 且 `RT < T`（实得 0 例） ⇒ 缺这个证据就说明 2 帧条件的按键没被记到；裁决：S6-1 FAIL、S6-6 WARN、S6-5 WARN |
| 2 | 99 | EXCLUDE | — | — | — | — | 6-B KbQueue 刺激期按键：最小 T 档（33.33 ms）里至少 1 例 `Response` 非 NA 且 `RT < T`（实得 0 例） ⇒ 缺这个证据就说明 2 帧条件的按键没被记到；裁决：S6-1 FAIL、S6-6 WARN、S6-5 WARN |

## 2. 判据汇总（仅计入场次）

| 判据 | PASS | WARN | FAIL | INFO | 未取到 |
|---|---|---|---|---|---|
| **S1-1** | 0 | 0 | 0 | 0 | 0 |
| **S1-1b** | 0 | 0 | 0 | 0 | 0 |
| **S6-3** | 0 | 0 | 0 | 0 | 0 |
| **S6-4** | 0 | 0 | 0 | 0 | 0 |
| **S6-1** | 0 | 0 | 0 | 0 | 0 |
| **S6-2** | 0 | 0 | 0 | 0 | 0 |
| **S6-2c** | 0 | 0 | 0 | 0 | 0 |
| **S6-5** | 0 | 0 | 0 | 0 | 0 |
| **S6-6** | 0 | 0 | 0 | 0 | 0 |
| **S6-2b** | 0 | 0 | 0 | 0 | 0 |

## 3. 按 §8 决策规则触发的分支

- 无 FAIL 触发。
- `S6-2c` 未超 20% ⇒ Stage 8 按现计划（静态输入）。

> 不计入场次里仍有非 PASS 裁决（**不触发** §8，仅作缺陷线索保留）：组1-被试1 S6-2 WARN、S6-1 FAIL、S6-6 WARN、S6-5 FAIL；组1-被试99 S6-1 FAIL、S6-6 WARN、S6-5 WARN；组2-被试99 S6-1 FAIL、S6-6 WARN、S6-5 WARN。

## 4. 结论

**暂不可进入 Stage 7。** 原因：计入 N 只有 0，不足 8；没有一场判定为 KEEP。

