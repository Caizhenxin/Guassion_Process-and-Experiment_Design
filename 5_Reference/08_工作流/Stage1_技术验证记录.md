# Stage 1 技术验证记录 — `Exp_Design_Formal.m` v4

日期：2026-10-14
状态：✅现行（**代码侧四条必修已全部落地并静态验证通过**；§6 的实机证据表待用户在实验机上跑完 N=2–3 技术试测后回填）
依据：`5_Reference/08_工作流/工作流_主计划.md` §3 Stage 1（L88–107）；`5_Reference/README.md` §五 第 5 条（W 语义陷阱）
权威性：本文件是 Stage 1 的唯一验证记录。程序行为一律以 `1_Code/Experiment/exp_matlab/Exp_Design_Formal.m`（v4，**1313 行**）为准，本文件的代码行号即指向该文件

> **行号口径（2026-10-18，D78）**：§2–§5 里的 `L…` 是按 **v4（1313 行）** 记的。现行程序是 **v4.4（1357 行）**——v4.2/v4.3 把「弹窗 + 校验 + 主试确认」抽成
> `exp_ask_subject_info.m`，v4.4 把逐试次容器从 `table()` 换成 cell（`exp_new_data.m` / `exp_data_table.m`），行号整体后移 40 余行。
> 因此**不要拿本文件的 `L…` 去数现行文件的行**：每处引用都附了原文代码串，用该串搜；行为判据以 `test/check_ask_info`、`test/check_data_accum`、
> `test/check_input_validation`、`test/check_manual_d4.py` 四条自测为准（见 §6 第 0 步）。

---

## 0. 一句话结论

Stage 1 的目的是**确保"记录到的时间戳"就是"真实发生的时间"**。v3 的程序有四处会破坏这一点：掩蔽纹理在刺激之后才读盘（把实际 T 拉长）、用 `KbCheck` 轮询（丢掉轮询间隙里的按键）、不记录真实 flip 时刻（无法知道名义 T 与实际 T 差多少）、以及输出列里没有 timeout / block 等判定字段。

⚠️ **开工时的一个发现**：D38(a) 那次「按 D4 重写程序」只改了条件表与试次结构，**Stage 1 的四项技术修正一项都没做**（唯一顺带完成的是第 4 项帧量化）。也就是说，上一轮交付的「1120 行版本」在计时口径上其实和旧版一样脆。本轮的 1120 → 1313 行才是 Stage 1 真正要求的改动。

v4 把四条全部改掉，并在同一轮里修掉两个**真实存在、实机必崩或必错**的缺陷：`FlipInv` 未定义变量、`char(NaN)` 写出的 NUL 字节。代码侧已通过三项静态检查（块结构、未定义标识符、25 列一致性）。

---

## 1. 改动总表

| # | Stage 1 要求 | 改动前 | 改动后 | 代码位置 | 静态验证 | 实机验证 |
|---|---|---|---|---|---|---|
| 1 | 掩蔽纹理预加载 | 每个试次内 `imread` + `Screen('MakeTexture')`（练习/正式各一处） | 开场一次性建好 10 张纹理句柄 + 矩形，试次内只 `Screen('DrawTexture')` | L280–302（预加载）；L596–607（练习用）、L924–935（正式用） | ✅ 全文 `imread` 只剩 2 处（L289/L297）、都在预加载块内 | ⏳ 见 §6-A |
| 2 | `KbCheck` → `KbQueue` | 三段 `while` 里高频 `KbCheck` 轮询 | 驱动侧事件队列，按键带**绝对 `GetSecs` 时间戳**入队 | L470–477（建队列）、L497/L823（每试次 flush）、`kqFirstPressUntil`（L1254） | ✅ 反应采集路径已无 `KbCheck`（只剩边界 `checkEscape` 与空格等待） | ⏳ 见 §6-B |
| 3 | 记录真实 flip 时间戳 | 无 | 每试次新增 5 个时间戳/时长列（21–25） | L610–614 记时刻、L685–694 写列（练习）；L938–942、L1014–1023（正式） | ✅ 两阶段列号均覆盖 1–25 | ⏳ 见 §6-C |
| 4 | 帧量化 | T/W 用名义值直接算帧数，未记录实际时长 | T/W 先按 `round(x/FlipIntv)` 量化；启动打印名义→帧→实际对照表；每试次记 `stimulus_frames` | L227–231（量化）、L265–278（对照表） | ✅ 静态核对通过 | ⏳ 见 §6-C |
| 额外 1 | 输出字段标准化 | 未响应写 `char(NaN)`（CSV 里是 NUL 字节） | `Response` 未响应写 `NA`；`Correct` 未响应写 `NaN` | L649–653（练习）、L977–981（正式） | ✅ 格式串 25 个占位符、与表头逐字一致 | ⏳ 见 §6-D |
| 额外 2 | 每试次 `responded_by_deadline`/`timeout`/`block`/`trial_index` | 无（`trial_index` 由原有 `trialID` 承担） | 新增 `block`、`timeout`、`responded_by_deadline` 三列 | L644–650（练习）、L972–978（正式） | ✅ 同上 | ⏳ 见 §6-D |
| 附带 | **未定义变量 `FlipInv`** | `T_levels`/`W_levels` 两行用了 `FlipInv`，而程序定义的是 `FlipIntv` | 统一为 `FlipIntv`，并把名义值抽成 `T_nominal`/`W_nominal` | L225–231 | ✅ **负向自测能抓到**（§5.2） | — |
| 附带 | 抢按计数 | 无 | 新增 `premature_press` 列（注视期就按 f/j） | L571–573（练习）、L899–901（正式） | ✅ 同上 | ⏳ 见 §6-B |

