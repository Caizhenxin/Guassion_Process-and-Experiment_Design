# 已剔除数据（Excluded）

> 建立：2026-09-30 ｜ 决定人：蔡振辛

本目录存放**从分析池中剔除、但保留原始记录**的实验数据文件。剔除不等于删除——原文件完整保留在此，便于复核与恢复。

| 文件 | 原位置 | 剔除原因 |
|---|---|---|
| `EXP_data_group2_11.csv` | `UnExtact/raw/` | 被试中途实验卡死，重新进入后**按键映射记录错误** |
| `EXP_data_group2_11.emp_data_copy.csv` | `UnExtact/emp_data/` | 同一被试的另一份副本（序列化格式不同：缺失值写作空串而非 `NA`） |

---

## 一、剔除依据

该被试（`groupID=2, subjectID=11`，`subjectID % 4 == 3`）的记录 `CorrectKey` **全部**落在错误的映射模式上：

| 项目 | 应有（编号规则推导） | 实际记录 |
|---|---|---|
| 模式 | `SAME`（mod ∈ {0,3}） | `ALT` |
| `(square,self) →` | `f` | `j` |
| `(square,stranger) →` | `j` | `f` |
| `(circle,self) →` | `j` | `f` |
| `(circle,stranger) →` | `f` | `j` |
| 正式试次中 KeyErr 比例 | 0% | **100%**（1320/1320） |

推导规则与 `1_Code/Python_for_Check/Visualization/app_server.py` 的 `get_pairing_rules()`、`get_match_key()` 一致；复核脚本：`_scratch/check_nonmatch_quality.py`。

**后果**：该被试的 Matching / NonMatching 标签会整体**对调**——它真实的"匹配"试次会被标成"不匹配"，反之亦然。若不剔除，会同时污染匹配列与不匹配列。

该结论与 `1_Code/Experiment/exp_matlab/test/刺激呈现期按键无法记录_原因排查与结论.md` 早前的独立排查记录一致（当时结论为"按键映射与编号不匹配，建议分析中剔除或按其实际规则重算"）。

---

## 二、影响范围

| 项目 | 剔除前 | 剔除后 |
|---|---|---|
| 可用被试数 | 88 | **87** |
| 正式试次数 | 45,760 | **45,240** |
| 四格（身份 × 匹配性）每格 | 11,440 | **11,310** |

四格仍然完全平衡，不匹配试次仍可全部保留。

---

## 三、如需恢复

两个选项，**任选其一，不要混用**：

1. **按其实际按键规则重算**：对该被试使用 `ALT` 模式（`R_ALT`）重新推导 `CorrectKey` / `condition`，再放回分析池。需同时确认他是否真的做了完整的两套试次。
2. **整体恢复原状**：把文件移回 `UnExtact/raw/`，并从 `_scratch/check_nonmatch_quality.py` 的 `EXCLUDED` 集合与 `_scratch/check_single_v_consistency.py` 的 `SKIP` 集合中移除文件名。

---

## 四、下游必须同步的位置

| 位置 | 需要的动作 |
|---|---|
| `1_Code/Python_HDDM_Nonmatching/step1_prepare_data.py` | 自动按 `RAW_DIR.glob("EXP_data_group*.csv")` 读取，**文件已移出 `raw/`，无需改代码** |
| `1_Code/Python_HDDM/`（原版，仅匹配） | 同上，自动生效 |
| `2_Data/Real_Data/UnExtact/emp_data/` | 该目录不是 `step1` 的输入，但已同步移除以保持两处一致 |
| 任何已生成的 `HDDM_Ready*` / `HDDM_Traces*` | **需要用剔除后的 87 人重新生成**（旧产物仍含该被试） |

> ⚠️ 最后一行是硬约束：剔除决策发生在 2026-09-30，此前产出的所有 HDDM 结果都包含这名被试，重新生成前不要在论文中引用新旧数字的差异。
