# 版本更新日志

---

## v0.8 (2026-09-28)

**责任人**：蔡振辛

### 问题修复（v0.7 引入的"一进试次就崩溃"）
- **现象**：`Exp_Design_Formal` 跑到第一个试次的 `checkEscape()` 即报
  `错误使用 KbName / Key name "esc" not recognized`，整场实验在正式试次开始前退出。
- **根因**：v0.7 在文件开头加了一句 `KbName('UnifyKeyNames')`。本机 PTB 3.0.19 实测：
  开启"统一键名"后**小写 `'esc'` 立即变成无效键名**（只认 `'ESCAPE'`/`'escape'`），
  而本程序其余各处仍按未开启时的命名方案书写（`'esc'` / `'return'` / `'space'`）→ 第一个
  `checkEscape` 直接抛错。
- **同源印证**：这正是 `Exp_Design_Formal_v2.m` 当初"无法进入正式试次、txt 只有表头"的真正原因
  （v2 同样同时使用了 UnifyKeyNames + `KbName('esc')`），**与 KbQueue 无关**。
- **实测数据（本机 PTB 3.0.19，`matlab -batch`）**：

  | 键名 | 未开启 UnifyKeyNames | 开启后 |
  |---|---|---|
  | `'esc'` | 27 ✓ | **报错** |
  | `'ESCAPE'` | 报错 | 27 ✓ |
  | `'return'` / `'space'` / `'f'` / `'j'` | ✓ | ✓ |

  反向查询 `KbName(70)`→`'f'`、`KbName(74)`→`'j'` 在两种方案下完全一致，故 f/j 判定不受影响。

### 修复内容
- **撤销** `KbName('UnifyKeyNames')`，回到原版（即采集 88 人数据时）的命名方案；
  并在该位置留下醒目注释，防止以后再次加回。
- **加固** `checkEscape`：Esc 键码用 `persistent` 只解析一次，先试 `KbName('esc')`、
  失败再试 `KbName('ESCAPE')` —— 对两种命名方案都兼容，即使日后有人重新打开 UnifyKeyNames 也不会再整场崩溃。

### 验证
- `matlab -batch checkcode`：0 语法错误（仍为那 4 条既有无害告警）
- `matlab -batch` 实测修复后的键盘路径（无需开窗）：`KbName('esc')=27`、`KbCheck` 正常返回 256 长度
  `keyCode`、`checkEscape` 判定表达式求值成功、`KbName(70)='f'`、`KbName(74)='j'`、
  `KbName('return')=13`、`KbName('space')=32` → ALL_OK

### 另注（非阻塞，属环境问题）
- 该机运行时 PTB 报 `beamposition timestamping computed an impossible stimulus onset value`，
  随后 PTB **自动关闭高精度时间戳**、改用 VBL 时间戳（实测 164.87 Hz，接近系统报告的 165 Hz）；
  另有 DWM 合成器开启、Windows 11 不受支持、`libptbdrawtext_ftgl64.dll` 缺失（中文回落 GDI 渲染）等提示。
  本次均未导致中断。若需更稳的同步，可用 `ptb_switch_screen('light')`，或把
  `Screen('Preference','SkipSyncTests',0)` 改为 `1`（跳过同步自检，但同样会放宽时间精度保证）。

---

## v0.7 (2026-09-28)

**责任人**：蔡振辛

### 问题修复（正式采集程序 `Exp_Design_Formal.m`）
- **刺激呈现期/掩蔽期按键被整题丢弃**：旧版只在"掩蔽结束后的空白屏"里用 `KbCheck` 轮询，
  刺激呈现期(T)与掩蔽期(200 ms)按下的键根本不会被读取 → 表现为漏答或 RT 偏大。
  现改为在 **刺激期 / 掩蔽期 / 反应窗口** 三段全程轮询键盘，取最早的 f/j 按键作为反应。
- **W 口径错误**：旧版 deadline = `onset + T + W`，等价于"W 从刺激结束起算"。
  现修正为 **`deadline = stimulusFlipTime + W`**（W = 自刺激 onset 起算到最晚可反应时刻），
  RT 口径不变 = 按键时刻 − 刺激 onset。条件表数值按要求**保持不变**，故各组窗口绝对时长较旧版各短 T。