---

## 2. 逐项详述

### 2.1 修正 #1：掩蔽纹理预加载

**问题**。v3 在**每个试次内部**调用 `imread` + `Screen('MakeTexture')` 来准备掩蔽图。磁盘 I/O 的耗时不确定（首次读盘可能几毫秒到几十毫秒），而掩蔽的 `Screen('Flip')` 必须等它完成 ⇒ **实际刺激时长 = 名义 T + 不可预测的 I/O 抖动**。对 33.33 ms 这种只有 2 帧的条件，几十毫秒的抖动足以把 T 翻倍。

**改法**。在开场（`%% 联结阶段` 之前）一次性把 5 张 self + 5 张 stranger 掩蔽图读成纹理句柄，并预先算好各自的居中矩形；试次内只做 `DrawTexture`：

```matlab
selfMaskTex = zeros(1, numel(selfMaskImages));
selfMaskRect = cell(1, numel(selfMaskImages));
for i = 1:numel(selfMaskImages)
    im = imread(selfMaskImages{i});
    [mh, mw, ~] = size(im);
    selfMaskTex(i) = Screen('MakeTexture', window, im);
    selfMaskRect{i} = CenterRectOnPoint([0 0 mw mh], centerX, centerY + distance);
end
```

试次内（练习 L596–607、正式 L924–935）：

```matlab
if strcmp(currentLabel, 'stranger')
    maskIdx = randi(numel(strangerMaskTex));
    Screen('DrawTexture', window, strangerMaskTex(maskIdx), [], strangerMaskRect{maskIdx});
elseif strcmp(currentLabel, 'self')
    ...
end
maskFlipTime = Screen('Flip', window);
```

**改动前后对比**：单试次内的 `imread` + `MakeTexture` 调用次数 1 → 0；全文 `imread` 只剩 L289、L297 两处，都在开场预加载块内（各执行 5 次，共 10 张纹理）。

**备注**：程序结束时并未 `Screen('Close')` 这些纹理句柄（靠 L1139 附近的 `Screen('CloseAll')` 统一回收）。整场只建 10 张，不构成泄漏风险。

### 2.2 修正 #2：`KbQueue` 事件队列

**问题**。v3 用 `KbCheck` 在 `while` 里高频轮询。`KbCheck` 只回答"**此刻**是否有键按下"，两次轮询之间的按下—松开若完全落在间隙内就**永远读不到**。轮询周期受绘图/系统负载影响，典型 1–10 ms；对 200 ms 掩蔽段里 5 ms 的短按，丢失概率可达百分之几。丢掉的后果不是"RT 略偏大"，而是**整题变成漏答**。

**改法**。改用 PTB 的按键事件队列：驱动在按键发生的那一刻打上绝对时间戳并入队，`KbQueueCheck` 把"上次调用之后发生的全部按键 + 时间戳"一并交出。采集范围与 v3 相同（刺激期 / 掩蔽期 / 反应窗口），仍取**最早**的 f/j 按键。

建队列（L470–477，只建一次）：

```matlab
% ⚠ PTB 3.0.19 实测：KbQueueCreate 的 keyList 必须是【256 长度的 double 掩码】，
%   传键码短向量或 logical 都会报 "Usage:"
keysOfInterest = zeros(1, 256);
keysOfInterest([KbName('f'), KbName('j'), resolveEscKeyCode()]) = 1;
try, KbQueueRelease(); catch, end   % 防御：上次异常退出可能仍占用队列
KbQueueCreate([], keysOfInterest);
KbQueueStart();
```

每个试次开头清空（L495–497 / L821–823）：

```matlab
checkEscape();
KbQueueFlush();   % 丢弃本试次之前的历史按键；注视期抢按由 kqCountPresses 单独计数
```

三段采集（L570–641 / L898–969）：

| 段 | 代码 | 行为 |
|---|---|---|
| 刺激期 | `[respKey, respAbs, nEsc] = kqFirstPressUntil(stimulusFlipTime + T)` | 到点或首次 f/j 即返回；**这就是 D5 的"刺激期内按键即结束刺激"** |
| 掩蔽期 | `while GetSecs() - maskFlipTime < maskDuration; checkEscape(); WaitSecs(0.005); end` | **故意不读队列**（见下） |
| 反应窗口剩余 | `if isnan(responseTime); kqFirstPressUntil(stimulusFlipTime + W)` | 一次取走掩蔽期+空白期累积的全部按键 |

**为什么掩蔽段故意不读队列**。若在掩蔽结束这个"段边界"把队列读走，那么"在掩蔽最后几毫秒按下、但按定义属于反应窗口"的那次按键会被记到掩蔽段并被丢弃。改成不读，按键就留在队列里，由反应窗口段一次性取出；而每个事件都带**驱动时间戳**，所以它究竟发生在哪一段仍然可以还原（`RT = 时间戳 − stimulusFlipTime`）。这是"用时间戳代替分段"的做法，也是 `KbQueue` 相对 `KbCheck` 最本质的收益。

**为什么精度不受轮询频率影响**。`kqFirstPressUntil` 里每次循环都有 `WaitSecs(0.001)`：

```matlab
while GetSecs() < deadline
    [pressed, firstPress] = KbQueueCheck();
    if pressed
        [key, when, nEsc] = kqScan(firstPress, deadline, fCode, jCode, escCode);
        if nEsc > 0 || ~isempty(key), return; end
    end
    WaitSecs(0.001);
end
% 循环退出后【再补读一次】：兜住"刚好在 deadline 之前按下、上一次轮询还没看到"的按键
[pressed, firstPress] = KbQueueCheck();
if pressed, [key, when, nEsc] = kqScan(firstPress, deadline, fCode, jCode, escCode); end
```

