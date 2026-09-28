# Manim GP 原理动画演示 — 设计方案

> 立项日期：2026-09-27
> 用途：组会/课题组汇报，让听众直观理解"高斯过程"在本项目中的角色
> 状态：MVP 阶段（前 4 幕）实施中

---

## 一、目标与受众

| 项目 | 说明 |
|:---|:---|
| 核心目标 | 用动画讲清 GP 原理，并说明它如何服务于 (P, T, W) → SPE 的实验设计建模 |
| 受众 | 组会/课题组，默认知道 SMT 范式与 DDM，不需要从零解释实验背景 |
| 核心叙事 | 数据稀疏 → GP 用不确定性"诚实"回答未知区域 → 不确定性反过来指导下一轮实验 |
| 数据口径 | canonical4（G3–G8 共 6 个可用条件），G1/G2 因遗漏率过高已排除 |

---

## 二、技术选型

| 选择 | 决定 | 理由 |
|:---|:---|:---|
| 动画库 | **Manim Community** (`manim`) | 纯 Cairo 软件渲染，Windows 安装成熟；ManimGL 强依赖 OpenGL，依赖链脆弱 |
| Python | 3.12（独立 venv `.venv-manim`） | 项目现有 .venv 为 3.14，缺 manimpango/pycairo 预编译包；不污染主环境 |
| 视频后端 | ffmpeg | 优先 winget 安装；失败则用 imageio-ffmpeg 提供的静态二进制 + manim.cfg 指定路径 |
| 中文字体 | 系统 Microsoft YaHei | 避免 CJK 渲染为方块 |
| 公式渲染 | MathTex（TeX Live 2025 已装） | 若 dvisvgm 缺失导致失败，退化为 Text + Unicode 符号 |

---

## 三、分镜脚本

### MVP 阶段（本次交付，约 2.5 分钟）

| # | 场景 | 画面设计 | 时长 |
|:--:|:---|:---|:--:|
| S0 | 标题 | 项目名淡入 + 核心问题："只测了 6 个设计点，没测过的点会怎样？" | 15s |
| S1 | 把问题变成函数 | 三维坐标系中 6 个真实设计点依次落位；标注大片空白区域 | 30s |
| S2 | GP 是什么（1D） | 从 RBF 先验中采样：多条平滑函数曲线自左向右"生长" | 45s |
| S3 | 条件化 = 后验 | 观测点落入 → 曲线束收窄为 μ±2σ 带；远离数据处带宽自然膨胀 | 60s |

### 后续阶段（本次已全部完成）

| # | 场景 | 画面设计 | 时长 |
|:--:|:---|:---|:--:|
| S4 | 核函数的作用 | 滑杆连续拖动 length_scale（0.25→2.0），曲线束与不确定度带实时重算 | 32s |
| S5 | 升维到 3D | 三维空间中切出 W = 800 ms 的 (P, T) 截面，再"潜入"截面变成二维视图 | 31s |
| S6 | 真实数据接入 | 6 组真实 SPE_v 作为观测值 → 响应面热力图；给出 LOCV 限制与替换方案 | 25s |
| S7 | 从拟合到决策 | 同一截面把底色换成 σ，标出高不确定区与真实 Top 候选点 | 31s |
| S8 | 收尾 | (P,T,W) → Sigmoid 先验 → GP 残差 → DDM 参数 → 行为数据 的架构图 | 18s |

全片约 **4.4 分钟**。

---

## 四、数据接入

| 数据 | 来源 | 用途 |
|:---|:---|:---|
| 6 个真实条件 | `2_Data/Generate_Data/GP_Sigmoid_Canonical4/input_conditions_g3g8_canonical4.csv` | GP 观测点 (P, T, W) 与目标 SPE_v |
| 候选设计点 | `2_Data/Generate_Data/GP_Sigmoid_Canonical4/step6_candidate_design_points.csv` | S7 的 Top 候选点坐标（真实结果，非硬编码） |
| 留一验证指标 | `2_Data/Generate_Data/GP_Sigmoid_Canonical4/canonical4_summary.json` | S6 的 LOCV 相关系数 r |
| 核参数 | `step4_gp_sigmoid_model_canonical4.pkl` | S4 页脚的 ℓ 真实取值范围（0.16 ~ 1.78） |