- **漏答被误记为错误**：旧版 `response` 初值为 `NaN`，而 `isempty(NaN)` 恒为 false，
  使漏答落到 `strcmp` 分支被记成 `Correct = 0`（错误）。现改用 `isnan(response)` 判断，
  漏答记为 `Correct = NaN`；`Response` 列仍沿用 `char(NaN)` 写法（CSV 中为缺失/NA），与旧数据一致。
- **`checkEscape` 缺陷**：按 Esc 时 `sca` 关屏后脚本仍继续执行，后续 `Screen` 调用接连崩溃；
  现补 `error()` 干净终止。
- **弃用 KbQueue**：`v2` 的 KbQueue 方案在本机运行时"无法进入正式试次"（数据文件只有表头）。
  本次回到原版的 `KbCheck` 轮询方案（最小改动、零外部依赖）。
  ~~顺手加 `KbName('UnifyKeyNames')` 统一键名~~ → **这一行是错的，已在 v0.8 撤销，它才是真正的崩溃源**。
- 新增启动自检：`W <= T + 200 ms` 时直接报错（当前 9 组均满足；**组 1 掩蔽后仅剩 70 ms 可按键**）。

### 功能完善
- `maskDuration` 由试次循环内的局部常量提到文件开头，供自检与练习/正式两段循环共用。

### 文件变更
- 修改: `1_Code/Experiment/exp_matlab/Exp_Design_Formal.m`（外层唯一可运行程序）
- 归档: `Exp_Design_Formal_v2.m` → `test/Exp_Design_Formal_v2.m`；修改前的 v1 备份为 `test/Exp_Design_Formal_v1.m`
- 修改: `1_Code/Experiment/exp_matlab/主试培训手册_Exp_Design_Formal.md` → v1.2（同步时间轴、W 口径、主试话术与核对清单）
- 待办: 手册 Word 版 `主试培训手册_Exp_Design_Formal.docx` 尚未同步，需人工重导

### 验证
- `matlab -batch checkcode` 通过：0 语法错误，仅 4 条既有无害告警（`isTestMode` 死分支 + 3 条预分配提示）
- 用本机 MATLAB 实测"漏答 → 表格赋值 → fprintf → writetable"全链路：
  初值若写成 `''`（0×0 char）会**直接报错**（表格元素宽度不符），故最终保留 `NaN` 初值 + `isnan` 判据
- 未做真机 PTB 运行验证（需显示器与 GStreamer 运行环境）

### 注意（数据可比性）
- 新口径下 RT 下限 ≈ 0（抢按被如实记录），而旧版数据 RT 下限恒为 `T + 200 ms`
  → **新旧数据在 RT 下限上不可直接混用**；若需对齐，分析时按 `RT < T+200ms` 剔除抢按。
- `Correct` 列：旧数据把漏答记成 `0`（上述 bug），新数据记为 `NaN`。若下游脚本按 `Correct` 直接算正确率，
  请注意旧数据需先按 `RT` 缺失剔除漏答（现有 `exp_Check` 审计脚本本就如此处理，不受影响）。

---

## v0.6 (2026-09-27)

**责任人**：蔡振辛

### 新增功能
- **三维地形响应面配图**：新增 `1_Code/Animation_Manim/make_terrain_figures.py`，一键生成 6 张 4K 静态配图
  - `01_主图_W600_纯地形.png` — W = 600 ms 截面的三维响应曲面（起伏 1.78）
  - `02_主图_W600_叠加σ透明度.png` — 同一地形叠加 σ 透明度调制
  - `03_对比_W800_现用截面.png` — 对照现有视频用截面（起伏仅 0.42）
  - `04_真实拟合ℓ0.22.png` — ℓ 取项目真实拟合值附近
  - `05_标注版_观测点与高不确定区.png` — 标注 G3/G4 观测点与高 σ 区域
  - `06_侧视角_起伏轮廓.png` — 低视角突出峰谷
- 输出目录：`3_Figures/Animation/terrain_figures/`