`WaitSecs(0.001)` 只决定"多快**发现**按键"，`when` 是驱动记下的**按下瞬间**，所以 RT 分辨率不受 1 ms 轮询限制。补读那一次专门处理临界情形，且 `kqScan` 里用 `firstPress(idx(m)) <= deadline` 把晚于截止的按键排除掉。

**Esc 处理**。`checkEscape()` 保留 `KbCheck`（`KbCheck` 与 `KbQueue` 互不影响），扫描期与掩蔽期都保持 5 ms 一次的响应；队列里也注册了 Esc，`kqFirstPressUntil` 通过 `nEsc > 0` 把中止请求交回调用方，由 `escAbort()` 统一处理：

```matlab
function escAbort()
    disp('实验结束！');
    try, KbQueueRelease(); catch, end
    sca;
    error('实验已中止（按下了 Esc 键）。');
end
```

`resolveEscKeyCode()` 把 Esc 键码的解析抽成一处（`'esc'` → `'ESCAPE'` → `'escape'` 依次尝试，最终回退到物理键码 27），保证**队列掩码与 `checkEscape` 用的是同一个键码**——这正是 v2/v0.7 曾经栽跟头的地方（见文件头 L38–42 的警告：`KbName('UnifyKeyNames')` 绝不能开）。

**改动前后对比**：反应采集路径上 `KbCheck` 调用次数（每试次）13 → 0（只剩掩蔽段 40 次边界守卫和空格等待）；按键丢失机制从"依赖轮询周期"变为"驱动事件队列，不丢"。

### 2.3 修正 #3：真实 flip 时间戳与新输出列

**问题**。v3 只存了名义 `T`/`W` 和 RT，**没有任何一列能回答"刺激实际在屏多久"**。研究生计划 §8.4 把这一条列为验收关键：没有它就无法证明名义 T 与实际 T 的差在 1 帧以内。

**改法**。每试次在掩蔽 flip 之后记录（练习 L610–614、正式 L938–942）：

```matlab
maskOnsetActual      = maskFlipTime;   % 掩蔽（或空白）真正上屏的时刻
stimulusOffsetActual = maskFlipTime;   % 刺激离开屏幕的时刻 = 掩蔽 onset
stimulusDurActual    = stimulusOffsetActual - stimulusFlipTime;
stimulusFrames       = round(stimulusDurActual / FlipIntv);
```

**口径说明（易错点）**。本设计里刺激与掩蔽之间**没有空白帧**：刺激结束的下一帧就是掩蔽。所以 `stimulus_offset_actual ≡ mask_onset_actual`（M=0 时那次 flip 翻的是空白屏）。D5 生效时（刺激期内按键）刺激会立刻结束，此时 `stimulus_offset_actual` = "按键之后紧接着的那次 flip"，因此**它 ≥ RT**，而不是等于 T。

⇒ **验收口径必须是**：在没有刺激期内按键的试次上，判断 `|stimulus_dur_actual − T| < 1 帧`。有刺激期内按键的试次，`stimulus_dur_actual ≈ RT + 1 帧`，这是 D5 的设计后果、不是缺陷。

### 2.4 修正 #4：帧量化与实际时长记录

**问题**。60 Hz 下 T=30 ms ≈ 1.8 帧，`round` 成 2 帧 = 33.3 ms；名义值本身就不可实现。

**改法（①）**：T/W 从**名义值**量化到帧的整数倍。把名义值单独存起来，量化值与名义值的偏离可以在启动时直接打印：

```matlab
T_nominal = [33.33, 83.33, 149.99, 249.98];   % ms
W_nominal = [799.98, 1199.9, 1799.9];         % ms
T_levels = round(T_nominal / 1000 / FlipIntv) * FlipIntv;  % 2/5/9/15 帧
W_levels = round(W_nominal / 1000 / FlipIntv) * FlipIntv;  % 48/72/108 帧
```

启动时逐行打印（L265–280）：

```
── 帧量化核对（FlipIntv = 16.665556 ms，约 60.004 Hz）──
   T1：名义 33.33 ms → 2 帧 → 实际 33.331 ms（偏离 +0.001 ms = +0.00 帧）
   T2：名义 83.33 ms → 5 帧 → 实际 83.328 ms（偏离 −0.002 ms = −0.00 帧）
   ...
```

（上面的数值是 60.004 Hz 下的预期结果；实际数字以实验机打印为准，回填到 §6。）

**改法（②）**：无论名义值多准，真实呈现时长都受 `Screen('Flip')` 的垂直同步限制，所以**实际时长一律记录**（`stimulus_dur_actual` / `stimulus_frames`，见 §2.3）。这样即使换到 120 Hz 或投影仪上跑，事后也能把每个试次的真实 T 找回。

**顺带修掉的真缺陷**。量化这两行原文写成 `round(x / 1000 / FlipInv) * FlipInv`，而程序里定义的是 `FlipIntv`（L127）。**`FlipInv` 从未被赋值**，MATLAB 会在启动跑到这一行时抛 `Undefined function or variable 'FlipInv'`，程序根本进不了第一个试次。已改为 `FlipIntv`（L225–231），并新增静态检查器专门抓这类错误（§5.2）。

### 2.5 额外要求一：输出字段标准化