S2/S3/S4 的一维 GP 演示使用固定随机种子的示意函数（教学用），S1/S5/S6/S7 使用真实数据。

### 关于 S5-S7 响应面的学术诚信说明（重要）

S5-S7 展示的响应面是一个**教学示范**：为让画面可读，把 GP 直接建在 SPE_v 上，
并取 ℓ = 0.45。项目正式的 GP 并不这样做——它拟合的是 **Sigmoid 预测的残差**，
且 ℓ 由边际似然自动优化（真实值 0.16 ~ 1.78）。

这一点在视频中通过两处明示：
1. S4 页脚给出项目真实的 ℓ 优化结果；
2. S6 明确说明"项目里 GP 不直接拟合 SPE_v，而是拟合 Sigmoid 预测的残差"。

S7 的 Top 候选点坐标与 σ 最大位置均来自项目真实输出
（`step6_candidate_design_points.csv`：rank 1 = P 0, T 500, W 300），与示范 GP 无关。

---

## 五、目录与产物

```text
1_Code/Animation_Manim/
├── manim.cfg                        # 渲染配置（背景色、媒体目录）
├── common.py                        # 共享：配色、字体、数据加载、GP 数学、绘图工具
├── build_video.py                   # 一键「渲染 9 幕 + 拼接为单视频」
├── scenes/
│   ├── s0_title.py                  # 开场：6 个条件与核心问题
│   ├── s1_design_space.py           # 三维设计空间散点与未测量区域
│   ├── s2_gp_prior.py               # GP 先验：一族函数 + ±2σ
│   ├── s3_gp_posterior.py           # 条件化：后验曲线束与 σ(x)
│   ├── s4_kernel_length_scale.py    # 核函数 length_scale 的连续滑杆
│   ├── s5_higher_dimension.py       # 三维切片 → 潜入截面
│   ├── s6_response_surface.py       # 真实数据接入与响应面
│   ├── s7_decision.py               # σ 图与 Top 候选点闭环
│   └── s8_closing.py                # GP 在项目中的位置
└── media/                           # 渲染中间产物（已 gitignore）
```

最终视频输出：`3_Figures/Animation/GP_Demo_1080p60.mp4`（另附 480p 预览版）

---

## 六、渲染命令

推荐用 `build_video.py` 一键完成（渲染全部 9 幕 + 拼接成单文件）：

```powershell
cd 1_Code\Animation_Manim
..\..\.venv-manim\Scripts\python.exe build_video.py --quick   # 480p15 快速预览，改台词时用
..\..\.venv-manim\Scripts\python.exe build_video.py           # 1080p60 正式版
```

单幕调试：

```powershell
..\..\.venv-manim\Scripts\python.exe -m manim -ql scenes\s7_decision.py S7Decision       # 低清预览
..\..\.venv-manim\Scripts\python.exe -m manim -qh scenes\s7_decision.py S7Decision       # 1080p60
```

场景类名与文件的对应关系见 `build_video.py` 的 `SCENES` 列表。

---

## 七、风险与规避

| 风险 | 影响 | 规避策略 |
|:---|:---|:---|
| manim 在 Python 3.12 安装失败 | 无法开工 | 先试 3.12；失败则退回 3.11 或改用 conda-forge |
| ffmpeg 缺失 | 无法合成视频 | winget 优先；备选 imageio-ffmpeg 静态二进制 + `ffmpeg_executable` 配置 |
| 中文字体渲染为方块 | 画面不可用 | 显式指定 `Microsoft YaHei`；渲染后抽样检查帧 |
| MathTex 失败（缺 dvisvgm） | 场景报错 | 关键公式改用 `Text` + Unicode（μ、σ、→） |
| 1080p60 渲染过慢 | 迭代周期长 | 开发全程用 `-ql` 480p 预览，仅最终交付渲染高清 |
| GP 可视化与项目结果不一致 | 学术风险 | S1/S6 直接读取项目 CSV，不在动画里硬编码数值 |