### 关键分析结论
- **现有 S6/S7 热力图"缺乏视觉冲击力"的根因是截面选错，不是画法问题**。实测各截面曲面起伏（μ 极差，基准：6 个观测值极差 = 0.97）：

  | 截面 | ℓ=0.22 | ℓ=0.45 | ℓ=1.20 | 观测点数 |
  |:---|:---:|:---:|:---:|:---:|
  | **W = 600**（G3 −0.22 / G4 +0.75） | 1.35 | **1.78** | 1.85 | 2 |
  | W = 800（G7 +0.44 / G8 +0.38） | 0.45 | 0.42 | 1.50 | 2 |
  | W = 1100 | 0.72 | 1.15 | 0.88 | 1 |
  | W = 1500 | 0.69 | 0.73 | 0.48 | 1 |
  | (T,W) @ P=120 | 1.39 | 2.28 | 2.19 | 4 |

  W = 800 只有两个同号观测点，曲面在数学上就不可能起伏。
- **不得靠调大 ℓ 制造起伏**：ℓ = 1.2~1.5 虽然起伏更大（1.85），但 σ 反而更低（0.85），属于"自信的外推"，与 S6 已建立的"6 个点撑不起三维空间"矛盾。
- **解法**：面片不透明度按 σ 调制，高 σ 区域淡出成幽灵——既有冲击力又不失真。

### 性能实测
- 三维曲面构造：**3.8 s / 个**（52×42 = 2184 面片）
- 动画逐帧渲染：480p15 与 1080p60 **均为 0.45 s/帧** → 瓶颈是三维投影/几何计算，与分辨率无关
- 推论：渲染时间只跟帧数走，1080p60 下 1 秒视频 ≈ 27 秒渲染；单曲面无法逐帧重建，W 滑动需预计算切片后 `Transform`

### 问题修复（Manim API）
- `ManimColor` 不支持按 hex 切片取值 → 改用 `ManimColor.to_rgb()`
- 三维坐标轴本身会被曲面遮挡 → 改用 `Line3D` 画外沿包围盒线框；刻度值写进底部图例，避免 3D 标签与图例碰撞

### 文件变更
- 新增: `1_Code/Animation_Manim/make_terrain_figures.py`
- 新增: `3_Figures/Animation/terrain_figures/`（6 张 4K PNG）
- 说明: 主视频暂未改动，等待确认后再决定是否并入

---

## v0.5 (2026-09-27)

**责任人**：蔡振辛

### 新增功能
- **动画演示补齐后 5 幕**，形成完整 9 幕成片 `GP_Demo_1080p60.mp4`（约 4 分 19 秒）
  - **S4 核函数 length_scale**：滑杆连续拖动 ℓ（0.25 → 2.0），后验曲线束与 ±2σ 带实时重算
  - **S5 升维到三维**：在三维设计空间中切出 W = 800 ms 的 (P, T) 截面，再"潜入"截面切换为二维视图
  - **S6 真实数据接入**：以 6 组真实 SPE_v 为观测值的响应面热力图 + 真实 LOCV 限制说明
  - **S7 从拟合到决策**：同一截面把底色换成 σ 不确定度雾，标出高不确定区与真实 Top 候选点（P=0, T=500, W=300）
  - **S8 收尾**：(P,T,W) → Sigmoid 先验 → GP 残差 → DDM 参数 → 行为数据的架构图

### 功能完善
- `common.py` 新增工具：PTW 归一化、多维 RBF 核 GP 回归、响应面热力图、σ 不确定度雾、matplotlib 等值线提取、色标、真实 LOCV 指标读取
- `build_video.py` 场景列表扩展为 9 幕
- S3 结尾调整：σ 插图与标注在结论出现前淡出，使 S2→S3→S4 连续拼接无跳变
- S5→S6、S6→S7 的画面状态精确对齐，已逐帧验证拼接处一致