| 情形 | v3 写出 | v4 写出 |
|---|---|---|
| 未响应（`Response` 列） | `char(NaN)` = `char(0)` ⇒ **写入文件的是一个 NUL 字节** | 字面量 `NA` |
| 未响应（`Correct` 列） | `NaN`（`%d` 渲染为 `NaN`，可接受） | 不变，仍为 `NaN` |
| RT | 保持 NaN（`%.3f` 渲染为 `NaN`） | 不变 |

`char(NaN)` 在 MATLAB 里等于 `char(0)`，落到磁盘上是一个 `0x00` 字节。它不报错，但会让"按 T 分隔读表"的解析器在某些工具里无声错位——这类"看不出来"的脏数据比报错更危险，故一并改掉（L649–653 / L977–981）。

### 2.6 额外要求二：判定标记与抢按计数

```matlab
respondedByDeadline = double(~isnan(responseTime) && responseTime <= W);
timeout = double(~respondedByDeadline);
if ~respondedByDeadline
    response = NaN; responseTime = NaN;   % 截止之后的按键不算反应
end
```

`timeout = 1 ⇔ 到截止仍无有效按键`；`responded_by_deadline = 1 − timeout`。两者互为补集但是**显式写出的两列**，避免下游分析用 `RT > W` 这种容易写错的口径去反推。

`premature_press` 记录"刺激 onset 之前就按了 f/j"（对应 v2 的 `Premask`）。它不改变 RT 也不进入判定，但它是本任务里真实存在的现象（P 这个被试间因子就是为它设计的），没有它就无法在分析阶段区分"漏答"和"抢按之后放弃"。

---

## 3. 输出列（25 列）

| 列 | 名称 | 含义 |
|---|---|---|
| 1–16 | `groupID` … `Correct` | 与 v3 完全一致（`stage` 为 `practice`/`formal`，`trialID` 即 `trial_index`） |
| 17 | `block` | 1/2/3；练习阶段记 0 |
| 18 | `premature_press` | 1 = 注视期就按了 f/j |
| 19 | `timeout` | 1 = 到截止仍无有效按键 |
| 20 | `responded_by_deadline` | 1 = 截止前有效按键（= 1 − `timeout`） |
| 21 | `stimulus_onset_actual` | 刺激那次 `Flip` 的绝对 `GetSecs`（秒） |
| 22 | `stimulus_offset_actual` | 刺激离屏时刻的绝对 `GetSecs`（秒） |
| 23 | `mask_onset_actual` | 掩蔽/空白上屏时刻（M=1 与列 22 同值） |
| 24 | `stimulus_dur_actual` | 列 22 − 列 21（秒） |
| 25 | `stimulus_frames` | `round(列24 / FlipIntv)` |

写入格式串（两处一致，L720 / L1031）：

```matlab
'%d\t%d\t%d\t%d\t%d\t%s\t%d\t%d\t%.1f\t%.1f\t%s\t%s\t%s\t%s\t%.3f\t%d\t%d\t%d\t%d\t%d\t%.6f\t%.6f\t%.6f\t%.6f\t%d\n'
```

两个数据出口：`exp_group{g}_subject{s}.txt`（逐试次追加的长表，带表头）与 `EXP_data_group{g}_{s}.csv`（`writetable` 写出的宽表）。列名以 `columnNames`（L1126–1130）为准，二者一致。

---

## 4. 未改动的东西（明确声明）

- 条件表数值（P/T/W 水平）、试次数（练习 `P` 循环 + 正式 3×192）、平衡与打乱规则；
- W 的口径（`deadline = stimulusFlipTime + W`，见头注释 L18–22）与 RT 口径（按键时刻 − 刺激 onset）；
- 反馈逻辑（正确/错误/过快/过慢）与 500 ms 呈现；
- 联结阶段（60 s）与指导语文本。

⇒ v4 是**技术性修正**，不改变任何设计参数，因此不影响 D4 的设计结论与已有模拟结果。

---

## 5. 静态验证证据（本机可复现，无需 MATLAB）

三个检查器都在 `1_Code/DDM_Core/_scratch/`，命令行可重跑：

```powershell
cd 1_Code/DDM_Core
python _scratch/check_matlab_blocks.py        ..\Experiment\exp_matlab\Exp_Design_Formal.m
python _scratch/check_matlab_undefined.py     ..\Experiment\exp_matlab\Exp_Design_Formal.m
python _scratch/check_exp_design_columns.py   ..\Experiment\exp_matlab\Exp_Design_Formal.m
```

### 5.1 块结构

```
Exp_Design_Formal.m: 行数 = 1313
  未闭合的 function = 0
  ✅ 块结构平衡
```

### 5.2 未定义标识符（新增检查器）

```
文件行数 = 1313；已定义名字 204 个、函数 9 个
✅ 没有发现未定义的标识符
```

**负向自测**（证明这个检查器真的能抓到 §2.4 那个 `FlipInv` 缺陷）：把 `FlipIntv) * FlipIntv` 改回 `FlipInv) * FlipInv` 后重跑，

```
文件行数 = 1314；已定义名字 204 个、函数 9 个
❌ 共 1 个『被使用但未见赋值/定义』的标识符：
    L  229  FlipInv
```

⇒ 检查器有效，不是"看起来通过"。

### 5.3 25 列一致性

```
本地函数定义（9）：checkEscape, deg2pix, escAbort, getMatchKey, getPairingRules,
                  kqCountPresses, kqFirstPressUntil, kqScan, resolveEscKeyCode
  ✅ Stage 1 新增/改写的本地函数全部有定义
  ✅ 练习阶段列号：[1..25 全]
  ✅ 正式阶段列号：[1..25 全]
  ✅ columnNames 个数 = 25，与 25 列表头逐字一致
  ✅ fprintf(fileID) 占位符个数 = 25（两处）
```

