# Guassion-Process-Experiment-Design

## Project Overview
This research project is based on the **Self-Matching Task** proposed by Sui (2012), focusing on exploring how three core experimental design variables influence the psychological decision-making process reflected by the **Self-Preference Effect (SPE)**. The variables under investigation are:
- Number of practice trials (P)
- Stimulus presentation time (T)
- Response window duration (W)

The goal is to establish a flexible and psychologically realistic framework for parameter modeling and virtual data generation, with a focus on capturing the uncertainty and individual differences in real participants' behavioral patterns.

## Background & Motivation
Initially, the project adopted the **Sigmoid function** to simulate the impact of variables (P, T, W) on the core parameters of the **Drift Diffusion Model (DDM)**:
- Drift rate (v)
- Boundary separation (a)
- Non-decision time (t₀)
- Starting point (z)

Using this approach, virtual reaction time and accuracy data were generated, and the rationality of the function fitting was verified. However, to better align with the complexity of real human behavior, we plan to optimize the model by introducing **Gaussian Process (GP)**.

## Core Innovation
Replace the fixed Sigmoid function with Gaussian Process (GP) to:
1. Automatically learn the nonlinear relationships between experimental variables (P, T, W) and DDM parameters (v, a, t₀, z)
2. Model the uncertainty and individual differences in psychological decision-making processes at the function level
3. Achieve a more flexible and generalizable virtual data generation framework

## Repository Structure
| File Name               | Description                                                                 |
|-------------------------|-----------------------------------------------------------------------------|
| `Generate_Data_v1.ipynb` | Initial code for data generation (based on Sigmoid function + DDM).后续将更新 GP-based 模型开发、数据生成与验证代码 (Subsequent updates will include GP-based model development, data generation, and validation code) |

## Future Updates
- Implementation of Gaussian Process (GP) for nonlinear relationship modeling
- Integration of GP with DDM to generate virtual behavioral data
- Validation of the optimized model against simulated/real participant data
- Documentation of parameter tuning and performance comparison (Sigmoid vs. GP)

## Key Terminology
| Term (Chinese)       | English Translation               | Abbreviation |
|----------------------|-----------------------------------|--------------|
| 自我匹配任务         | Self-Matching Task                | -            |
| 自我优势效应         | Self-Preference Effect            | SPE          |
| 漂移扩散模型         | Drift Diffusion Model             | DDM          |
| 高斯过程             | Gaussian Process                  | GP           |
| 练习试次数量         | Number of practice trials         | P            |
| 刺激呈现时间         | Stimulus presentation time        | T            |
| 反应窗口时长         | Response window duration          | W            |

## References
- Sui, J., He, X., & Humphreys, G. W. (2012). Perceptual advantages for self-related stimuli: A review. *Current Directions in Psychological Science*, 21(5), 318-323.

## Contact
For questions or collaborations, feel free to reach out via GitHub Issues or contact the repository owner.
