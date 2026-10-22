# 流水线报告

- 数据目录：`D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\2_Data\Real_Data\_SYNTHETIC_DEMO_v1`
- 输出目录：`D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\2_Data\Real_Data\_SYNTHETIC_DEMO_v1\_pipeline`
- 配置：`quick`（quick 仅供流程验证，数值不作结论）
- 总耗时：0.1 min

| 步骤 | 结果 | 详情 | 产物 |
|---|---|---|---|
| 1 入库判定 | ✅ | 8 场、KEEP 8 | `D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\2_Data\Real_Data\_SYNTHETIC_DEMO_v1\_pipeline\intake_report.md` |
| 2 Pilot 达标 | ✅ | 见报告 | `D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\2_Data\Real_Data\_SYNTHETIC_DEMO_v1\_pipeline\stage6_report.md` |
| 3 层级拟合 | ✅ | 复用已有 4 组 JSON（--reuse-stage8） | `D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\2_Data\Real_Data\_SYNTHETIC_DEMO_v1\_pipeline\stage8` |
| 3.5 LOO 健康 | ❌ | 可引用 0/4 组、4 组不可引用（判据 D73/D74/D75） | `D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\2_Data\Real_Data\_SYNTHETIC_DEMO_v1\_pipeline\results_skeleton.md` |
| 4 图 | ✅ | 2 s、含真值线 | `D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\2_Data\Real_Data\_SYNTHETIC_DEMO_v1\_pipeline\figures\figures_index.md` |
| 5 论文草稿 | ✅ | 8762 B、待写处 10 | `D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\2_Data\Real_Data\_SYNTHETIC_DEMO_v1\_pipeline\manuscript_draft.md` |

- 结果节骨架：`D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\2_Data\Real_Data\_SYNTHETIC_DEMO_v1\_pipeline\results_skeleton.md`

- 论文结果章草稿：`D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\2_Data\Real_Data\_SYNTHETIC_DEMO_v1\_pipeline\manuscript_draft.md`

> 若数据目录含 `synth_truth.json`，则本次全部产物来自**合成数据**，只能证明流水线可跑通，不得进入论文结果。