**负向自测**（证明这个检查器真的能抓到表头不一致）：把 `columnNames` 里的 `'stimulus_frames'` 改成 `'stimulus_framesX'` 后重跑，
**只看第 25 列就报出来了**，不是"全表都对不上"：

```
    ✗ 第 25 列：表头 'stimulus_frames' vs columnNames 'stimulus_framesX'
  ❌ columnNames 25 个，表头 25 个
```

⇒ 检查器有效。换成删除/新增一个列名、或漏写 9 列中的任意一列，同样会被抓到（列号集合、列名列表、
占位符个数三条判据互相独立）。

---

## 6. 实机验证步骤（待用户在实验机执行并回填）

> 本机无 MATLAB / Psychtoolbox，以下四条**必须在实验机跑**。建议做成 N=2–3 名"技术被试"（只看程序不看数据），并保留 MATLAB 命令行窗口的完整输出。

> **先跑这条命令**（D67）：把实机产出的逐被试 `.txt` 直接喂给验收检查器，6-C/6-D 不必手算 ——
>
> ```
> python -X utf8 -u 1_Code\Experiment\exp_Check\check_stage1_acceptance.py <被试1.txt> <被试2.txt> ...
> ```
>
> 它逐条打印 `6-A`–`6-E` 的实测值（含 `stimulus_frames` 应有帧数、`max |ΔT| / FlipIntv`、`NA` 约定的违例行数、`0x00` 字节数、指定 T 档的 `T − max(RT)` 余量），末行给出「本机可判 4 项、需手测 2 项」。`6-A`（掩蔽纹理预加载）与 `6-E`（刺激内与刺激后按键的延时可比性）**不可机器判**，仍需人看。判据由 `1_Code/Experiment/exp_Check/check_stage1_acceptance.py::self_test` 的 6 个用例守住（干净数据 + 5 种人为缺陷，含「历史 16 列口径」被「0 口径」守卫拦住）。

### ★ 0. 程序自测（跑实验之前先做，约 35 s）

2026-10-18 主试在实验机填「组别 7」直接报错退出（D77），根因是**培训手册还是旧的 9 条件设计**、
而程序早已 D4。这类"文档与代码漂移"不会自己报错，只能靠对照。**跑实验之前先在实验机执行这六条**：

```bat
matlab -batch "cd('<仓库>\1_Code\Experiment\exp_matlab'); addpath('test'); check_ask_info"
matlab -batch "cd('<仓库>\1_Code\Experiment\exp_matlab'); addpath('test'); check_input_validation"
matlab -batch "cd('<仓库>\1_Code\Experiment\exp_matlab'); addpath('test'); check_data_accum"
matlab -batch "cd('<仓库>\1_Code\Experiment\exp_matlab'); addpath('test'); runbatch_full_session(1, 99)"
python -X utf8 1_Code\Experiment\exp_matlab\test\check_manual_d4.py
python -X utf8 1_Code\Experiment\exp_matlab\test\check_full_session.py
```

| 命令 | 期望末行 | 它守住什么 |
|---|---|---|
| `check_ask_info` | `通过 40 / 未通过 0` | 弹窗路径：填 7 ⇒ 弹「4 个 P 组速查」并**重填**；填 1 ⇒ 回显「本组 P = 0」；只有点取消才终止 |
| `check_input_validation` | `结果：51 通过 / 0 失败` | 五项校验的文案与边界（空/NaN/非整数/越界） |
| `check_data_accum` | `通过 33 / 未通过 0` | 数据累积与保存：`f` 之后写 `NA` 不崩（D78 的复现）、不等长标签无补齐空格、`data = table()` 等旧写法静态拦下、写 CSV 再读回逐列核对 |
| `check_manual_d4.py` | `共 40 项：通过 40 / 未通过 0` | 程序常量 / 手册 / Word 版 / 自测**四者口径一致**（4 组、576 试次、3 block、25 列） |
| `runbatch_full_session(1, 99)` | `SUMMARY pass=27 fail=0` | **整场冒烟**（D79）：用 24 个 PTB 桩在无屏幕环境跑完整场 576 试次，再把产物喂回 `read_formal_data.py`；B20–B23 专钉「刺激期内按键 = min(T, RT)」「无负 RT」「RT 与 responded_by_deadline 一致」 |
| `check_full_session.py` | `== 通过 29 / 未通过 0 ==` | 上面那次冒烟的**仓库侧**牙齿：程序里三处 v4.5 修正仍在、驱动判据仍在、两组日志 `pass=27 fail=0`、产物已回读通过；含 2 条反例自检，以及 D84 的 B27–B29（tFloor 契约测试三条牙齿） |

六条全过才动机器（另有一条**开发者回归** `check_kq_floor` 见下，不进现场纪律）。任一条 ❌ ⇒ 程序、校验/累积逻辑或手册之一被改过且没同步，**不得**开始正式采集
（`check_manual_d4.py` 会把不一致项逐条打出来，例如手册里还写着旧版的 520 试次／16 列）。

另：程序现在**不会再因组别填错而退出**。填错（越界/留空/非整数）会弹一个说明窗口，列出
「组1 P0 ｜ 组2 P8 ｜ 组3 P32 ｜ 组4 P120」，关掉后自动回到「实验信息」窗重填；填完还会回显
「groupID ⇒ 本组 P」让你核对，输错就输入 `r` 回车重来，不必 Ctrl+C 重开。