---

## 八、验收标准

1. MVP 4 幕可连续播放，总时长 2.5 分钟左右，无报错。
2. 画面中所有中文正常显示，无方块/乱码。
3. S1 的 6 个设计点坐标与 `input_conditions_g3g8_canonical4.csv` 完全一致。
4. S2/S3 的 GP 先验-后验逻辑正确：观测点处 σ≈0，远离观测点 σ 增大。
5. 输出 1080p60 MP4 可被常规播放器与 PPT 正常嵌入。

---

## 九、实施记录与方案偏差

实际实施过程中与原方案的差异，均源于环境实测结果：

| 原计划 | 实际做法 | 原因 |
|:---|:---|:---|
| MathTex 渲染公式 | 全部改用 `Text` + Unicode（μ、σ、→） | 本机 TeX Live 2025 缺 `standalone.cls`，MathTex 编译失败 |
| 用 ffmpeg 合成视频 | 不安装 ffmpeg | Manim 0.21 已内置 PyAV 编码器，无需外部二进制 |
| S1 相机缓慢环绕 | 相机固定 | 环绕后 3D 空间中的文字标签定位与可读性无法保证；改为静止相机 + 数据点逐个落位提供动感 |
| S1 逐点 G 标签 + 引线 | 改为右侧条件速查表 | 4 个条件（G3/G4/G7/G8）在设计空间中天然聚集，逐点标签必然重叠 |
| 多段视频拼接 | concat 分离器流拷贝 | 逐帧重编码会因时间基不匹配报 EINVAL；流拷贝无损且更快 |
| S5 固定 W 切面直接展示 | 加了"三维切一刀 → 潜入截面"的过渡 | 从三维到二维的视角切换比直接切画面更能让听众理解"截面"的含义 |
| S7 用 σ 等值线表示不确定度 | 以 σ **雾状图**为主、等值线为辅 | 该截面上 σ 大部分区域接近上限，等值线只剩两三条、信息量低；雾状图能直观反映"整片区域都不知道" |
| S4 用离散关键帧 morph | 用 `ValueTracker` + `always_redraw` 连续重算 | 连续滑动更能体现"ℓ 是一个连续可调的假设"，且视觉上更连贯 |

新增的 `1_Code/Animation_Manim/build_video.py` 提供一键「渲染 9 幕 + 拼接」，
并支持 `--quick` 以 480p15 快速出预览片。

`common.py` 的 GP 数学部分（RBF 核、Cholesky 采样、后验均值/标准差、多维 GP 回归）
用 numpy 手写，不依赖 sklearn，便于在动画脚本中直接复用并可复现（固定随机种子）。

### 遇到的 Manim API 陷阱（已修正，供后续维护参考）

| 现象 | 根因 | 正确做法 |
|:---|:---|:---|
| 热力图尺寸与坐标系对不上 | `ImageMobject.width` / `.height` 属性是等比缩放 | 用 `stretch_to_fit_width` / `stretch_to_fit_height` |
| `TypeError: Only values of type VMobject can be added as submobjects of VGroup` | `ImageMobject` 不是 VMobject | 放进 `Group` |
| 三维场景中的文字标签错位、倾斜 | `add_fixed_orientation_mobjects` 传入 VGroup 时以整体中心定向 | 逐个对象传入（`add_fixed_orientation_mobjects(*labels)`） |
| 中断渲染后报 `InvalidDataError` | 缓存里残留未写完的分片文件 | 删除对应画质的 `partial_movie_files` 后重跑 |
| 抽帧核对时序时画面与预期不符 | PyAV 的 `seek()` 定位不准 | 顺序解码到目标时间点 |

`ValueTracker` + `always_redraw` 的用法已验证：tracker **不需要**加入场景，
`self.play(tracker.animate.set_value(...))` 即可驱动重绘。