### 问题修复（Manim API 适配）
- `ImageMobject` 的 `width` / `height` 属性是**等比缩放**，无法分别对齐两个方向 → 改用 `stretch_to_fit_width` / `stretch_to_fit_height`
- `ImageMobject` 不是 VMobject，**不能放入 `VGroup`** → 改用 `Group`
- `add_fixed_orientation_mobjects` **必须逐个对象传入**；传 VGroup 会以整体中心定向，导致文字错位与倾斜
- `csv.DictReader` 读出的值都是字符串，格式化前必须转 `float`
- 渲染被中断会留下损坏的分片缓存，导致后续 `InvalidDataError` → 清理 `partial_movie_files` 后恢复（已写入 `build_video.py` 文档字符串）
- 成片时序核对不能用 `av` 的 `seek()`（定位不准）→ 改为顺序解码定位

### 学术诚信说明（重要）
- S5–S7 的响应面是**教学示范**：为让画面可读，把 GP 直接建在 SPE_v 上并取 ℓ = 0.45；项目正式模型拟合的是 **Sigmoid 预测的残差**，ℓ 由边际似然优化到 0.16 ~ 1.78。此说明已写入 S4 页脚、S6 结论以及 S6/S7 右下角脚注
- S4 的 ℓ 取值范围取自 `step4_gp_sigmoid_model_canonical4.pkl`，S7 的候选点取自 `step6_candidate_design_points.csv`，S6 的 LOCV 指标取自 `canonical4_summary.json`——均为项目真实结果，动画中无硬编码

### 文件变更
- 新增: `1_Code/Animation_Manim/scenes/s4_kernel_length_scale.py`、`s5_higher_dimension.py`、`s6_response_surface.py`、`s7_decision.py`、`s8_closing.py`
- 修改: `1_Code/Animation_Manim/common.py`、`build_video.py`、`scenes/s3_gp_posterior.py`
- 更新: `3_Figures/Animation/GP_Demo_1080p60.mp4`、`3_Figures/Animation/GP_Demo_preview480p.mp4`
- 更新: `.trae/documents/manim_gp_animation_design.md`

---

## v0.4 (2026-09-27)

**责任人**：蔡振辛

### 新增功能
- **Manim 动画演示系统**：用 3Blue1Brown 风格的动画讲解高斯过程（GP）在本项目中的角色，面向组会汇报，让人直观理解"数据稀疏 → GP 用不确定性回答未知区域 → 不确定性指导下一轮实验"这条主线
- 新增 `1_Code/Animation_Manim/`：
  - `common.py` — 共享模块（配色、中文字体、真实数据加载、手写 RBF 核 GP 数学）
  - `scenes/s0_title.py` — S0 开场标题与核心问题
  - `scenes/s1_design_space.py` — S1 三维设计空间散点（6 个真实条件 + 未测量区域）
  - `scenes/s2_gp_prior.py` — S2 GP 先验（一族函数 + ±2σ 不确定带）
  - `scenes/s3_gp_posterior.py` — S3 条件化后验（曲线束收窄 + σ(x) 插图）
  - `build_video.py` — 一键「渲染 4 幕 + 拼接为单视频」，支持 `--quick` 出 480p 预览
- 输出视频：`3_Figures/Animation/GP_Demo_1080p60.mp4`（约 2 分钟）与 `GP_Demo_preview480p.mp4`
- 新增独立渲染环境 `.venv-manim`（Python 3.12 + Manim Community 0.21.0），与项目主环境 `.venv`（3.14）隔离

### 功能完善
- 动画中的 6 个观测点直接读取 `2_Data/Generate_Data/GP_Sigmoid_Canonical4/input_conditions_g3g8_canonical4.csv`，与主线分析口径一致（G3–G8，G1/G2 因遗漏率过高已排除）
- 新增设计文档 `.trae/documents/manim_gp_animation_design.md`：含 9 幕完整分镜（MVP 4 幕 + 后续 5 幕）、数据接入方式、风险规避、验收标准与实施偏差记录
- S2 与 S3 的画面状态精确对齐，两幕拼接处无跳变

### 问题修复（环境适配）
- **LaTeX 不可用**：本机 TeX Live 2025 缺 `standalone.cls`，导致 MathTex 编译失败。改为全部使用 `Text` + Unicode（μ、σ、→）渲染
- **无需安装 ffmpeg**：确认 Manim 0.21 内置 PyAV 编码器，不再依赖外部 ffmpeg 二进制
- **视频拼接**：逐帧重编码会因时间基不匹配报 EINVAL；改用 concat 分离器做流拷贝（Manim 内部同款方案），无损且更快
- **渲染缓存损坏**：中断渲染会留下不完整的分片缓存，导致后续 `InvalidDataError`。清理 `media/videos/*/1080p60/partial_movie_files` 后恢复