另（D78）：v4.3 的数据表用 `table()` 逐行累积，第一个**未响应**试次写 `NA` 就崩（`赋值右侧的值的宽度错误`），
2026-10-18 实机踩到；v4.4 改为 cell 累积 + 保存时 `cell2table`，由 `check_data_accum` 33/33 钉住。
另（D79）：v4.4 之前还把抢按当成反应（负 RT）、且逐试次 txt 通道从不 `fclose`；v4.5 修掉，
由「整场无屏幕冒烟」`runbatch_full_session` 27/27 + `check_full_session.py` 29/29 钉住。

另（D84）：v4.6 的修法只体现在一行 `> tFloor` 上，改回 `>=` 或删掉参数时**整场冒烟照样全绿**
（桩的按键时刻与铺助线无关）。因此补了一条**契约测试**，它不进现场六条、只在改程序后跑：

```bat
matlab -batch "cd('<仓库>\1_Code\Experiment\exp_matlab'); addpath('test'); check_kq_floor"
```

期望 `SUMMARY pass=10 fail=0`。它从 `Exp_Design_Formal.m` **原文抽取** `kqFirstPressUntil` / `kqScan` /
`resolveEscKeyCode` 再测（不复刻逻辑），十例覆盖：早于 onset 不返回、不传 floor 时必须返回（反向有牙）、
+1 ms 返回、恰等于 onset 不返回、恰等于 deadline 返回、晚于 deadline 不返回、两键取最早、无键则空、
Esc 只计数、早键被挡后窗口内后一键仍取到。结果同时落盘 `test/_kq_floor_result.txt`，由
`check_full_session.py` 的 B27–B29 复核。**坑**：桩目录必须用 `-begin` 压在 PTB 之前，
否则 `KbName('f')` 返回 70（PTB 口径）而不是桩的 6，`f/j` 永远匹配不上（首轮 5/10、只有 Esc 绿）。


### 设备前提（D81，**先看这一条**）

6-B/6-C/6-D 的每一条都依赖「这块屏是实验室那块 **60.004 Hz** 的屏」：

- 60.004 Hz ⇒ 帧长 16.6656 ms，T 的四个档位才正好是 **2 / 5 / 9 / 15 帧**（33.33 / 83.33 / 149.99 / 249.98 ms）；
- 换成 120 / 144 / 165 Hz 的屏，程序会按毫秒取整成别的帧数（本机 165 Hz 实测 5 / 14 / 25 / 41 帧），
  而每帧可用的绘制预算也从 16.67 ms 掉到 6.06 ms —— 2026-10-18 本机那一场就有 44/576 行刺激多停了 2–25 帧。

所以：**本机/笔记本上的数据只能证明「程序能跑通、能写出 25 列」**（连通性证据），
要回填下面的表，必须在实验室机上重跑一场。检查器会用 `--expect-hz`（默认 60.004）自动判这一层，
刷新率不符时打印「证据降级」而不是把数据判成缺陷。

### 6-A 掩蔽纹理预加载

1. 启动程序，确认命令行出现 `掩蔽纹理预加载完成：self 5 张、stranger 5 张（Stage 1 修正 #1）`；
2. 确认这一行出现在**联结阶段指导语之前**（即开场一次，而不是每个试次一次）。

| 证据项 | 期望 | 实测（回填） |
|---|---|---|
| 预加载回显出现且只出现一次 | ✅ | ✅ **2026-10-18，v4.6，控制台亲见**：`掩蔽纹理预加载完成：self 5 张、stranger 5 张（Stage 1 修正 #1）`。该行是 `Exp_Design_Formal.m:365` 的 `fprintf`，位于**开场的一次性预加载段**（`:344-368`，两个 `for` 之后、联结阶段指导语之前），不在任何试次循环里 ⇒ 每次启动只打印一次 |
| 首个试次之前没有 `imread` 报错 | ✅ | ✅ 该场 576 个正式试次跑完并正常落盘（`EXP_data_group1_99.csv`），过程中未出现 `imread` / `Screen('MakeTexture')` 报错——这类错误会直接中止程序 |

### 6-B `KbQueue` 能记录刺激期按键

在刺激呈现期内（尤其是 T=33.33 ms 的 2 帧条件）按键，检查：

| 证据项 | 期望 | 实测（回填） |
|---|---|---|
| T=33.33 ms 单元里 `Response` 为 `f`/`j`（不是 `NA`） | 至少 1 例 | **15 例**（2026-10-18 **v4.6**，59.988 Hz 屏，组 2，576 试次）；v4.5 那场 19 例 |
| 该行 `RT` < 0.0333 | ✅ | ✅ v4.6 15/15、v4.5 19/19，全部 < 0.0333 |
| 注视期抢按被记为 `premature_press = 1`，且**不**影响该试次 RT | ✅ | ✅ v4.5 431 行、**v4.6 502 行** `premature_press = 1`；有 RT 的行 **全部为正**（无负值） |
| 掩蔽期内按键仍被记录（`RT` 落在 T ~ T+200 ms 之间） | ✅ | ✅ v4.5 142 例、**v4.6 225 例**（含 T 档内 0.033–0.45 s 全区间） |
| `responded_by_deadline` / `timeout` 两列互补、无第三态 | ✅ | ✅ v4.5：135 / 441；**v4.6：41 / 535**；两场和都 = 576，无第三态 |

### 6-C 实际 T 与名义 T 的差 < 1 帧（**核心验收项**）

对**没有刺激期内按键**的试次（`RT` 为 NaN 或 `RT > T`），逐行算：

