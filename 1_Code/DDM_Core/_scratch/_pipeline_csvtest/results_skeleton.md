# 结果节骨架（半自动）

> 表格与统计量由 `run_pipeline.py` 从数据直接生成；`【待写】` 处需要人写论述。
> 若数据是合成的（目录里有 `synth_truth.json`），**本文件不得进入论文**。

## 1. 被试与场次

| 组 | 编号 | 判定 | 正式试次 | 练习试次 | 正确率 | timeout |
|---|---|---|---|---|---|---|
| 1 | 1 | EXCLUDE | 576 | 0 | 0.485 | 23.4% |
| 1 | 99 | EXCLUDE | 576 | 4 | 0.496 | 30.4% |
| 2 | 99 | EXCLUDE | 576 | 8 | 0.489 | 30.4% |

【待写】纳入 N、剔除理由、各组人数是否平衡。

## 4. 图

- `figures/fig1_behavior_by_P.png` —— 行为随 P 的变化（不依赖模型）
- `figures/fig2_param_recovery.png` —— 组层参数与被试层散点
- `figures/fig3_model_comparison.png` —— M-T1 vs M-T3 的 Δelpd

【待写】每张图的图注与正文引用。
