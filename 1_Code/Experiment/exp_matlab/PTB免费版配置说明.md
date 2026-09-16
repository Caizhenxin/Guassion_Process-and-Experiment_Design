# Psychtoolbox 免费版配置说明（本机已完成）

> 适用程序：`Exp_Design_Formal.m`（本目录）
> 状态：**已配置并验证通过**（2026-09-02）
> 结论：本机现使用 **PTB 3.0.19.16 免费版**，**不需要任何许可证**，`Screen` 已验证可正常加载。

---

## 1. 为什么是"免费版"

Psychtoolbox 的许可机制时间线（官方文档 [psychtoolbox.org/download](https://psychtoolbox.org/download)、[版本说明](https://psychtoolbox.org/versions)）：

| 版本 | Windows/macOS 是否需要付费 | 说明 |
|---|---|---|
| ≤ **3.0.19.16**（2024-12-14 发布） | **完全免费** | **官方原话：最后一个在 Windows/macOS 上免费使用的版本**；本机用的就是它 |
| ≥ 3.0.20 | 需要许可证 | 首次使用后 **免费 14 天**，之后需订阅（单机版早期优惠 50 欧/年）；按机器（node）锁定 |
| Linux 版 | 免费 | 官方称 Linux 版本继续免费 |

LICENSE 层面：PTB 源码与 3.0.19.16 的预编译 mex 均为自由许可（GPL/MIT 混合），**在 Windows 上免费使用 3.0.19.16 完全合规**。

> 备选免费路线（本机未采用）：Linux + Octave 免费变体。自编译 Windows 版不解决许可证问题（许可证代码在源码中由平台宏控制，Windows 构建默认包含），因此不建议。

---

## 2. 本机已完成的改动（可复现清单）

1. **下载免费版**：`3.0.19.16.zip`（76.7 MB，官方 GitHub Release 资源，经可达镜像 `ghproxy.net` 获取；github.com 本机不可达）。
   已归档至：`D:\学习\Coding Learning\Matlab\installers\Psychtoolbox-3.0.19.16.zip`
2. **解压安装**：`D:\学习\Coding Learning\Matlab\Psychtoolbox-3.0.19.16\Psychtoolbox`
   Windows mex 位于其子目录 `PsychBasic\MatlabWindowsFilesR2007a\`。
3. **运行 `SetupPsychtoolbox(1)`** 完成路径安装（该版本**没有** `PsychLicenseHandling`，无任何许可证检查）。
4. **屏幕 mex 使用轻量版**：本机未安装 GStreamer，完整版 `Screen.mexw64` 会因缺少 `glib-2.0-0.dll` 等报"MEX 文件无效：找不到指定的模块"。
   因此把同目录下的 `ScreenLight.mexw64`（无 GStreamer 依赖）复制为 `Screen.mexw64`：
   - 原文件已备份为 `Screen.mexw64.full.bak`
   - 本实验只用基础绘图/文字/纹理/Flip，轻量版功能足够
5. **项目脚本已切换**：`setup_paths.m` 已改写为指向免费版（并自动清理旧的 3.0.20+ 路径），原脚本另存为 `setup_paths_licensed_master.m`。
6. **新增切换助手**：`ptb_switch_screen.m`（`'light'` / `'full'` / `'status'`）。
7. 另存有 GStreamer 安装包（可选升级用）：`D:\学习\Coding Learning\Matlab\installers\gstreamer-1.0-msvc-x86_64-1.22.12.msi`（127 MB，官方免费）。
8. 3.0.20+ 的 master 版仍保留在 `D:\学习\Coding Learning\Matlab\Psychtoolbox-3-master`（其 `Screen.mexw64` 已还原为原始完整版，需许可证，暂不使用）。

---

## 3. 日常使用（每台用于采集的电脑只需做一次）

在 MATLAB 中：

```matlab
cd 'D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\1_Code\Experiment\exp_matlab'
setup_paths          % 配置/自检 PTB（首次运行一次即可，脚本会自动 savepath）
Exp_Design_Formal    % 开始正式实验
```

`setup_paths` 正常输出应为：

```
[2/5] 免费版确认：该版本不含许可证管理，可长期免费使用。
[3/5] 路径已更新（mex 目录已置顶: ...\MatlabWindowsFilesR2007a）。
[5/5] 已保存：下次启动 MATLAB 无需重复配置。
PsychtoolboxVersion: 3.0.19 - Flavor: Manual Install, ...
Screen 加载成功 —— 环境就绪，可以运行 Exp_Design_Formal。
```

> 若 `PsychtoolboxVersion` 显示 3.0.2x（即收费版），说明 MATLAB 路径里还有 master 版；重新运行 `setup_paths` 即可（脚本会清除旧路径）。

---

## 4. 可选升级：安装 GStreamer，用回完整版 Screen

轻量版不支持视频类功能；本实验不需要，但若想恢复完整版：

1. 双击运行 `D:\学习\Coding Learning\Matlab\installers\gstreamer-1.0-msvc-x86_64-1.22.12.msi`（**需要管理员权限**；安装时选择 Complete/全部组件）。
2. 重启 MATLAB，然后：

```matlab
cd 'D:\...\1_Code\Experiment\exp_matlab'
ptb_switch_screen('full')   % 还原完整版 Screen.mexw64
setup_paths                 % 重新自检
```

安装包与版本对照（官方要求 GStreamer 1.22.5 MSVC 或更新；1.22.12 满足且是现存的 1.22.x 版本）。

---

## 5. 如果将来想用 3.0.21+ / 需要订阅（或先试用）

```matlab
% 需要 3.0.20+ 版本时（master 版）：
P = 'D:\学习\Coding Learning\Matlab\Psychtoolbox-3-master\Psychtoolbox';
run(fullfile('D:\...\1_Code\Experiment\exp_matlab','setup_paths_licensed_master.m'));  % 切回收费版路径
PsychLicenseHandling('Setup')    % 同意启用许可证管理 → 直接回车 = 启用 14 天免费试用
PsychLicenseHandling('IsLicensed')  % 查看状态（1 = 已授权）
```

- 试用期为**首次使用后 14 天**，到期后 `Screen` 会直接拒绝运行；
- 订阅：单机 50 欧/年（早期优惠价），官网 https://www.psychtoolbox.net ；
- 许可证按"机器+操作系统"锁定，换机需先 `PsychLicenseHandling('Deactivate')` 释放。

**本项目的建议**：9 条件 × ≥20 人 ≈ 180 人次、跨数周的采集期，**继续使用 3.0.19.16 免费版**最稳妥（无到期风险）。

---

## 6. 排障速查

| 现象 | 原因 | 处理 |
|---|---|---|
| `MEX 文件 ... Screen.mexw64 无效: 找不到指定的模块` | 完整版 Screen 缺 GStreamer（`glib-2.0-0.dll` 等） | `ptb_switch_screen('light')`，或安装 GStreamer 后 `ptb_switch_screen('full')` |
| `Missing or dysfunctional Psychtoolbox Mex file` | MATLAB 路径顺序错误（`PsychBasic` 排在 `MatlabWindowsFilesR2007a` 之前） | 重新运行 `setup_paths`（脚本会把 mex 目录置顶） |
| `This Psychtoolbox function is currently not licensed` | 用的是 3.0.20+ 版本且未激活 | 改用免费版路径（`setup_paths`），或 `PsychLicenseHandling('Setup')` |
| `PsychStartup: GStreamer ... not installed` | 未装 GStreamer（正常） | 忽略；轻量版无需 GStreamer。要完整版则装 MSI |
| `PsychtoolboxVersion` 显示 3.0.2x | 路径里挂的是 master 收费版 | 运行 `setup_paths` 切回免费版 |
| **`错误使用 Screen / See error message printed above.`（报错行 = `Screen('OpenWindow',…)`）** | **PTB 同步测试（SkipSyncTests=0）失败**：上方会打印 `WARNING: Couldn't compute a reliable estimate of monitor refresh interval` + `----- ! PTB - ERROR: SYNCHRONIZATION FAILURE ! -----` | 见下方 §6.1；v2 已内置自动回退 |
| 每次运行 `PsychtoolboxVersion`/开窗都提示 Windows 11 不受支持 | PTB 3.0.19（2023 构建）未列入 Win11 支持 | 仅提示；配合 `SkipSyncTests=1` 可正常采集，但时序需自行核验 |

### 6.1 `Screen('OpenWindow')` 报 "SYNCHRONIZATION FAILURE"（本机已复现）

**现象**：第 52 行 `Screen('Preference',…)` 正常，第 153 行 `Screen('OpenWindow',…)` 报
`错误使用 Screen / See error message printed above.`；上方原文为 VBL 同步测量失败。

**实测结论（本机，2026-09-16）**：这台笔记本（Windows 11 + DWM + 双屏 165Hz + RTX 4060 Laptop）的
**VBL 同步测试结果不稳定**——同一命令在几分钟内出现过"失败"与"通过"两种结果：

| 测试 | 结果 |
|---|---|
| screen 0/1/2 × {全屏,小窗口} × `SkipSyncTests=1` | 全部 OK（开窗本身没问题） |
| screen 2 全屏 × `SkipSyncTests=0` | **FAIL（SYNCHRONIZATION FAILURE）** |
| 同一命令再次运行 | 有时又 OK（不稳定） |
| 同步失败后立即用 `SkipSyncTests=1` 重开 | OK，`GetFlipInterval = 6.061 ms`（165 Hz）|

**处理**：
1. `Exp_Design_Formal_v2.m` 保持与 v1 相同的 `SkipSyncTests = 0` 设置；**仅当开窗因此报错时**，
   会自动打印真实原因并改用 `SkipSyncTests = 1` 重试一次，随后继续实验（不再直接中断）。
   如需确定性跳过，可在该文件顶部把 `Screen('Preference', 'SkipSyncTests', 0)` 改为 `1`。
2. 在显示配置规范的采集机上无需任何改动（同步测试通过时 v2 行为与 v1 完全一致）。
3. 诊断脚本：`test/ptb_window_diagnostic.m` —— 逐屏幕 × 逐设置试开窗口并输出日志
   `test/ptb_window_diagnostic_log.txt`（含屏幕分辨率/刷新率、OpenGL 渲染器、每步成败与错误原文）。
4. 采集前检查：关闭录屏/投屏/其它全屏程序；多屏 + DPI 不一致时 PTB 容易失败；必要时只保留刺激屏
   （Win+P → 仅电脑屏幕）。
5. **时序注意**：一旦用到跳过同步测试的兜底路径，说明本机显示时序未经验证。若论文对刺激呈现/RT 精度
   要求高，请用外部设备（光电二极管）核验，或在方法中说明 `SkipSyncTests` 取值与实测 `FlipInterval`。

---

## 7. 相关文件

| 文件 | 作用 |
|---|---|
| `setup_paths.m` | 配置免费版 PTB（清理旧路径 + mex 置顶 + 自检） |
| `setup_paths_licensed_master.m` | 原脚本（指向 3.0.20+ 收费版，需许可证） |
| `ptb_switch_screen.m` | 完整版/轻量版 Screen 一键切换 |
| `Exp_Design_Formal.m` | 正式实验程序（9 条件：8 掩蔽 + 组7 无掩蔽） |
| `主试培训手册_Exp_Design_Formal.md` / `.docx` | 主试培训手册 |
| `automation/md_to_docx.py` | 手册 Markdown → Word 转换脚本 |
| `automation/pe_deps.py` | PE 依赖分析工具（排查 mex 缺 DLL 用） |