> **判据口径（D81 订正）**：程序写进第 25 列的是 `round(stimulus_dur_actual / FlipIntv)`，
> 而实际在屏时长本来就允许比名义 T **多 0~1 帧**（vsync 余量，见 §7 第 2 条）。原先这里写
> `|dur − T| < 1 帧` 是**错的口径**：它把 88% 的正常行判死。正确的三条是

```
−0.5 ≤ (stimulus_dur_actual − T) / FlipIntv < 1.5      （下界防刺激被截断，上界 = 1 帧余量 + 半帧容差）
stimulus_frames == round(stimulus_dur_actual / FlipIntv)
stimulus_offset_actual == mask_onset_actual
mask_onset_actual == stimulus_onset_actual + stimulus_dur_actual   （容差 1e-5 秒，秒级浮点尘土是 ±1e-6）
```

| 证据项 | 期望 | 实测（回填） |
|---|---|---|
| 启动打印的帧量化对照表 | 每个 T/W 偏离名义 ≤ 1 帧 | ✅ **v4.6 / 59.988 Hz**：T = 33.331 / 83.328 / 149.990 / 249.984 ms（**2/5/9/15 帧**），偏离 ≤ **0.005 ms**；W = 799.948 / 1199.922 / 1799.882 ms（48/72/108 帧）。（v4.5 那场 59.111 Hz：T = 33.83 / 84.59 / 152.26 / 253.76 ms，偏离 ≤ 4.3 ms） |
| 全部无刺激期按键试次的 `stimulus_frames` | 分别 ≈ 2 / 5 / 9 / 15（±1 帧） | ✅ **v4.6：341 行全部落在 2 / 5 / 9 / 15**（v4.5：297 行里 291 行落位，另 5 行抢按截断） |
| `max (stimulus_dur_actual − T) / FlipIntv` | ∈ [−0.5, +1.5) | ✅ **v4.6：0 行越界**，341 行 ∈ [+0.06, +0.51] 帧（vsync 余量）。（v4.5 那场曾有 5 行越界：−1.37 / −1.61 / −4.35 / −13.95 / −14.15 帧，已由 v4.6 的 `tFloor` 收口） |
| `stimulus_offset_actual − mask_onset_actual` 恒为 0 | ✅ | ✅ 576/576（容差 1e-5） |
| `mask_onset_actual − stimulus_onset_actual − stimulus_dur_actual` 恒为 0 | ✅ | ✅ 576/576（容差 1e-5 秒） |

> ✅ **已收口（D87，2026-10-18）**：同一判据在 v4.6 那一场（576 试次）上 **0 行越界**，`frames == round(dur/FlipIntv)` 全部成立，
> 说明 v4.6 的 `tFloor` 修法把「onset 之前的键」彻底挡在反应窗口之外。下面这段是当时（v4.5）的现场记录，保留备查：
>
> ⚠ **6-C 的 5 行越界（D83）**：这 5 行 `stimulus_dur_actual` 只有 0–1 帧、`premature_press = 1`、
> `Response = NA`、`timeout = 1`。根因不是显示卡顿，而是**注视末梢的键落进了反应窗口**——
> 注视期抢按在 `kqCountPresses()`（`Exp_Design_Formal.m:964`）处读取，该点距真正 onset 隔着一次
> `Screen('Flip')` 的 vsync 等待；这条缝隙里按下的第二个键不会进抢按计数，却被刺激期的
> `kqFirstPressUntil` 立刻取走，于是刺激在 0–1 帧内被敲掉、试次变成漏答。
> **v4.6 已修**（`kqFirstPressUntil(deadline, tFloor)`，四个调用点传 `stimulusFlipTime`），
> 但这 5 行是 **v4.5 产物**：按「不改判据去迁就数据」的原则，6-C 仍记为 ❌，
> 待 v4.6 在实验室机复跑一场后重判（预计 297 行全部 ∈ [−0.5, +1.5) 帧）。


### 6-D 输出列与缺失值

| 证据项 | 期望 | 实测（回填） |
|---|---|---|
| `.txt` 首行表头为 25 个列名、与 §3 一致 | ✅ | ✅ 与 `HEADER25` 逐字一致 |
| 漏答行的 `Response` 是 `NA`（不是空、不是 `0`） | ✅ | ✅ v4.5：135 行；**v4.6：41 行**，全部为 `NA` |
| 漏答行的 `Correct` 是 `NaN`、`timeout = 1`、`responded_by_deadline = 0` | ✅ | ✅ v4.5 135/135、**v4.6 41/41** |
| 练习行 `block = 0`，正式行 `block ∈ {1,2,3}` | ✅ | ✅ 两场均无练习行（CSV 只落正式段）；正式 `block` 1/2/3 各 192 |
| 用十六进制查看器搜不到 `0x00` 字节 | ✅ | ✅ 0 个 |

### 6-E 刺激内与刺激后按键的延时可比性

**口径**：`RT` 取自 `KbQueue` 的硬件时间戳，与「程序什么时候把键取走」无关；但**刺激被敲掉的时间**
（`stimulus_dur_actual`）就是「程序发现这个键」的时刻。所以可比性唯一可检验的形式是：

```
刺激内按键：0 ≤ stimulus_dur_actual − RT ≤ 1 帧        （发现延时不超过一次 vsync 等待）
刺激后按键：dur ≈ T，RT 可远大于 T                    （两者解耦，RT 不被掩蔽期"不读队列"污染）
```

工具：`1_Code/Experiment/exp_Check/check_6e_latency.py`（零依赖、只读；`--self-test` 3/3：
干净场通过、把延时改成 2.5 帧必须判红、只有刺激后按键时必须判"不可判"）。