### 文件变更
- 新增: `1_Code/Animation_Manim/`（`common.py`、`manim.cfg`、`build_video.py`、`scenes/s0_title.py`、`scenes/s1_design_space.py`、`scenes/s2_gp_prior.py`、`scenes/s3_gp_posterior.py`）
- 新增: `3_Figures/Animation/GP_Demo_1080p60.mp4`、`3_Figures/Animation/GP_Demo_preview480p.mp4`
- 新增: `.trae/documents/manim_gp_animation_design.md`
- 修改: `.gitignore`（新增忽略 `.venv-manim/` 与 `Animation_Manim/media/`）

---

## v0.3 (2026-05-26)

### 问题修复
- **修复 Screen.mexw64 加载失败 (找不到指定的模块)**：
  - 根因：`LexActivator.dll`（Psychtoolbox 许可证管理 DLL）缺失。该 DLL 是 Screen.mexw64、WaitSecs.mexw64、GetSecs.mexw64 等所有 MEX 文件的静态导入依赖
  - 原因：用户使用的 `Psychtoolbox-3-master` 是 GitHub 开发者源代码仓库，不含 `LexActivator.dll` 商业组件
  - 下载了 LexActivator-Win.zip (v3.31.2) 并提取 `LexActivator.dll` (vc14/x64) 至项目目录
  - 更新 `setup_paths.m` 为完整自动化配置脚本（5步：确认目录→安装DLL→添加路径→配置运行时→保存路径）

### 功能完善
- `setup_paths.m` 现在自动处理 LexActivator.dll 的安装（优先本地复制，备选网络下载 `downloadlexactivator`）
- 脚本自动运行 `PsychStartup` 将 PsychPlugins 目录添加到系统 PATH，确保 MEX 文件能找到运行时 DLL

### 文件变更
- 修改: `1_Code/Experiment/exp_matlab/setup_paths.m`
- 新增: `1_Code/Experiment/exp_matlab/LexActivator.dll`

---

## v0.2 (2026-05-26)

### 新增功能
- 创建 `setup_paths.m` 环境配置脚本：一键将 Psychtoolbox-3 添加到 MATLAB 搜索路径并持久化保存

### 问题修复
- 确认 `Screen` 报错根因：MATLAB R2023b (E:\matlab2023b) 已安装，Psychtoolbox-3 已下载至 `D:\学习\Coding Learning\Matlab\Psychtoolbox-3-master\`，但未加入 MATLAB 搜索路径
- 确认 Psychtoolbox MEX 文件完整：Screen.mexw64、PsychHID.mexw64、GetSecs.mexw64、WaitSecs.mexw64 等均存在

### 功能完善
- 提供一键配置脚本 `setup_paths.m`，用户首次使用时运行一次即可永久配置环境

### 文件变更
- 新建: `1_Code/Experiment/exp_matlab/setup_paths.m`

---

## v0.1 (2026-05-26)

### 新增功能
- 创建 `EXP_NEW.m`，基于 `experiment_formal_newcon.m` 重命名并修复后的正式实验脚本

### 问题修复
- **Psychtoolbox 缺失检测**：脚本开头新增 `exist('Screen', 'file')` 检查，若 Psychtoolbox-3 未安装或不在 MATLAB 路径中，给出明确的中文错误提示和安装指引
- **checkEscape() 函数缺陷修复**：原函数调用 `sca` 关闭窗口后脚本仍继续执行，导致后续 `Screen()` 调用全部崩溃。修复后增加 `error()` 终止脚本，干净退出实验

### 功能完善
- 保留原 `experiment_formal_newcon.m` 的 9 组实验条件（conditions 1-9），支持 groupID 1-9

### 文件变更
- 新建: `1_Code/Experiment/exp_matlab/EXP_NEW.m`

---
