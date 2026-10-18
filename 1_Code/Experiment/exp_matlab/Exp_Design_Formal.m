%% Exp_Design_Formal.m
% 自我-联结匹配任务 (Self-Matching Task, 参照 Sui et al., 2012) 正式数据采集程序
% -----------------------------------------------------------------------------
% 用途  ：D4 设计（v4）——P 被试间 4 组 × 每组 ~40 名被试；T×W 被试内全交叉
%         每人 12 个 (T,W) 单元 × 4 类刺激 × 12 次 = 576 试次（3 个 block，每块一个 W）
%         P ∈ {0,8,32,120}；T ∈ {33.33,83.33,149.99,249.98} ms；W ∈ {799.98,1199.9,1799.9} ms
%         （旧版为 9 条手挑条件、每人只跑一行；本次按 D38 决议改为以 D4 为准）
% 沿革（相对 experiment_formal_newcon.m 的改动，保留）：
%   (1) conditions 表增加第 4 列 M（掩蔽开关）：M=1 呈现 200ms 掩蔽图；M=0 掩蔽段翻空白屏 200ms
%   (2) 旧版的"组7=无掩蔽"应急条件在 v4/D4 中已废除：D4 只有 4 个 P 组，12 个
%       (T,W) 单元全部带掩蔽（见下方"组别速查"与 v4 段）
%   (3) 程序开头增加主试确认回显，防止填错组别/编号
%
% ★★ v3 本次两处修正（其余逻辑、条件表数值、试次数、平衡规则一律未改）★★
%   (A) 按键采集范围：自【刺激 onset】起全程轮询键盘。
%       旧版只在"掩蔽结束后的空白屏"里用 KbCheck 轮询，刺激呈现期(T)与掩蔽期(200ms)的按键
%       根本不会被读取 → 被试在刺激还在时按键会整题丢失（表现为漏答或 RT 偏大）。
%       本版在 刺激期 / 掩蔽期 / 反应窗口 三段都轮询，取最早的 f/j 按键作为反应。
%   (B) W 的定义：W = 【从刺激 onset 起算】到最晚可反应时刻的时长，deadline = stimulusFlipTime + W
%       （旧版误为 onset + T + W，相当于"从刺激结束起算"）。RT 口径不变 = 按键时刻 − 刺激 onset。
%       单个试次时间轴：注视500 → 刺激 T(采集按键) → 掩蔽/空白 200(采集按键)
%                       → 空白至 onset+W(采集按键) → 反馈 500
%       约束：W 必须 > T + 200ms（已加启动自检），掩蔽之后真正可按键时长 = W − T − 200ms
%   (C) 附带修正：漏答时 Correct 记为 NaN。旧版用 isempty(response) 判断，而 response 初值为
%       NaN 时 isempty 恒为 false，于是漏答落到 strcmp 分支被误记成 0=错误；现改用 isnan(response)。
%       （v4 起 Response 列缺失值写 'NA'，不再用 char(NaN)；Correct 缺失仍写 NaN）
%
% ★★ v4 本次修正（Stage 1 技术验证，必修 #1/#2/#3；逻辑与条件表数值一律未改）★★
%   (#1) 掩蔽纹理预加载：旧版在【每个试次内】imread + MakeTexture，磁盘 I/O 会让掩蔽那次 Flip
%        晚于名义时刻 ⇒ 实际 T 长于名义 T。现改为开场一次性建好全部 10 张纹理与矩形。
%   (#2) 按键采集改 KbQueue 事件队列：旧版 KbCheck 高频轮询会把轮询间隙里的短按键整段丢掉
%        （假遗漏）。KbQueue 由驱动在按键【发生的那一刻】打绝对 GetSecs 时间戳并排队，
%        所以轮询再慢也不丢事件，RT 精度也不再受轮询频率限制。
%        采集范围不变（刺激期 / 掩蔽期 / 反应窗口），仍取最早的 f/j 按键作为反应。
%        ⚠ 掩蔽段故意【不读】队列：在段边界读走会吞掉"掩蔽末期按下、其实属于反应窗口"的按键。
%   (#3) 记录真实 flip 时间戳，并新增 9 列（见下方"输出列"）：名义 T 与实际 T 的差只能靠它们看出来。
%        验收口径：没有刺激期内按键的试次应满足 |stimulus_dur_actual − T| < 1 帧。
%
% ★★ v4.1 本次修正（2026-10-14，Stage 6 前置检查发现；只改两处输出格式串）★★
%   (D1) T/W 列的打印精度不足，会【静默摧毁 T 这个被试内因子】。
%        旧格式串（v3 继承）对第 9/10 列用 %.1f，而 v4 里 T 的单位是【秒】：
%        T = 2/5/9/15 帧 = 0.03333/0.08333/0.14999/0.24998 s → %.1f 打印成 0.0/0.1/0.1/0.2，
%        于是 83.33 ms 与 149.99 ms 两级【完全无法区分】，且数值本身也失了真。
%        （旧版 data{trialIndex,9} 存的是毫秒，%.1f 当时是对的；改成秒之后没人同步格式串。）
%        修法：两处数据行格式串的第 9/10 列 %.1f → %.6f（练习段与正式段各一处）。
%        对 W 无影响（0.8/1.2/1.8 s 用 %.1f 本来就不失真），但一并加宽以保持一致性。
%        ⚠ 教训：任何"改了单位"的改动都必须回头检查所有格式化输出；这类丢失不报错。
%
% ★★ v4.2 本次修正（2026-10-18，主试按旧手册填"组别 7"导致整场报错退出）★★
%   (#1) 组别输入加固：D4 只有 4 个 P 组，旧版 v3 的"组7=无掩蔽"已废除。旧代码在
%        groupID 越界时直接 error（错误使用 Exp_Design_Formal / groupID=7 越界），
%        主试只能重开；现在改为**弹窗内重填**——校验失败弹出说明（含 4 组速查），
%        关掉后重新弹信息窗，不中断进程；五项信息（组别/编号/性别/年龄/惯用手）
%        全部校验；点"取消"/关窗是**唯一**会终止的情况（不把 NaN 带进实验）。
%   (#2) 同时清掉头注里"组7 无掩蔽"的旧说明，并在主试确认回显里打印
%        "组别 → P"（如 groupID=2 ⇒ P=8），让主试回车前就能看出填错。
%
% ★★ v4.3 本次重构（2026-10-18，为了让这条路径能被无屏幕自测覆盖）★★
%   弹窗 + 校验 + 主试确认的循环从本脚本正文搬到 exp_ask_subject_info.m（本脚本只调用它），
%   好处：hooks 可以注入假的 inputdlg/warndlg/input，于是「先填 7 被拒 → 改填 1 通过」这条
%   真实路径能在命令行跑一遍（test/check_ask_info.m，40 项全通过）。脚本正文因此少了约 50 行。
%   自测入口：
%     matlab -batch "cd('<仓库>/1_Code/Experiment/exp_matlab'); addpath('test'); check_ask_info"
%     matlab -batch "cd('<仓库>/1_Code/Experiment/exp_matlab'); addpath('test'); check_input_validation"
%     python -X utf8 1_Code/Experiment/exp_matlab/test/check_manual_d4.py   % 程序/校验/手册/Word 四者口径
%     matlab -batch "cd('<仓库>/1_Code/Experiment/exp_matlab'); addpath('test'); check_data_accum"
%
% ★★ v4.4 本次修正（2026-10-18，主试实跑第一个 timeout 试次就崩：请修 #1）★★
%   (#1) 数据累积容器 table → cell。旧代码 `data = table()` 之后逐行 `data{trialIndex,14}=respStr`，
%        table 的变量类型由**第一次赋值**锁定：第一行写 'f'（宽度 1）就把 Response 固定成
%        1 字符宽 char 矩阵，第一个 timeout 试次写 'NA'（宽度 2）立刻报
%        「赋值右侧的值的宽度错误。赋值需要宽度为 1 的值」并整场退出（Screen('CloseAll')）。
%        次生症状：每加一行都打印「赋值时将各行添加到了表格中，但并未对表格中所有现有的
%        变量赋值」（主试看到的那 6 条警告），且 table 逐行增长是 O(n^2) 复制。
%        修法：exp_new_data(25) 建 0×25 cell 累积；保存时 exp_data_table 一次性 cell2table。
%   (#2) 顺带修掉一个**只在更晚才会暴露**的静默错误：cell2table 会把不等长的字符列用空格
%        补齐成 char 矩阵（'self' / 'stranger' ⇒ 'self     '），writetable 会把这些补齐空格
%        原样写进 CSV ⇒ 下游按 'self' 精确匹配失败。exp_data_table 统一把 char 列转
%        string(cellstr(...))（cellstr 逐行去尾随空格）。
%   (#3) 保存前增加行数自检：size(data,1) 与 trialIndex-1 不等就 warning（有试次没进内存表）。
%   ⚠ 教训：**"能跑完全程"不等于"能存下来"**——数据写入路径必须单独自测
%      （test/check_data_accum.m：混合 f/j/NA 三行 + 不等长 stim 标签 + 静态守卫）。
%
% ★★ v4.6 本次修正（2026-10-18，60 Hz 实机数据实测发现；判据见 exp_Check/check_stage1_acceptance.py）★★
%   (#1) 「onset 之前的按键」会敲掉刺激：注视期抢按是在 kqCountPresses() 处读的，而它到真正的
%        刺激 onset 之间隔着 Screen('Flip') 的 vsync 等待（最长约一帧）。在这条缝隙里按下的键
%        不会被抢按计数看到，却会被刺激期的 kqFirstPressUntil 立刻取走 ⇒ 刺激在 0–1 帧内被敲掉
%        （stimulus_dur_actual 6–14 ms），本试次被误判为漏答 —— 实测 5/576 = 0.87%。
%        漏答率是本设计的核心因变量，因此必须修，不能当噪声。
%        修法：kqFirstPressUntil(deadline, tFloor) 只接受 tFloor < t <= deadline 的按键；
%              四个调用点（练习/正式 × 刺激期/反应窗口）传 stimulusFlipTime 作 tFloor。
%        这些早于 onset 的键不消费、留在队列里，由下一试次开头的 KbQueueFlush() 清掉。
%   ⚠ 教训：**"抢按已经被计数"不等于"抢按不会影响反应"**——计数与消费是两件事；
%      凡是以时间戳划分的窗口，边界都必须用同一个 tFloor 显式裁一次。
%
% ★★ v4.5 本次修正（2026-10-18，无屏幕全程冒烟实测发现；跑法与判据见 test/run_full_session.m）★★
%   (#1) 逐试次 txt 通道写完从不 fclose：`fidTrial = fopen(..., 'a+')` 之后只 fprintf，
%        保存阶段 movefile 会因文件仍被占用报「无法从源读取」，且缓冲区可能未落盘。
%        修法：保存阶段先 fclose(fidTrial)（无文件句柄时静默跳过）。
%   (#2) 注视期抢按被**当成反应**：抢按已记进 premature_press，但那一按仍留在 KbQueue 里，
%        紧接着的刺激期 kqFirstPressUntil 立刻取到它 ⇒ responseTime = 按键时刻 − 刺激 onset
%        为**负值**，该行既算"已响应"又让 stimulus_dur_actual 与「按键后下一帧」对不上。
%        修法：记完 premature_press 立即 KbQueueFlush()（练习段、正式段各一处）。
%   (#3) 数值兜底：反应时必须严格为正（responseTime <= 0 ⇒ 仍按抢按处理、响应清空），
%        防止驱动时间戳早于 onset 的极端情况把负 RT 写进数据。
%   ⚠ 教训：**"能跑完全程 + 能存下来"仍不等于"每一步的数值都对得上"**——
%      需要一条把产物再喂回 read_formal_data.py 的端到端判据（本次就是它抓出 #2）。
%
% 输出列（25 列 = v3 的 16 列 + v4 新增 9 列；练习阶段 block = 0）：
%   1 groupID  2 subjectID  3 gender  4 age  5 handedness  6 stage  7 trialID
%   8 P  9 T  10 W  11 Shape  12 Label  13 CorrectKey  14 Response  15 RT  16 Correct
%   17 block  18 premature_press  19 timeout  20 responded_by_deadline
%   21 stimulus_onset_actual  22 stimulus_offset_actual  23 mask_onset_actual
%   24 stimulus_dur_actual  25 stimulus_frames
%   · 【单位】T、W、RT、stimulus_*_actual 一律为【秒】（T=0.08333 ⇔ 83.33 ms）。列 8 的 P 是
%     "本组额外练习试次数"（个）。v4.1 起 T/W 以 %.6f 写出，四档 T 各自可辨。
%   · 缺失值统一写 NA / NaN（Response 未响应写 'NA'，Correct 未响应写 NaN），不写字面 0 或空串
%   · stimulus_onset_actual  = 刺激那次 Flip 的【绝对 GetSecs 时刻】（秒）
%     stimulus_offset_actual = 刺激离屏时刻 = 掩蔽（或空白）那次 Flip；D5 下若刺激期内按键，
%                              它等于"按键之后紧接着的那次 Flip"，因此 ≥ RT
%     mask_onset_actual      = 与 stimulus_offset_actual 同一次 Flip（M=0 时是翻空白屏）
%     stimulus_dur_actual    = stimulus_offset_actual − stimulus_onset_actual（秒）
%     stimulus_frames        = round(stimulus_dur_actual / FlipIntv)
%   · timeout = 1 ⇔ 到截止（stimulusFlipTime + W）仍无有效按键；responded_by_deadline = 1 − timeout
%   · premature_press = 1 ⇔ 注视期（刺激 onset 之前）就按了 f/j（抢按；对应 v2 的 Premask）
%
% 组别速查（P = 额外练习试次数；共 4 组；T 与 W 均为被试内因子，逐试次/逐块变化）
%   组1 P0    组2 P8    组3 P32    组4 P120
%   （C5：所有被试都先做 60 s 联结学习 ⇒ P=0 ≠ 零暴露，变量应称 P_additional_practice_trials）
% 正式阶段：3 个 block（W = 799.98 / 1199.9 / 1799.9 ms），每块 4 T × 4 类刺激 × 12 次 = 192 试次
%   ★ C6：W 在被试内变化 ⇒ 每块开始前有一次提示屏告知本组的反应窗口，被试按空格开始
%   ★ D5：刺激期内按键即结束刺激（实际呈现时长 = min(T, RT)），掩蔽段仍固定 200 ms
% 被试编号规则：组内从 1 连续递增、不跳号（奇偶决定形状-标签配对方向；
%   编号 mod4 = 1或0 → 匹配键 f；mod4 = 2或3 → 匹配键 j）
% 数据输出：程序当前文件夹下 EXP_data_group{组别}_{编号}.csv（宽表，25 列）和
%   exp_group{组别}_subject{编号}.txt（逐试次追加的长表，同一份 25 列表头）
% -----------------------------------------------------------------------------
Screen('Preference', 'SkipSyncTests', 0);
% ⚠ 切勿在此调用 KbName('UnifyKeyNames')！
%   本机 PTB 3.0.19 实测：开启"统一键名"后，小写 'esc' 立刻变成无效键名（只认 'ESCAPE'/'escape'），
%   而本程序通篇是按"未开启"的命名方案书写的（'esc' / 'return' / 'space'），于是会在第一个试次的
%   checkEscape 处直接报错 "Key name "esc" not recognized" 并整场退出（v2 与 v0.7 都栽在这里）。
%   反向查询 KbName(70)/KbName(74) 在两种方案下均返回 'f'/'j'，f/j 判定不受影响，故无需开启。
InitializeMatlabOpenGL;

%
% ★★ v4.7 本次修正（2026-10-18，主试实机报告"块首指导语一闪而过"；D90）★★
%   (#1) 8 处「按空格继续」缺"松键门槛"：这些等待都用 KbCheck 忙等"此刻空格是否按着"，
%        没有按下沿的概念。相邻两屏（练习结束休息屏 → 块首 C6 指导语）之间只隔一次
%        Screen('Flip') 与几十毫秒建表时间；上一屏确认用的空格若还按着（≥50 ms 即够），
%        下一屏的 while 会立刻被这个"残留按下"穿透 ⇒ 指导语一闪而过、被试还没读完就进了
%        正式试次（该块首个试次被白白消耗，且被试不知道本组反应窗口是多少）。
%        修法：新增局部函数 waitForSpaceRelease()，在每个 while 空格等待之前先等一次
%        "所有键都松开"（最多 5 s，防键卡住时死结），再等一次新的按下。
%        只改等待方式，不动试次时序、不动数据列。
%

% ★★ v4.8 本次修正（2026-10-18，路径可移植性；D92）★★
%   (#1) 掩蔽纹理用裸文件名 imread('self10-1.png') ⇒ 解析依据是【当前目录】。而手册第 7 节
%        要求把当前目录设成本轮数据文件夹，两者冲突：照着手册做，预加载就会报”文件不存在”。
%        用户的实际习惯是把 exp_matlab 整个文件夹拷到实验室机器，路径与本机不同。
%        修法：progDir = fileparts(mfilename('fullpath'))，10 张掩蔽纹理一律用
%        fullfile(progDir, ...) 解析；数据仍写【当前目录】（不改变”数据存本轮文件夹”的用法）。
%   (#2) 启动时打印【程序目录】与【输出目录】，并自检 10 张 PNG 是否齐全，
%        缺哪张一次性报出（旧版要等到掩蔽预加载才报，且只说第一个）。
%

%% 被试基础信息
% 逐试次累积容器：**必须用 cell 而不是 table()**（★ v4.4 / D78）
% table 的变量类型由第一次赋值锁定：第一行写 'f'（宽度 1）就把 Response 列固化成
% 1 字符宽，第一个 timeout 试次写 'NA'（宽度 2）会报
% 「赋值右侧的值的宽度错误。赋值需要宽度为 1 的值」并整场退出（2026-10-18 实机踩到）。
% cell 不锁宽度；保存时用 exp_data_table 一次性转换。
data = exp_new_data(25);

% 路径锚定（★ v4.8 / D92）：程序资源跟着【本文件所在目录】走，数据仍写【当前目录】
progDir = fileparts(mfilename('fullpath'));
if isempty(progDir), progDir = pwd; end
dataDir = pwd;
maskFiles = {'self10-1.png', 'self10-2.png', 'self10-3.png', 'self10-4.png', 'self10-5.png', ...
             'stranger10-1.png', 'stranger10-2.png', 'stranger10-3.png', 'stranger10-4.png', 'stranger10-5.png'};
missingMask = maskFiles(~cellfun(@(f) exist(fullfile(progDir, f), 'file') == 2, maskFiles));
assert(isempty(missingMask), 'Exp_Design_Formal:maskMissing', ...
    '掩蔽纹理缺失（程序目录 = %s）：%s', progDir, strjoin(missingMask, ', '));
fprintf('[路径] 程序目录（掩蔽纹理） = %s\n', progDir);
fprintf('[路径] 输出目录（CSV/txt） = %s\n', dataDir);


% 基本信息收集（★ v4.2：D4 只有 4 个 P 组，任何一项非法都在弹窗里重填，不再 error 退出）
P_groups = [0; 8; 32; 120];            % D4 的 4 个组（被试间），按 groupID 取

% 弹窗 + 逐项校验 + 主试确认（逻辑见 exp_ask_subject_info.m；无屏幕自测见 test/check_ask_info.m）
info       = exp_ask_subject_info(P_groups);
groupID    = info.groupID;
subjectID  = info.subjectID;
gender     = info.gender;
age        = info.age;
handedness = info.handedness;

%% 屏幕窗口
% 隐藏鼠标，最后记得取消注释
HideCursor;

% 创建窗口并设置屏幕
screenNumber = max(Screen('Screens')); % 获取屏幕
isTestMode = false; % 设置测试模式，修改为true或false
% 根据是否是测试模式设置窗口大小
if isTestMode
    windowWidth = 800; % 测试模式下设置小窗口宽度
    windowHeight = 600; % 测试模式下设置小窗口高度
    rect = [0, 0, windowWidth, windowHeight]; % 设置窗口位置和大小
else
    rect = []; % 不设置具体的窗口大小，使用全屏
end
% 创建窗口
[window, windowRect] = Screen('OpenWindow', screenNumber, [128, 128, 128], rect);
% 获取屏幕大小
[screenXpixels, screenYpixels] = Screen('WindowSize', window); 
% 屏幕中心坐标
centerX = screenXpixels / 2; % 屏幕中心X坐标
centerY = screenYpixels / 2; % 屏幕中心Y坐标

% 获取显示器的帧间隔（秒/帧）
FlipIntv = Screen('GetFlipInterval', window);

%% 刺激设置
% 设置字体
Screen('TextFont', window, 'Simsun'); % 宋体

% 刺激颜色
stimColor = [255, 255, 255]; % 白色

% 注视点的大小
FixationSize = deg2pix(0.8, 16, windowRect(3), 70);

% 刺激与注视点的距离
distance = deg2pix(3.5, 16, windowRect(3), 70);

% 刺激的坐标位置
shapePositions = [
    centerX, centerY - distance; % 上方的形状
    centerX, centerY + distance; % 下方的文字
];

% 设置标签
labelEnglish = {'self', 'stranger'}; % 英文标签
labelChinese = {'自我', '生人'};  % 中文标签

% 设置形状
shapeEnglish = {'circle', 'square'}; % 英文标签
shapeChinese = {'圆形', '正方形'};  % 中文标签

% 形状的大小:3.8° * 3.8°, 计算这个条件下对应视角在屏幕中的像素数
halfShapeSize = deg2pix(1.9, 16, windowRect(3), 70);

% 定义形状和标签的正确匹配关系,_后为余数
correctPairs_0 = {
    'square', 'self';
    'circle', 'stranger'
};

correctPairs_1 = {
    'square', 'stranger';
    'circle', 'self'
};

% 根据被试编号决定刺激分配方式
if mod(subjectID, 2) == 0  % 偶数编号的被试
    correctOrder = correctPairs_0;  % 正确的匹配顺序
else   % 奇数编号的被试
    correctOrder = correctPairs_1;  % 反转正确的匹配顺序
end

% 预分配匹配和不匹配刺激的单元格数组
matchingStimuli = cell(0, 2);
nonMatchingStimuli = cell(0, 2);

% 生成匹配和不匹配刺激
for i = 1:size(correctOrder, 1)
    shape = correctOrder{i, 1};
    correctLabel = correctOrder{i, 2};
    
    % 生成匹配刺激
    matchingStimuli = [matchingStimuli; {shape, correctLabel}];
    
    % 生成不匹配刺激，排除当前的正确标签
    otherLabel = setdiff(labelEnglish, correctLabel);  % 排除当前的正确标签
    for j = 1:length(otherLabel)
        nonMatchingStimuli = [nonMatchingStimuli; {shape, otherLabel{j}}];
    end
end

% 合并匹配和不匹配的刺激
stimuli = [matchingStimuli; nonMatchingStimuli];

% 掩蔽刺激
selfMaskImages     = cellfun(@(f) fullfile(progDir, f), maskFiles(1:5),  'UniformOutput', false);
strangerMaskImages = cellfun(@(f) fullfile(progDir, f), maskFiles(6:10), 'UniformOutput', false);

% =========================================================================
% D4 设计（2026-10-14 定稿；依据 5_Reference/08_工作流/正式采集_候选设计_v2_定稿.md）
%   P 被试间   ∈ {0, 8, 32, 120} 个额外练习试次
%              （C5：所有被试都做过 60 s 联结学习，P=0 ≠ 零暴露）
%   T 被试内   ∈ {33.33, 83.33, 149.99, 249.98} ms  = 2/5/9/15 帧
%   W 被试内   ∈ {799.98, 1199.9, 1799.9} ms        = 48/72/108 帧
%   12 个 (T,W) 单元 × 4 类刺激 × 12 次 = 576 试次/人（3 个 block，每块一个 W）
%   ★ 旧版是 9 条手挑条件、每人只跑一行（P/T/W 三者被试间）——已废弃。
% =========================================================================
% P_groups 已在"被试基础信息"处定义（★ v4.2 提前，供弹窗校验使用）：
%   P_groups = [0; 8; 32; 120];
if groupID < 1 || groupID > numel(P_groups)
    error('D4 只有 %d 个 P 组（被试间），groupID=%d 越界。', numel(P_groups), groupID);
end

% 练习试次数量 P（组间不同；组内所有被试相同）
P = P_groups(groupID);

% C4：P 必须是 4 的倍数（程序每轮呈现 4 类刺激）
if mod(P, 4) ~= 0
    error('D4 要求 P 为 4 的倍数，收到 P=%d。', P);
end

% C2 帧量化：T 与 W 都按 round(x / FlipIntv) 取帧（FlipIntv 见上方 Screen('GetFlipInterval')）
% ⚠ v4 修正：原文误写为 FlipInv（未定义变量），会在启动时直接报错，已统一为 FlipIntv
T_nominal = [33.33, 83.33, 149.99, 249.98];   % ms，D4 的名义 T 水平
W_nominal = [799.98, 1199.9, 1799.9];         % ms，D4 的名义 W 水平
T_levels = round(T_nominal / 1000 / FlipIntv) * FlipIntv;  % 2/5/9/15 帧
W_levels = round(W_nominal / 1000 / FlipIntv) * FlipIntv;  % 48/72/108 帧

% 掩蔽开关 M：D4 的 12 个格子全部带掩蔽（旧的"组7无掩蔽"不再存在）
M = 1;

% 掩蔽段固定时长（秒）
maskDuration = 0.2;

% ★ 物理约束自检：逐格检查全部 12 个 (T,W) 组合
%   C1：W > T + 200 ms（掩蔽段不能被反应窗口截断）
%   C3：掩蔽后可用窗口 W − T − 200 ≥ 300 ms（否则该单元接近全遗漏）
for wi = 1:numel(W_levels)
    for ti = 1:numel(T_levels)
        if W_levels(wi) <= T_levels(ti) + maskDuration
            error(['D4 违反 C1：W=%.2f ms 必须 > T+200 ms（T=%.2f ms），' ...
                   '否则掩蔽段会超出反应窗口。'], W_levels(wi) * 1000, T_levels(ti) * 1000);
        end
        if (W_levels(wi) - T_levels(ti) - maskDuration) < 0.3
            error(['D4 违反 C3：掩蔽后可用窗口 = %.0f ms < 300 ms' ...
                   '（T=%.2f ms, W=%.2f ms），该单元会接近全遗漏。'], ...
                   (W_levels(wi) - T_levels(ti) - maskDuration) * 1000, ...
                   T_levels(ti) * 1000, W_levels(wi) * 1000);
        end
    end
end

% 练习阶段/联结阶段使用固定的代表性 T/W；正式阶段逐试次用 Ttrial/Wtrial
T = T_levels(2);   % 83.33 ms
W = W_levels(2);   % 1199.9 ms

fprintf('   D4：P=%d ｜ T 水平 = %s ms ｜ W 水平 = %s ms\n', P, ...
    mat2str(round(T_levels * 1000, 2)), mat2str(round(W_levels * 1000, 1)));

% ★ Stage 1 修正 #4 证据：逐行打印"名义 → 帧数 → 量化后"，并给出与名义值的偏离
%   验收时要跟 stimulus_dur_actual 比的是【量化后】的 T（差应 < 1 帧）
fprintf('   ── 帧量化核对（FlipIntv = %.6f ms，约 %.3f Hz）──\n', FlipIntv * 1000, 1 / FlipIntv);
for ti = 1:numel(T_levels)
    fprintf('      T%d：名义 %.2f ms → %d 帧 → 实际 %.3f ms（偏离 %+.3f ms = %+.2f 帧）\n', ...
        ti, T_nominal(ti), round(T_levels(ti) / FlipIntv), T_levels(ti) * 1000, ...
        (T_levels(ti) - T_nominal(ti) / 1000) * 1000, ...
        (T_levels(ti) - T_nominal(ti) / 1000) / FlipIntv);
end
for wi = 1:numel(W_levels)
    fprintf('      W%d：名义 %.1f ms → %d 帧 → 实际 %.3f ms（偏离 %+.3f ms = %+.2f 帧）\n', ...
        wi, W_nominal(wi), round(W_levels(wi) / FlipIntv), W_levels(wi) * 1000, ...
        (W_levels(wi) - W_nominal(wi) / 1000) * 1000, ...
        (W_levels(wi) - W_nominal(wi) / 1000) / FlipIntv);
end

% =========================================================================
% ★ Stage 1 技术修正 #1（2026-10-14）：掩蔽纹理一次性预加载
%   旧版在【每个试次内】做 imread + Screen('MakeTexture')（联结/练习/正式三段各一处），
%   磁盘 I/O 会让掩蔽的 Flip 晚于名义时刻 ⇒ 实际刺激时长长于名义 T
%   （研究计划 §8.4 第 1 项，优先级最高）。改为开场一次性建好全部 10 个掩蔽纹理
%   与对应矩形，试次内只做 Screen('DrawTexture')。
% =========================================================================
selfMaskTex = zeros(1, numel(selfMaskImages));
selfMaskRect = cell(1, numel(selfMaskImages));
for i = 1:numel(selfMaskImages)
    im = imread(selfMaskImages{i});
    [mh, mw, ~] = size(im);
    selfMaskTex(i) = Screen('MakeTexture', window, im);
    selfMaskRect{i} = CenterRectOnPoint([0 0 mw mh], centerX, centerY + distance);
end
strangerMaskTex = zeros(1, numel(strangerMaskImages));
strangerMaskRect = cell(1, numel(strangerMaskImages));
for i = 1:numel(strangerMaskImages)
    im = imread(strangerMaskImages{i});
    [mh, mw, ~] = size(im);
    strangerMaskTex(i) = Screen('MakeTexture', window, im);
    strangerMaskRect{i} = CenterRectOnPoint([0 0 mw mh], centerX, centerY + distance);
end
fprintf('   掩蔽纹理预加载完成：self %d 张、stranger %d 张（Stage 1 修正 #1）\n', ...
    numel(selfMaskTex), numel(strangerMaskTex));

%% 联结阶段
% 指导语字体大小
Screen('TextSize', window, 30); 

% 获取形状配对规则信息
label1 = correctOrder{1, 2};  % 获取第一个形状配对的标签
label2 = correctOrder{2, 2};  % 获取第二个形状配对的标签
shape1 = correctOrder{1, 1};  % 获取第一个形状配对的标签
shape2 = correctOrder{2, 1};  % 获取第二个形状配对的标签

% 获取形状1的中文名
label1Index = find(strcmp(labelEnglish, label1));  % 获取标签1对应的英文标签索引
label1Chinese = labelChinese{label1Index};   % 获取标签1对应的中文形状
shape1Index = find(strcmp(shapeEnglish, shape1));  % 获取标签1对应的英文标签索引
shape1Chinese = shapeChinese{shape1Index};   % 获取形状1对应的中文形状

% 获取形状2的中文名
label2Index = find(strcmp(labelEnglish, label2));  % 获取形状2对应的英文标签索引
label2Chinese = labelChinese{label2Index};   % 获取形状2对应的中文形状
shape2Index = find(strcmp(shapeEnglish, shape2));  % 获取标签1对应的英文标签索引
shape2Chinese = shapeChinese{shape2Index};   % 获取形状1对应的中文形状

% 获取匹配按键
matchKey = getMatchKey(subjectID);

% 根据匹配按键定义不匹配按键
if matchKey == 'f'
    mismatchKey = 'j';
else
    mismatchKey = 'f';
end

% 联结阶段指导语1
aline1 = '你好，欢迎参加本实验。';
aline2 = '接下来首先你需要记忆几何形状（圆形、正方形）和身份标签（自我、陌生人）的配对关系。';
aline3 = '这一关系会呈现60s，60s之后会自动停止。';
aline4 = '明白了任务之后请按回车键记忆关系。';
aline5 = '如果对本实验还有不清楚之处，请立即向实验员咨询。';

% 定义每段文本的位置
DrawFormattedText(window, double(aline1), 'center', centerY - 200, stimColor); % 第一行
DrawFormattedText(window, double(aline2), 'center', centerY - 100, stimColor); % 第二行
DrawFormattedText(window, double(aline3), 'center', centerY, stimColor); % 第三行
DrawFormattedText(window, double(aline4), 'center', centerY + 100, stimColor); % 第四行
DrawFormattedText(window, double(aline5), 'center', centerY + 200, stimColor); % 第五行

% 刷新屏幕
Screen('Flip', window);

% 等待被试按空格键继续
waitForSpace = true;
waitForSpaceRelease();
while waitForSpace
    [keyIsDown, ~, keyCode] = KbCheck;
    if keyIsDown
        % 查找按下的键
        pressedKey = find(keyCode);  % 查找按下的键的索引
        if any(pressedKey == KbName('return'))  % 检查是否按下空格键
            waitForSpace = false;  % 按下空格键后跳出循环，继续实验
        end
    end
end


% 联结阶段指导语2
aline6 = '记忆以下规则60s：';
aline7 = sprintf('%s 是 %s , %s 是 %s',  label1Chinese, shape1Chinese, label2Chinese, shape2Chinese);

% 定义每段文本的位置
DrawFormattedText(window, double(aline6), 'center', centerY - 100, stimColor); % 第五行
DrawFormattedText(window, double(aline7), 'center', centerY, stimColor); % 第六行

% 刷新屏幕
Screen('Flip', window);

% 等待60秒后自动进入下一帧
WaitSecs(60);  % 等待60秒


% 联结阶段指导语3
aline8 = '接下来将进入正式实验。';
aline9 = '如果未记清楚记忆关系，请立即向实验员咨询。';
aline10 = '没有问题请按回车键进入实验。';

% 定义每段文本的位置
DrawFormattedText(window, double(aline8), 'center', centerY - 100, stimColor); % 第五行
DrawFormattedText(window, double(aline9), 'center', centerY, stimColor); % 第六行
DrawFormattedText(window, double(aline10), 'center', centerY + 100, stimColor); % 第七行

% 刷新屏幕
Screen('Flip', window);

% 等待被试按空格键继续
waitForSpace = true;
waitForSpaceRelease();
while waitForSpace
    [keyIsDown, ~, keyCode] = KbCheck;
    if keyIsDown
        % 查找按下的键
        pressedKey = find(keyCode);  % 查找按下的键的索引
        if any(pressedKey == KbName('return'))  % 检查是否按下回车键
            waitForSpace = false;  % 按下空格键后跳出循环，继续实验
        end
    end
end

% 继续后续实验流程

%% 匹配阶段-练习
% 指导语字体大小
Screen('TextSize', window, 30); 

% 练习指导语
bline1 = '屏幕中心的十字上方会呈现形状，同时下方会呈现标签。';
bline2 = '接下来的任务是判断屏幕上呈现的刺激对与刚刚学习的关系是否一致。';
bline3 = sprintf('匹配按 %s 键 , 不匹配按 %s 键', matchKey, mismatchKey);
bline4 = '有任何问题请立即向实验员咨询。';
bline5 = '没有问题请在记住配对关系后按空格键进入实验。';

DrawFormattedText(window, double(bline1), 'center', centerY - 200, stimColor); % 第一行
DrawFormattedText(window, double(bline2), 'center', centerY - 100, stimColor); % 第二行
DrawFormattedText(window, double(bline3), 'center', centerY, stimColor); % 第三行
DrawFormattedText(window, double(bline4), 'center', centerY + 100, stimColor); % 第四行
DrawFormattedText(window, double(bline5), 'center', centerY + 200, stimColor); % 第五行

% 刷新屏幕
Screen('Flip', window);

% 等待被试按空格键继续
waitForSpace = true;
waitForSpaceRelease();
while waitForSpace
    [keyIsDown, ~, keyCode] = KbCheck;
    if keyIsDown
        % 查找按下的键
        pressedKey = find(keyCode);  % 查找按下的键的索引
        if any(pressedKey == KbName('space'))  % 检查是否按下空格键
            waitForSpace = false;  % 按下空格键后跳出循环，继续实验
        end
    end
end

% 练习
% 动态生成文件名，根据subjectID命名
fileName = sprintf('exp_group%d_subject%d.txt', groupID, subjectID);

% 打开文件，用于保存数据，'a' 表示追加模式，确保每个 trial 保存一行数据
fileID = fopen(fileName, 'a+');
if fileID == -1
    error('无法打开文件');
end

% 在文件头部添加列标题（如果文件是空的）
% ★ v4：前 16 列为旧版原有列；后 9 列为 Stage 1 修正 #3 新增（时间戳与判定标记）
if ftell(fileID) == 0
    fprintf(fileID, ['groupID\tsubjectID\tgender\tage\thandedness\tstage\ttrialID\tP\tT\tW\t' ...
        'Shape\tLabel\tCorrectKey\tResponse\tRT\tCorrect\t' ...
        'block\tpremature_press\ttimeout\tresponded_by_deadline\t' ...
        'stimulus_onset_actual\tstimulus_offset_actual\tmask_onset_actual\t' ...
        'stimulus_dur_actual\tstimulus_frames\n']);
end

% =========================================================================
% ★ v4 Stage 1 技术修正 #2（2026-10-14）：按键采集改为 KbQueue 事件队列
%   旧版用 KbCheck 高频轮询：轮询间隙内发生的短按键会被整段丢掉 → "假遗漏"
%   （研究计划 §8.4 第 2 项，v2 已实现，此处移植）。
%   KbQueue 由驱动在按键【发生的那一刻】打上绝对 GetSecs 时间戳并排队，
%   因此轮询快慢只影响"多快发现按键"，不影响 RT 精度，也不会丢事件。
%   本机 PTB 3.0.19 实测（v2 已踩过）：KbQueueCreate 的 keyList 必须是
%   【256 长度的 double 掩码】，既不能传键码短向量，也不能传 logical，否则报 "Usage:"。
% =========================================================================
keysOfInterest = zeros(1, 256);
keysOfInterest([KbName('f'), KbName('j'), resolveEscKeyCode()]) = 1;
try, KbQueueRelease(); catch, end   % 防御：上次异常退出可能仍占用队列
KbQueueCreate([], keysOfInterest);
KbQueueStart();

% 初始化一个全局的trialIndex，用于记录当前试次
trialIndex = 1;

% 计算每次循环的试次数量
loopCount = P / 4; % 计算循环次数（P/4次）

% 循环呈现每个trial
for k = 1:loopCount  % 循环次数为 P/4

    % 打乱刺激顺序
    stimuli_bin = stimuli(randperm(size(stimuli, 1)), :);

    % 循环呈现每个trial
    for i = 1:length(stimuli)
    
        % 每个trial开始时，立即检查Esc键，并清空按键队列
        % ★ v4：KbQueueFlush 丢弃本试次之前的历史按键（抢按由下方单独计数）
        checkEscape();
        KbQueueFlush();

        % 获取当前刺激的形状和标签
        currentShape = stimuli_bin{i, 1};
        currentLabel = stimuli_bin{i, 2};
        
        % 获取当前被试的配对规则
        pairingRules = getPairingRules(subjectID);
        
        % 使用获取到的配对规则继续进行后续的实验流程
        disp(pairingRules);  % 输出配对规则以检查
        
        % 获取当前形状和标签的按键
        correctKey = pairingRules.(currentShape).(currentLabel);
        
        % 1. 显示中央注视点 (+)，持续500ms
        % 注视点持续时间
        fixationDuration = 0.5;
        
        % 根据注视点持续时间计算所需的帧数
        fixationFrames = round(fixationDuration / FlipIntv);  % 计算所需的帧数

        % 应用注视点大小
        Screen('TextSize', window, FixationSize);  

        % 预先生成所有要显示的注视点图像
        for j = 1:fixationFrames
            % 绘制注视点（在内存缓冲区中）
            DrawFormattedText(window, '+', 'center', 'center', stimColor); 
        end

        % 刷新屏幕，显示注视点
        fixationFlipTime = Screen('Flip', window);

        while GetSecs() - fixationFlipTime < fixationDuration
            % 等待fixationDuration时间
        end
    
        % 注视点呈现检查Esc键
        checkEscape(); 
        
        % 2. 显示形状和标签，持续500ms
        % 根据刺激呈现时间计算所需的帧数
        stimuliFrames = round(T / FlipIntv);  % 计算所需的帧数

        % 预先生成所有要显示的刺激图像
        for j = 1:stimuliFrames
            % 绘制注视点（在内存缓冲区中）
            % 应用注视点大小
            Screen('TextSize', window, FixationSize); 
            DrawFormattedText(window, '+', 'center', 'center', stimColor);
        
            % 绘制形状
            % 计算左、右、上、下边界
            left = shapePositions(1, 1) - halfShapeSize;  % 左边界
            right = shapePositions(1, 1) + halfShapeSize; % 右边界
            top = shapePositions(1, 2) - halfShapeSize;   % 上边界
            bottom = shapePositions(1, 2) + halfShapeSize; % 下边界
            
            switch currentShape
                case 'circle'
                    Screen('FillOval', window, stimColor, [left, top, right, bottom]);  % 绘制圆形
                case 'square'
                    Screen('FillRect', window, stimColor, [left, top, right, bottom]);  % 绘制方形
            end
            
            % 绘制标签（显示中文标签）
            Screen('TextSize', window, 90);
            labelIndex = find(strcmp(labelEnglish, currentLabel));  % 获取对应的中文标签索引
            DrawFormattedText(window, double(labelChinese{labelIndex}), 'center', shapePositions(2, 2), stimColor); % 标签位置：注视点下方
        end
      
        % ★ v4 修正 #2/#3：注视点期间（刺激 onset 之前）的 f/j 按键记为"抢按"
        %   这一段在 KbCheck 版里根本没被读取过，只有 KbQueue 拿得到
        [nPreKey, nPreEsc] = kqCountPresses();
        if nPreEsc > 0, escAbort(); end
        prematurePress = double(nPreKey > 0);
        if prematurePress > 0
            % ★ v4.5（D79）：抢按已经记进 premature_press，必须从队列里清掉。
            %   否则这一按会在下面的刺激期 kqFirstPressUntil 里被当成"反应"，得到
            %   负的反应时（pressAbs − stimulusFlipTime < 0），并让 stimulus_dur_actual
            %   与"按键后下一帧"对不上（2026-10-18 无屏幕全程冒烟实测到）。
            KbQueueFlush();
        end

        % 刷新屏幕并记录刺激呈现时间
        stimulusFlipTime = Screen('Flip', window); % 显示注视点、形状和标签，并记录刺激呈现时间
        
        % ★ 反应窗口自【刺激 onset】起算：截止 = stimulusFlipTime + W
        %   response/responseTime 在此初始化，随后 刺激期/掩蔽期/空白 三段全程轮询键盘
        response = NaN;       % 尚未反应时保持 NaN（漏答 → Response 缺失、Correct 记为 NaN）
        responseTime = NaN;   % 反应时 = 按键时刻 − 刺激 onset（秒）

        % 2a. 刺激呈现 T：用 KbQueue 采集（刺激期按键从此会被记录，不再丢失）
        [respKey, respAbs, nEsc] = kqFirstPressUntil(stimulusFlipTime + T, stimulusFlipTime);   % ★ v4.6：忽略 onset 之前的键
        if nEsc > 0, escAbort(); end
        if ~isempty(respKey)
            response = respKey;                            % 记录按键
            responseTime = respAbs - stimulusFlipTime;     % 反应时（自刺激 onset）
            % ★ D5：刺激期内按键即结束刺激 ⇒ 实际呈现 = min(T, RT)
        end

        % 刺激呈现检查Esc键
        checkEscape(); 

        % 3. 掩蔽/空白段 200 ms（M=1 显示掩蔽图；M=0 显示空白；时长 maskDuration 见文件开头）
        if M == 1
            % ★ Stage 1 修正 #1：纹理已在开场一次性预加载，此处只选句柄与矩形（无磁盘 I/O）
            if strcmp(currentLabel, 'stranger')
                maskIdx = randi(numel(strangerMaskTex));
                Screen('DrawTexture', window, strangerMaskTex(maskIdx), [], strangerMaskRect{maskIdx});
            elseif strcmp(currentLabel, 'self')
                maskIdx = randi(numel(selfMaskTex));
                Screen('DrawTexture', window, selfMaskTex(maskIdx), [], selfMaskRect{maskIdx});
            end
            maskFlipTime = Screen('Flip', window); % 显示掩蔽刺激
        else
            maskFlipTime = Screen('Flip', window); % 无掩蔽：翻到空白屏
        end
        % ★ v4 修正 #3：记录真实时间戳（名义 T 与实际 T 的差只能靠这几个量看出来）
        maskOnsetActual      = maskFlipTime;   % 掩蔽（或空白）真正上屏的时刻
        stimulusOffsetActual = maskFlipTime;   % 刺激离开屏幕的时刻 = 掩蔽 onset
        stimulusDurActual    = stimulusOffsetActual - stimulusFlipTime;  % 刺激实际在屏时长
        stimulusFrames       = round(stimulusDurActual / FlipIntv);      % 折算成帧数

        % 3b. 掩蔽期【不读】KbQueue：按键留在队列里，由后面的反应窗口段一次性取走
        %     （若在段边界就取走，会吞掉"掩蔽末期按下、其实属于反应窗口"的按键；
        %       而驱动打的时间戳本身就能还原它究竟发生在哪一段）
        %     Esc 仍由 checkEscape（KbCheck 与 KbQueue 互不影响）每 5 ms 检查一次
        while GetSecs() - maskFlipTime < maskDuration
            checkEscape();
            WaitSecs(0.005);
        end
        checkEscape();
    
        % 4. 反应窗口剩余部分：空白屏，直到 stimulusFlipTime + W（刺激/掩蔽期已按键则立即进入反馈）
        % 显示空白屏并记录flip时间
        responseFlipTime = Screen('Flip', window); 
    
        % 说明：response/responseTime 已在刺激 onset 处初始化，此处不得重置，
        %       否则刺激期/掩蔽期记录到的按键会被清掉（漏答时 response 保持 NaN）
        
        % 等待按键输入或超时：截止 = 刺激 onset + W
        % （若刺激期/掩蔽期已按键，isnan(responseTime) 为假，直接进入反馈）
        if isnan(responseTime)
            [respKey, respAbs, nEsc] = kqFirstPressUntil(stimulusFlipTime + W, stimulusFlipTime);   % ★ v4.6：忽略 onset 之前的键
            if nEsc > 0, escAbort(); end
            if ~isempty(respKey)
                response = respKey;
                responseTime = respAbs - stimulusFlipTime;
            end
        end

        % ★ v4 修正 #3：判定 timeout / responded_by_deadline（截止之后的按键不算反应）
        % ★ v4.5（D79）：反应时必须严格为正。驱动时间戳早于刺激 onset 的按键仍属抢按，
        %   不能算本试次反应（否则 RT 为负，stimulus_dur_actual 也会对不上）。
        if ~isnan(responseTime) && responseTime <= 0
            prematurePress = 1;
            response = NaN;
            responseTime = NaN;
        end
        respondedByDeadline = double(~isnan(responseTime) && responseTime <= W);
        timeout = double(~respondedByDeadline);
        if ~respondedByDeadline
            response = NaN;
            responseTime = NaN;
        end
        if isnan(response)
            respStr = 'NA';     % 未响应统一写 NA（Stage 1 额外要求：不写字面 0 / 空串）
        else
            respStr = char(response);
        end

        % 若无按键响应：response 保持 NaN、responseTime 保持 NaN，下方 Correct 记为 NaN

        % 列:1.被试编号, 2.性别, 3.年龄, 4.利手, 5.实验阶段, 6.试次数, 7.试次形状, 8.试次标签, 9.正确的键, 10.被试按键, 11.反应时, 12.是否正确
        % 存储试次数据
        data{trialIndex, 1} = groupID;
        data{trialIndex, 2} = subjectID;
        data{trialIndex, 3} = gender;
        data{trialIndex, 4} = age;
        data{trialIndex, 5} = handedness;
        data{trialIndex, 6} = "practice"; % 存储实验阶段
        data{trialIndex, 7} = trialIndex; % 存储试次编号
        data{trialIndex, 8} = P; % 存储练习试次数量
        data{trialIndex, 9} = T; % 存储刺激呈现时间
        data{trialIndex, 10} = W;   % 存储反应窗口
        data{trialIndex, 11} = currentShape; % 存储试次形状
        data{trialIndex, 12} = string(currentLabel); % 存储试次标签
        data{trialIndex, 13} = char(correctKey);   % 存储正确按键
        data{trialIndex, 14} = respStr;            % 存储被试按键（未响应为 'NA'）
        data{trialIndex, 15} = responseTime; % 存储反应时（单位：秒）
    
        % 判断是否正确
        if isnan(response)  % 如果没有响应（response 保持初值 NaN）
            data{trialIndex, 16} = NaN; % 无反应
        elseif strcmp(response, correctKey)  % 如果响应正确
            data{trialIndex, 16} = 1; % 正确
        else  % 如果响应错误
            data{trialIndex, 16} = 0; % 错误
        end

        % ★ v4 修正 #3：新增 9 列（时间戳与判定标记；练习阶段 block 记 0）
        data{trialIndex, 17} = 0;                    % block
        data{trialIndex, 18} = prematurePress;       % premature_press：注视期抢按
        data{trialIndex, 19} = timeout;              % timeout：截止时仍无有效按键
        data{trialIndex, 20} = respondedByDeadline;  % responded_by_deadline
        data{trialIndex, 21} = stimulusFlipTime;     % stimulus_onset_actual（绝对 GetSecs）
        data{trialIndex, 22} = stimulusOffsetActual; % stimulus_offset_actual
        data{trialIndex, 23} = maskOnsetActual;      % mask_onset_actual
        data{trialIndex, 24} = stimulusDurActual;    % stimulus_dur_actual（秒）
        data{trialIndex, 25} = stimulusFrames;       % stimulus_frames（实际帧数）
    
        % 5. 显示反馈（正确或错误或无响应）
        if isnan(data{trialIndex, 15})  % 无响应，即未在W内做出反应
            feedbackText = double('过慢！');
            feedbackColor = [255, 0, 0];  % 红色
        elseif data{trialIndex, 15} < 0.15  % 反应时小于150ms记为过快
            feedbackText = double('过快！');
            feedbackColor = [255, 0, 0];  % 红色
        elseif data{trialIndex, 16} == 1  % 正确
            feedbackText = double('正确！');
            feedbackColor = [0, 255, 0];  % 绿色
        elseif data{trialIndex, 16} == 0  % 错误
            feedbackText = double('错误！');
            feedbackColor = [255, 0, 0];  % 红色
        end
        
        % 显示反馈
        DrawFormattedText(window, feedbackText, 'center', 'center', feedbackColor); 
        feedbackFlipTime = Screen('Flip', window); % 显示反馈
        WaitSecs(0.5); % 呈现500 ms

        % 反馈检查Esc键
        checkEscape(); 

        % 写入数据到文件（25 列；列 14 直接用 respStr，避免 char(NaN) 写出 NUL 字节）
        fprintf(fileID, ['%d\t%d\t%d\t%d\t%d\t%s\t%d\t%d\t%.6f\t%.6f\t%s\t%s\t%s\t%s\t%.3f\t%d\t' ...
            '%d\t%d\t%d\t%d\t%.6f\t%.6f\t%.6f\t%.6f\t%d\n'], ...
            data{trialIndex, 1}, data{trialIndex, 2}, data{trialIndex, 3}, data{trialIndex, 4}, ...
            data{trialIndex, 5}, data{trialIndex, 6}, data{trialIndex, 7}, data{trialIndex, 8}, ...
            data{trialIndex, 9}, data{trialIndex, 10}, data{trialIndex, 11}, data{trialIndex, 12}, ...
            data{trialIndex, 13}, respStr, data{trialIndex, 15}, data{trialIndex, 16}, ...
            data{trialIndex, 17}, data{trialIndex, 18}, data{trialIndex, 19}, data{trialIndex, 20}, ...
            data{trialIndex, 21}, data{trialIndex, 22}, data{trialIndex, 23}, data{trialIndex, 24}, ...
            data{trialIndex, 25});

        % 更新trialIndex
        trialIndex = trialIndex + 1;  % 确保在每次循环后trialIndex递增

    end
end

%% 练习与正式实验之间的休息
% 指导语字体大小
Screen('TextSize', window, 30); 

% 每个block结束后，提示休息并等待按任意键继续
restMessage1 = '已完成练习，';
restMessage2 = '休息后按空格键进入正式实验。';
DrawFormattedText(window, double(restMessage1), 'center', 'center', stimColor); % 第一行
DrawFormattedText(window, double(restMessage2), 'center', centerY + 100, stimColor); % 第二行
Screen('Flip', window);  % 显示休息提示

% 等待被试按空格键继续
waitForSpace = true;
waitForSpaceRelease();
while waitForSpace
    [keyIsDown, ~, keyCode] = KbCheck;
    if keyIsDown
        % 查找按下的键
        pressedKey = find(keyCode);  % 查找按下的键的索引
        if any(pressedKey == KbName('space'))  % 检查是否按下空格键
            waitForSpace = false;  % 按下空格键后跳出循环，继续实验
        end
    end
end

%% 匹配阶段-正式实验
% D4：3 个 block，每块固定一个 W 水平；块内 4 个 T × 4 类刺激 × 12 次 = 192 试次
nRep = 12;                                                 % 每个 (T, 刺激类型) 单元的重复次数
block = numel(W_levels);                                   % 3 个 block
blockTrials = numel(T_levels) * length(stimuli) * nRep;    % 4 × 4 × 12 = 192
fprintf('   正式阶段：%d 个 block × %d 试次 = %d 试次/人\n', block, blockTrials, block * blockTrials);

% 循环多个block
for b = 1:block

    % 本 block 的 W（被试内变化）
    Wtrial = W_levels(b);

    % 记录当前block的正确回答数
    correctCount = 0;

    % 初始化当前block的反应时间数组
    responseTimes = [];

    % 生成本 block 的试次表：每个 (T 水平 × 刺激类型) 组合重复 nRep 次，然后整体打乱
    trialT = zeros(blockTrials, 1);
    trialS = zeros(blockTrials, 1);
    tIdx = 0;
    for ti = 1:numel(T_levels)
        for si = 1:length(stimuli)
            for r = 1:nRep
                tIdx = tIdx + 1;
                trialT(tIdx) = ti;
                trialS(tIdx) = si;
            end
        end
    end
    shuffleOrder = randperm(blockTrials);
    trialT = trialT(shuffleOrder);
    trialS = trialS(shuffleOrder);

    % ★ C6：W 在被试内变化 ⇒ 每块开始前必须把本组的反应窗口告知被试
    Screen('TextSize', window, 30);
    DrawFormattedText(window, double(sprintf('第 %d / %d 组', b, block)), 'center', centerY - 300, stimColor);
    DrawFormattedText(window, double(sprintf('本组反应窗口：%.0f 毫秒', Wtrial * 1000)), 'center', centerY - 150, stimColor);
    DrawFormattedText(window, double('看到刺激后请尽快按 f 或 j；窗口结束前未按键记为漏答。'), 'center', centerY, stimColor);
    DrawFormattedText(window, double('准备好后按空格键开始本组。'), 'center', centerY + 150, stimColor);
    Screen('Flip', window);
    waitingForSpace = true;
    waitForSpaceRelease();
    while waitingForSpace
        [keyIsDown, ~, keyCode] = KbCheck;
        if keyIsDown
            pressedKeyList = find(keyCode);
            if ~isempty(pressedKeyList) && any(pressedKeyList == KbName('space'))
                waitingForSpace = false;
            end
        end
    end

    % 逐试次循环（试次表 trialT/trialS 已在上方生成）
    for i = 1:blockTrials
    
        % 本试次的 T（D4：T 是 T×W 被试内因子，逐试次变化）
        Ttrial = T_levels(trialT(i));

            % 每个trial开始时，立即检查Esc键，并清空按键队列
            % ★ v4：KbQueueFlush 丢弃本试次之前的历史按键（抢按由下方单独计数）
            checkEscape();
            KbQueueFlush();

            % 获取当前刺激的形状和标签
            currentShape = stimuli{trialS(i), 1};
            currentLabel = stimuli{trialS(i), 2};
            
            % 获取当前被试的配对规则
            pairingRules = getPairingRules(subjectID);
            
            % 使用获取到的配对规则继续进行后续的实验流程
            % （正式阶段不再逐试次打印配对规则，避免 576 行刷屏）
            
            % 获取当前形状和标签的按键
            correctKey = pairingRules.(currentShape).(currentLabel);
            
            % 1. 显示中央注视点 (+)，持续500ms
            % 注视点持续时间
            fixationDuration = 0.5;
            
            % 根据注视点持续时间计算所需的帧数
            fixationFrames = round(fixationDuration / FlipIntv);  % 计算所需的帧数
    
            % 应用注视点大小
            Screen('TextSize', window, FixationSize); 
            DrawFormattedText(window, '+', 'center', 'center', stimColor);
    
            % 预先生成所有要显示的注视点图像
            for j = 1:fixationFrames
                % 绘制注视点（在内存缓冲区中）
                DrawFormattedText(window, '+', 'center', 'center', stimColor); 
            end
    
            % 刷新屏幕，显示注视点
            fixationFlipTime = Screen('Flip', window);
    
            while GetSecs() - fixationFlipTime < fixationDuration
                % 等待fixationDuration时间
            end

            % 注视点呈现检查Esc键
            checkEscape(); 
        
            % 2. 显示形状和标签，持续500ms
            % 根据刺激呈现时间计算所需的帧数
            stimuliFrames = round(Ttrial / FlipIntv);  % 计算所需的帧数（D4：逐试次的 T）
    
            % 预先生成所有要显示的刺激图像
            for j = 1:stimuliFrames

                % 应用注视点大小
                Screen('TextSize', window, FixationSize); 
                % 绘制注视点（在内存缓冲区中）
                DrawFormattedText(window, '+', 'center', 'center', stimColor); 
            
                % 绘制形状
                % 计算左、右、上、下边界
                left = shapePositions(1, 1) - halfShapeSize;  % 左边界
                right = shapePositions(1, 1) + halfShapeSize; % 右边界
                top = shapePositions(1, 2) - halfShapeSize;   % 上边界
                bottom = shapePositions(1, 2) + halfShapeSize; % 下边界
                
                switch currentShape
                    case 'circle'
                        Screen('FillOval', window, stimColor, [left, top, right, bottom]);  % 绘制圆形
                    case 'square'
                        Screen('FillRect', window, stimColor, [left, top, right, bottom]);  % 绘制方形
                end
                
                % 绘制标签（显示中文标签）
                Screen('TextSize', window, 90);
                labelIndex = find(strcmp(labelEnglish, currentLabel));  % 获取对应的中文标签索引
                DrawFormattedText(window, double(labelChinese{labelIndex}), 'center', shapePositions(2, 2), stimColor); % 标签位置：注视点下方
            end
          
            % ★ v4 修正 #2/#3：注视点期间（刺激 onset 之前）的 f/j 按键记为"抢按"
            %   这一段在 KbCheck 版里根本没被读取过，只有 KbQueue 拿得到
            [nPreKey, nPreEsc] = kqCountPresses();
            if nPreEsc > 0, escAbort(); end
            prematurePress = double(nPreKey > 0);
        if prematurePress > 0
            % ★ v4.5（D79）：抢按已经记进 premature_press，必须从队列里清掉。
            %   否则这一按会在下面的刺激期 kqFirstPressUntil 里被当成"反应"，得到
            %   负的反应时（pressAbs − stimulusFlipTime < 0），并让 stimulus_dur_actual
            %   与"按键后下一帧"对不上（2026-10-18 无屏幕全程冒烟实测到）。
            KbQueueFlush();
        end

            % 刷新屏幕并记录刺激呈现时间
            stimulusFlipTime = Screen('Flip', window); % 显示注视点、形状和标签，并记录刺激呈现时间
            
            % ★ 反应窗口自【刺激 onset】起算：截止 = stimulusFlipTime + W
            %   response/responseTime 在此初始化，随后 刺激期/掩蔽期/空白 三段全程轮询键盘
            response = NaN;       % 尚未反应时保持 NaN（漏答 → Response 缺失、Correct 记为 NaN）
            responseTime = NaN;   % 反应时 = 按键时刻 − 刺激 onset（秒）

            % 2a. 刺激呈现 Ttrial：用 KbQueue 采集（刺激期按键从此会被记录，不再丢失）
            [respKey, respAbs, nEsc] = kqFirstPressUntil(stimulusFlipTime + Ttrial, stimulusFlipTime);   % ★ v4.6：忽略 onset 之前的键
            if nEsc > 0, escAbort(); end
            if ~isempty(respKey)
                response = respKey;                            % 记录按键
                responseTime = respAbs - stimulusFlipTime;     % 反应时（自刺激 onset）
                % ★ D5：刺激期内按键即结束刺激 ⇒ 实际呈现 = min(T, RT)
            end

            % 刺激呈现检查Esc键
            checkEscape(); 

            % 3. 掩蔽/空白段 200 ms（M=1 显示掩蔽图；M=0 显示空白；时长 maskDuration 见文件开头）
            if M == 1
                % ★ Stage 1 修正 #1：纹理已在开场一次性预加载，此处只选句柄与矩形（无磁盘 I/O）
                if strcmp(currentLabel, 'stranger')
                    maskIdx = randi(numel(strangerMaskTex));
                    Screen('DrawTexture', window, strangerMaskTex(maskIdx), [], strangerMaskRect{maskIdx});
                elseif strcmp(currentLabel, 'self')
                    maskIdx = randi(numel(selfMaskTex));
                    Screen('DrawTexture', window, selfMaskTex(maskIdx), [], selfMaskRect{maskIdx});
                end
                maskFlipTime = Screen('Flip', window); % 显示掩蔽刺激
            else
                maskFlipTime = Screen('Flip', window); % 无掩蔽：翻到空白屏
            end
            % ★ v4 修正 #3：记录真实时间戳（名义 T 与实际 T 的差只能靠这几个量看出来）
            maskOnsetActual      = maskFlipTime;   % 掩蔽（或空白）真正上屏的时刻
            stimulusOffsetActual = maskFlipTime;   % 刺激离开屏幕的时刻 = 掩蔽 onset
            stimulusDurActual    = stimulusOffsetActual - stimulusFlipTime;  % 刺激实际在屏时长
            stimulusFrames       = round(stimulusDurActual / FlipIntv);      % 折算成帧数

            % 3b. 掩蔽期【不读】KbQueue：按键留在队列里，由后面的反应窗口段一次性取走
            %     （若在段边界就取走，会吞掉"掩蔽末期按下、其实属于反应窗口"的按键；
            %       而驱动打的时间戳本身就能还原它究竟发生在哪一段）
            %     Esc 仍由 checkEscape（KbCheck 与 KbQueue 互不影响）每 5 ms 检查一次
            while GetSecs() - maskFlipTime < maskDuration
                checkEscape();
                WaitSecs(0.005);
            end
            checkEscape();
        
            % 4. 反应窗口剩余部分：空白屏，直到 stimulusFlipTime + W（刺激/掩蔽期已按键则立即进入反馈）
            % 显示空白屏并记录flip时间
            responseFlipTime = Screen('Flip', window); 
        
            % 说明：response/responseTime 已在刺激 onset 处初始化，此处不得重置，
            %       否则刺激期/掩蔽期记录到的按键会被清掉（漏答时 response 保持 NaN）
            
            % 等待按键输入或超时：截止 = 刺激 onset + Wtrial
            % （若刺激期/掩蔽期已按键，isnan(responseTime) 为假，直接进入反馈）
            if isnan(responseTime)
                [respKey, respAbs, nEsc] = kqFirstPressUntil(stimulusFlipTime + Wtrial, stimulusFlipTime);   % ★ v4.6：忽略 onset 之前的键
                if nEsc > 0, escAbort(); end
                if ~isempty(respKey)
                    response = respKey;
                    responseTime = respAbs - stimulusFlipTime;
                end
            end

            % ★ v4 修正 #3：判定 timeout / responded_by_deadline（截止之后的按键不算反应）
            % ★ v4.5（D79）：反应时必须严格为正。驱动时间戳早于刺激 onset 的按键仍属抢按，
            %   不能算本试次反应（否则 RT 为负，stimulus_dur_actual 也会对不上）。
            if ~isnan(responseTime) && responseTime <= 0
                prematurePress = 1;
                response = NaN;
                responseTime = NaN;
            end
            respondedByDeadline = double(~isnan(responseTime) && responseTime <= Wtrial);
            timeout = double(~respondedByDeadline);
            if ~respondedByDeadline
                response = NaN;
                responseTime = NaN;
            end
            if isnan(response)
                respStr = 'NA';     % 未响应统一写 NA（Stage 1 额外要求：不写字面 0 / 空串）
            else
                respStr = char(response);
            end
    
            % 若无按键响应：response 保持 NaN、responseTime 保持 NaN，下方 Correct 记为 NaN
    
            % 列:1.被试组别, 2.编号, 2.性别, 3.年龄, 4.利手, 5.实验阶段, 6.试次数, 7.试次形状, 8.试次标签, 9.正确的键, 10.被试按键, 11.反应时, 12.是否正确
            % 存储试次数据
            data{trialIndex, 1} = groupID;
            data{trialIndex, 2} = subjectID;
            data{trialIndex, 3} = gender;
            data{trialIndex, 4} = age;
            data{trialIndex, 5} = handedness;
            data{trialIndex, 6} = "formal"; % 存储实验阶段
            data{trialIndex, 7} = trialIndex; % 存储试次编号
            data{trialIndex, 8} = P; % 存储练习试次数量
            data{trialIndex, 9} = Ttrial; % 存储本试次的刺激呈现时间
            data{trialIndex, 10} = Wtrial;   % 存储本 block 的反应窗口
            data{trialIndex, 11} = currentShape; % 存储试次形状
            data{trialIndex, 12} = string(currentLabel); % 存储试次标签
            data{trialIndex, 13} = char(correctKey);   % 存储正确按键
            data{trialIndex, 14} = respStr;            % 存储被试按键（未响应为 'NA'）
            data{trialIndex, 15} = responseTime; % 存储反应时（单位：秒）
        
            % 判断是否正确
            if isnan(response)  % 如果没有响应（response 保持初值 NaN）
                data{trialIndex, 16} = NaN; % 无反应
            elseif strcmp(response, correctKey)  % 如果响应正确
                data{trialIndex, 16} = 1; % 正确
                correctCount = correctCount + 1; % 正确计数加1
            else  % 如果响应错误
                data{trialIndex, 16} = 0; % 错误
            end

            % ★ v4 修正 #3：新增 9 列（时间戳与判定标记；block 记当前组号）
            data{trialIndex, 17} = b;                    % block
            data{trialIndex, 18} = prematurePress;       % premature_press：注视期抢按
            data{trialIndex, 19} = timeout;              % timeout：截止时仍无有效按键
            data{trialIndex, 20} = respondedByDeadline;  % responded_by_deadline
            data{trialIndex, 21} = stimulusFlipTime;     % stimulus_onset_actual（绝对 GetSecs）
            data{trialIndex, 22} = stimulusOffsetActual; % stimulus_offset_actual
            data{trialIndex, 23} = maskOnsetActual;      % mask_onset_actual
            data{trialIndex, 24} = stimulusDurActual;    % stimulus_dur_actual（秒）
            data{trialIndex, 25} = stimulusFrames;       % stimulus_frames（实际帧数）

            % 记录每次反应时间
            if ~isnan(responseTime)
                responseTimes = [responseTimes, responseTime]; % 将有效的反应时间加入数组
            end
            
            % 写入数据到文件（25 列；列 14 直接用 respStr，避免 char(NaN) 写出 NUL 字节）
            fprintf(fileID, ['%d\t%d\t%d\t%d\t%d\t%s\t%d\t%d\t%.6f\t%.6f\t%s\t%s\t%s\t%s\t%.3f\t%d\t' ...
                '%d\t%d\t%d\t%d\t%.6f\t%.6f\t%.6f\t%.6f\t%d\n'], ...
                data{trialIndex, 1}, data{trialIndex, 2}, data{trialIndex, 3}, data{trialIndex, 4}, ...
                data{trialIndex, 5}, data{trialIndex, 6}, data{trialIndex, 7}, data{trialIndex, 8}, ...
                data{trialIndex, 9}, data{trialIndex, 10}, data{trialIndex, 11}, data{trialIndex, 12}, ...
                data{trialIndex, 13}, respStr, data{trialIndex, 15}, data{trialIndex, 16}, ...
                data{trialIndex, 17}, data{trialIndex, 18}, data{trialIndex, 19}, data{trialIndex, 20}, ...
                data{trialIndex, 21}, data{trialIndex, 22}, data{trialIndex, 23}, data{trialIndex, 24}, ...
                data{trialIndex, 25});
    
            % 更新trialIndex
            trialIndex = trialIndex + 1;  % 确保在每次循环后trialIndex递增

        end

    % 计算当前block的正确率
    accuracy = correctCount / blockTrials;  % 正确率 = 正确回答数 / block总试次数
    % 平均反应时
    avgRT = mean(responseTimes);  
    
    % 指导语字体大小
    Screen('TextSize', window, 30); 
    
    % 显示当前block的正确率和平均反应时
    message1 = sprintf('正确率: %.2f%% ', accuracy * 100);
    message2 = sprintf('平均反应时: %.3f 秒', avgRT);
    message3 = sprintf('按回车键进入休息');

    DrawFormattedText(window, double(message1), 'center', centerY - 150, stimColor); % 显示正确率
    DrawFormattedText(window, double(message2), 'center', centerY, stimColor); % 显示正确率
    DrawFormattedText(window, double(message3), 'center', centerY + 150, stimColor); % 显示正确率
    
    Screen('Flip', window); % 刷新屏幕显示

    % 等待被试按回车键继续
    waitForSpace = true;
    waitForSpaceRelease();
    while waitForSpace
        [keyIsDown, ~, keyCode] = KbCheck;
        if keyIsDown
            % 查找按下的键
            pressedKey = find(keyCode);  % 查找按下的键的索引
            if any(pressedKey == KbName('return'))  % 检查是否按下空格键
                waitForSpace = false;  % 按下空格键后跳出循环，继续实验
            end
        end
    end

    % 指导语字体大小
    Screen('TextSize', window, 30); 

    % 每个block结束后，提示休息并等待按空格键继续
    restMessage = double('休息中，请按空格键继续。');
    DrawFormattedText(window, restMessage, 'center', 'center', stimColor);
    Screen('Flip', window);  % 显示休息提示
    
    % 等待被试按空格键继续
    waitForSpace = true;
    waitForSpaceRelease();
    while waitForSpace
        [keyIsDown, ~, keyCode] = KbCheck;
        if keyIsDown
            % 查找按下的键
            pressedKey = find(keyCode);  % 查找按下的键的索引
            if any(pressedKey == KbName('space'))  % 检查是否按下空格键
                waitForSpace = false;  % 按下空格键后跳出循环，继续实验
            end
        end
    end
end

%% 结束
dline1 = '已完成所有实验，';
dline2 = '感谢您的参与。';
dline3 = '按回车键结束实验。';

DrawFormattedText(window, double(dline1), 'center', centerY - 100, stimColor); % 第一行
DrawFormattedText(window, double(dline2), 'center', centerY, stimColor); % 第二行
DrawFormattedText(window, double(dline3), 'center', centerY + 100, stimColor); % 第三行

Screen('Flip', window);

% 等待被试按空格键继续
waitForSpace = true;
waitForSpaceRelease();
while waitForSpace
    [keyIsDown, ~, keyCode] = KbCheck;
    if keyIsDown
        % 查找按下的键
        pressedKey = find(keyCode);  % 查找按下的键的索引
        if any(pressedKey == KbName('return'))  % 检查是否按下空格键
            waitForSpace = false;  % 按下空格键后跳出循环，继续实验
        end
    end
end

%% 保存数据
% ★ v4：新增 9 列（顺序必须与上方 fprintf 写出的表头完全一致）
columnNames = {'groupID', 'subjectID', 'gender', 'age', 'handedness', 'stage', 'trialID', 'P', 'T', 'W', ...
    'Shape', 'Label', 'CorrectKey', 'Response', 'RT', 'Correct', ...
    'block', 'premature_press', 'timeout', 'responded_by_deadline', ...
    'stimulus_onset_actual', 'stimulus_offset_actual', 'mask_onset_actual', ...
    'stimulus_dur_actual', 'stimulus_frames'};
% ★ v4.4：cell → table 一次性转换（char 列转 string，去掉补齐空格；见 exp_data_table.m）
if size(data, 1) ~= trialIndex - 1
    warning('Exp_Design_Formal:rowCount', ...
        '累积 %d 行，但 trialIndex-1 = %d —— 有试次没写进内存表，请检查。', ...
        size(data, 1), trialIndex - 1);
end
dataTable = exp_data_table(data, columnNames);
% 设置保存文件的路径（根据被试编号命名文件）
filename = ['EXP_data_group' num2str(groupID) '_' num2str(subjectID) '.csv'];
% 保存为 CSV 文件
writetable(dataTable, filename);
disp(['Data has been saved to ', filename]);

% ★ v4.5（D79）：关闭逐试次 txt 通道。
%   原来 L487 fopen 之后【从不 fclose】，两个后果：
%   (1) 缓冲区可能还没落盘（MATLAB 直到退出才 flush）⇒ 被试刚做完就想拷走会缺尾部；
%   (2) Windows 下该文件被本进程独占 ⇒ 主试当场移动/上传/用别的软件打开会报
%       「无法从源读取」（2026-10-18 无屏幕全程冒烟实测到）。
if exist('fileID', 'var') && fileID > 0
    fclose(fileID);
    fprintf('长表已关闭并落盘：%s\n', fileName);
end

% 关闭窗口
try, KbQueueRelease(); catch, end   % ★ v4：释放按键事件队列
Screen('CloseAll');

%% Functions
function pairingRules = getPairingRules(subjectID)
    % 根据被试编号决定刺激分配方式    
    % 通过 mod(subjectID, 4) 来判断被试编号的规则，编号可以是 0, 1, 2, 3
    modResult = mod(subjectID, 4);
    
    % 定义所有规则，四种情况
    rules = { ...
        % 4的倍数, f是匹配, j是不匹配
        'square', struct('self', 'f', 'stranger', 'j'), 'circle', struct('self', 'j', 'stranger', 'f'); ...
        % 4k+1 的奇数, f是匹配, j是不匹配
        'square', struct('self', 'j', 'stranger', 'f'), 'circle', struct('self', 'f', 'stranger', 'j'); ...
        % 其他偶数, j是匹配, f是不匹配
        'square', struct('self', 'j', 'stranger', 'f'), 'circle', struct('self', 'f', 'stranger', 'j'); ...
        % 4k+3 的奇数, j是匹配, f是不匹配
        'square', struct('self', 'f', 'stranger', 'j'), 'circle', struct('self', 'j', 'stranger', 'f')  ... 
    };

    % 通过 modResult 查找对应的规则
    pairingRules = struct(rules{modResult + 1, :});
end

function key = getMatchKey(subjectID)
    % 根据 subjectID 返回匹配按键，按循环模式 {f, j, j, f}
    % 输入: subjectID (正整数)
    % 输出: key (匹配按键 'f' 或 'j')
    
    % 检查输入是否为正整数
    if subjectID <= 0 || mod(subjectID, 1) ~= 0
        error('subjectID 必须是正整数');
    end
    
    % 定义循环模式
    matchKeys = {'f', 'j', 'j', 'f'};
    
    % 通过取模计算模式索引
    index = mod(subjectID - 1, length(matchKeys)) + 1; % 映射到 1-4 范围
    key = matchKeys{index};
end

function pixs = deg2pix(degree,inch,pwidth,vdist) 

screenWidth = inch*2.54/sqrt(1+11.81/15.75);
pix=screenWidth/pwidth; 
pixs = round(2*tan((degree/2)*pi/180) * vdist / pix); 

end

function code = resolveEscKeyCode()
    % Esc 键码只解析一次；对"统一键名"开关的两种命名方案都兼容，避免整场实验因此崩溃
    % （本机实测：未开启 UnifyKeyNames 时只认 'esc'；开启后只认 'ESCAPE'/'escape'）
    % ★ v4：KbQueue 的键掩码与 checkEscape 必须用【同一个】键码，故抽出本函数共用
    persistent escCode
    if isempty(escCode)
        escCode = [];
        candidates = {'esc', 'ESCAPE', 'escape'};
        for q = 1:numel(candidates)
            try
                v = KbName(candidates{q});
                if ~isempty(v) && isnumeric(v)
                    escCode = v;
                    break
                end
            catch
                % 该命名方案不认这个名字 → 试下一个
            end
        end
        if isempty(escCode)
            escCode = 27;   % 终极回退：两种命名方案下 Esc 的物理键码都是 27
        end
    end
    code = escCode;
end

function escAbort()
    % Esc 中止：先释放按键队列 → 关屏 → 抛错停下
    % （sca 之后若继续跑，后续 Screen 调用会接连崩溃，所以必须立刻停下）
    disp('实验结束！');
    try, KbQueueRelease(); catch, end
    sca;
    error('实验已中止（按下了 Esc 键）。');
end

function checkEscape()
    % 边界守卫：Esc 即可中止。KbCheck 与 KbQueue 互不影响，可与队列并存。
    [keyIsDown, ~, keyCode] = KbCheck;
    if keyIsDown && keyCode(resolveEscKeyCode())  % 如果按下Esc键
        escAbort();
    end
end

function [nKey, nEsc] = kqCountPresses()
    % 把队列里【已经从发生到现在】的按键取走并计数，不等待
    %   nKey : 本区间内 f/j 的按下次数（KbQueueCheck 每个键只报"第一次"，故实为 0/1）
    %   nEsc : 本区间内 Esc 的按下次数
    % 用途：trial 开头 KbQueueFlush 之后、刺激 onset 之前调用 ⇒ 得到"注视期抢按"
    nKey = 0; nEsc = 0;
    fCode = KbName('f'); jCode = KbName('j'); escCode = resolveEscKeyCode();
    [pressed, firstPress] = KbQueueCheck();
    if ~pressed
        return
    end
    idx = find(firstPress > 0);
    for m = 1:numel(idx)
        if idx(m) == escCode
            nEsc = nEsc + 1;
        elseif idx(m) == fCode || idx(m) == jCode
            nKey = nKey + 1;
        end
    end
end

function [key, when, nEsc] = kqFirstPressUntil(deadline, tFloor)
    % 用 KbQueue 一直等到 GetSecs() >= deadline，返回该区间内【最早】的 f/j 按键
    %   key  : 'f' / 'j'；本区间没有 f/j 则为 ''（空 char）
    %   when : 该按键的【绝对】GetSecs 时间戳（秒）；没有则为 NaN
    %   nEsc : 本区间内 Esc 的按下次数（>0 时由调用方调用 escAbort）
    %   tFloor: 【可选】下界（绝对 getsecs 秒）。只接受 tFloor < 时间戳 <= deadline 的按键。
    %           ★ v4.6：反应窗口的物理起点是刺激 onset，而 onset 之前按下的键（注视末梢的抢按，
    %           隔着一次 vsync 等待才有机会被读到）不属于本试次反应。传 stimulusFlipTime 即可
    %           把这类键挡在窗口之外，否则它们会把刺激在 0–1 帧内敲掉、把试次变成漏答。
    %
    % 为什么这样写：
    %  (1) KbQueueCheck 返回的是【驱动在按键发生那一刻打的时间戳】，
    %      因此下面的 WaitSecs(0.001) 只决定"多快发现按键"，既不影响 RT 精度也不丢事件
    %      —— 这正是 KbCheck 轮询做不到的（轮询间隙内的短按键会整段消失）。
    %  (2) 循环退出后【再补读一次】：兜住"刚好在 deadline 之前按下、上一次轮询还没看到"
    %      的那次按键；补读时只接受时间戳 <= deadline 的按键，晚于 deadline 的按键
    %      按定义已经不是本窗口的反应，丢掉即可（本函数是本试次最后一段，不会有下一段要接）。
    if nargin < 2 || isempty(tFloor), tFloor = -Inf; end
    key = ''; when = NaN; nEsc = 0;
    fCode = KbName('f'); jCode = KbName('j'); escCode = resolveEscKeyCode();
    while GetSecs() < deadline
        [pressed, firstPress] = KbQueueCheck();
        if pressed
            [key, when, nEsc] = kqScan(firstPress, deadline, fCode, jCode, escCode, tFloor);
            if nEsc > 0 || ~isempty(key)
                return
            end
        end
        WaitSecs(0.001);
    end
    [pressed, firstPress] = KbQueueCheck();   % 补读（见上文 (2)）
    if pressed
        [key, when, nEsc] = kqScan(firstPress, deadline, fCode, jCode, escCode, tFloor);
    end
end

function [key, when, nEsc] = kqScan(firstPress, deadline, fCode, jCode, escCode, tFloor)
    % 在一次 KbQueueCheck 的返回里挑出【最早的 f/j 按键】与 Esc 次数
    key = ''; when = NaN; nEsc = 0;
    idx = find(firstPress > 0);
    if isempty(idx)
        return
    end
    [~, ord] = sort(firstPress(idx));   % 按驱动时间戳排序 ⇒ 保证取到最早的那个
    idx = idx(ord);
    for m = 1:numel(idx)
        if idx(m) == escCode
            nEsc = nEsc + 1;
        elseif isempty(key) && (idx(m) == fCode || idx(m) == jCode) ...
                && firstPress(idx(m)) > tFloor && firstPress(idx(m)) <= deadline
            if idx(m) == fCode
                key = 'f';
            else
                key = 'j';
            end
            when = firstPress(idx(m));
        end
    end
end




         
 

function waitForSpaceRelease()
% v4.7（D90）：直到所有键都松开才返回（最多等 5 s，防止键卡住时死结）。
%   目的：挡住"上一屏的确认键还没松开"穿透下一屏的空格等待——症状是指导语一闪而过。
%   用法：放在每个 `while waitForSpace` / `while waitingForSpace` 之前。
    t0 = GetSecs();
    while GetSecs() - t0 < 5
        [keyIsDown, ~, ~] = KbCheck;
        if ~keyIsDown
            return
        end
        WaitSecs(0.005);
        checkEscape();
    end
end