| 证据项 | 期望 | 实测（回填） |
|---|---|---|
| 刺激内按键的检测延时 `stimulus_dur_actual − RT` | ≤ 1 帧（16.7 ms） | ✅ **235 例：1.6–16.6 ms**（v4.6 那场，组 2，576 试次；另一场截断的第 2 组 4 例：3.1–5.4 ms） |
| 刺激后按键的 `RT` 与 `dur` 解耦 | `dur ≈ T`，`RT` 可远大于 T | ✅ 300 例：落在掩蔽窗内 **225 例**（`RT−T` 2.1–199.0 ms）、掩蔽后 **75 例**（最大 1651 ms） |
| 两种路径用的是同一套取键逻辑 | 同一函数、同一时间戳源 | ✅ v4.6 起两条路径都走 `kqFirstPressUntil(deadline, tFloor)`（`Exp_Design_Formal.m:996` / `:1047`） |

> ⚠ 分析层（不属于本条判据）：这场有 **90 例 `RT < 50 ms`**（预期性/连按）。它们会被 S6-5 的"过快"条
> 与分析阶段的 `RT` 下限处理，不影响「记录延时」这一结论。

---

## 7. 遗留与未做

1. **`responded_by_deadline` 的边界**：判定用 `responseTime <= W`，而 RT 本身是"按键时刻 − 刺激 onset"。若按键恰好落在截止后 1 帧内，会被判为 `timeout`。这是**有意**的口径（宁可算漏答也不把超窗按键当反应），但分析阶段若要区分"严格漏答"与"临界超窗"，需要额外一列记录被丢弃按键的时间戳——目前**未实现**，若 Stage 6 预试显示临界情形常见，再补。
2. **刺激期结束的粒度**：D5 下"刺激期内按键即结束刺激"，但真正离屏要等下一次 vsync，因此 `stimulus_dur_actual ≈ RT + (0~1) 帧`。这是显示硬件的物理限制，只能记录、不能消除。
3. **`stimuliFrames` 预绘图循环**（L540 / L867）：把同一张刺激画 `round(T/FlipIntv)` 遍再 `Flip` 一次。实际控制时长的是 `GetSecs` 轮询而不是这个循环，所以它不产生错误，只是**多余**（每试次多若干次绘图调用）。为了让 diff 最小，本轮**未改动**；若实机发现 Flip 时机偏晚，这是第一个该动的地方。
4. **`waitForSpace` 与 `checkEscape` 仍是 `KbCheck` 忙等**：这些路径与反应采集无关，不影响数据质量，故未改成队列。
5. **实机证据空缺**：§6 中 `6-B` / `6-C` / `6-D` 已按 **v4.6 那场**（2026-10-18，59.988 Hz，组 2，576 试次）逐项回填（D87），**六张表已齐**：`6-A` 于 D88 回填（控制台确认）、`6-B`–`6-D` 于 D87 按 v4.6 那场回填、`6-E` 于 D89 回填（`check_6e_latency.py` 判）。这是本文件目前唯一的缺口，也是 Stage 1 是否算"完成"的唯一判据。**已缩窄（D67）**：`6-B`–`6-D` 改由 `1_Code/Experiment/exp_Check/check_stage1_acceptance.py` 机器判定（自测 5/5），人手只剩 `6-A` 与 `6-E` 两行 —— 但**这两行不填，Stage 1 仍然不算完成**。
6. **程序/手册的版本一致性**（D77 新增）：程序改了设计而手册没同步，症状是主试被弹窗拒绝或按旧口径操作——**代码侧任何回归测试都发现不了**。已由 `1_Code/Experiment/exp_matlab/test/check_manual_d4.py`（40/40，程序常量 vs 手册 vs Word 版 vs 自测）守住，但它只覆盖写死的几项（4 组 / 576 试次 / 3 block / 25 列 / 四档 T / 三档 W）；**新增输出列或改组数时必须手工改该检查器**，否则它会静默放行。


---

## 附：v4 改动涉及的代码锚点

| 位置 | 内容 |
|---|---|
| L23–57 | 头注释新增 v4 段：三项修正 + 25 列口径 |
| L127 | `FlipIntv = Screen('GetFlipInterval', window)` |
| L225–231 | 名义值 `T_nominal`/`W_nominal` + 帧量化（修掉 `FlipInv`） |
| L265–278 | 启动帧量化对照表打印 |
| L280–302 | 掩蔽纹理预加载（修正 #1） |
| L457–458 | `.txt` 表头改为 25 列 |
| L470–477 | KbQueue 建立（修正 #2） |
| L495–497 / L821–823 | 每试次 `KbQueueFlush` |
| L571–573 / L899–901 | `premature_press` 计数 |
| L584 / L912 | 刺激期 `kqFirstPressUntil` |
| L596–607 / L924–935 | 掩蔽绘制与 Flip（修正 #1 的试次内用法） |
| L615–620 / L943–948 | 掩蔽段：不读队列，只守 Esc |
| L635 / L963 | 反应窗口剩余段 `kqFirstPressUntil` |
| L644–650 / L972–978 | `timeout` / `responded_by_deadline` 判定 |
| L649–653 / L977–981 | `Response` 缺失值写 `NA` |
| L685–694 / L1014–1023 | 新增 9 列写入 |
| L720–728 / L1031–1039 | 25 列 `fprintf` |
| L1126–1130 | `columnNames`（25 个） |
| L1139 | `KbQueueRelease` |
| L1190–1313 | 新函数：`resolveEscKeyCode` / `escAbort` / `checkEscape` / `kqCountPresses` / `kqFirstPressUntil` / `kqScan` |
