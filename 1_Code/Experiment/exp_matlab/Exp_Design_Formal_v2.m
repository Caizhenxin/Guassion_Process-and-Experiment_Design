%% Exp_Design_Formal_v2.m
% 自我-联结匹配任务 (Self-Matching Task, 参照 Sui et al., 2012) 正式数据采集程序 —— v2
% =============================================================================
% v2 = Exp_Design_Formal.m 的【最小改动版】，只改一处逻辑：按键采集方式
%   旧版(v1)：只在反应窗口（掩蔽结束后）用 KbCheck 轮询 → 刺激呈现期/掩蔽期的按键会丢失
%   本版(v2)：从刺激 onset 起用 KbQueue 事件队列全程记录 → 刺激期按键也会被记录，
%            并用 Premask 标记"是否发生在掩蔽结束前"，分析时可自由取舍
% RT 口径不变（自刺激 onset 起算）；时间轴、试次数、练习量、平衡规则、指导语均与 v1 一致
% 新增数据列（追加在原 16 列之后）：Mask, Link, MatchKey, Premask, NKeyBeforeMask, NKeyTotal
% 输出文件名带 _v2 后缀，避免与 v1 数据混淆
% =============================================================================
% 自我-联结匹配任务 (Self-Matching Task, 参照 Sui et al., 2012) 正式数据采集程序
% -----------------------------------------------------------------------------
% 用途  ：9 个条件 × 每组 ≥20 名被试的正式采集（组间设计，每名被试只跑一个条件）
%         组1-6、组8-9 = 8 个【有掩蔽】条件；组7 = 【无掩蔽】条件（组5参数去掉掩蔽）
% 相对旧版 experiment_formal_newcon.m 的改动：
%   (1) conditions 表增加第 4 列 M（掩蔽开关）：M=1 呈现 200ms 掩蔽图（与原程序行为一致）
%       M=0 掩蔽段翻空白屏 200ms（总时间轴/反应窗口/RT 口径不变，仅去掉掩蔽刺激）
%   (2) 组7 由旧版"程序崩溃后接着做"应急行（P0/T100/W1100/掩蔽）改为【无掩蔽组7】
%       = P8/T100ms/W1100ms/M0（与组5唯一差别是掩蔽，deadline 同为 T+W=1.2s）
%   (3) 程序开头增加主试确认回显，防止填错组别/编号
% 组别-条件速查（P=练习试次数 | T=刺激呈现时间 | W=反应窗口 | M=1掩蔽/M=0无掩蔽）
%   组1 P0  T30ms   W300ms  M1   组4 P120 T80ms   W600ms  M1   组7 P8  T100ms  W1100ms M0
%   组2 P0  T30ms   W600ms  M1   组5 P8  T100ms  W1100ms M1   组8 P120 T30ms  W800ms  M1
%   组3 P120 T30ms  W600ms  M1   组6 P120 T500ms W1500ms M1   组9 P120 T80ms  W800ms  M1
% 被试编号规则：组内从 1 连续递增、不跳号（奇偶决定形状-标签配对方向；
%   编号 mod4 = 1或0 → 匹配键 f；mod4 = 2或3 → 匹配键 j）
% 数据输出：程序当前文件夹下 EXP_data_group{组别}_{编号}_v2.csv 和 exp_group{组别}_subject{编号}_v2.txt
% -----------------------------------------------------------------------------
% 采集配置（默认值 = v1 行为，除按键采集范围外无差异）
REJECT_PREMASK = 0;   % 0 = 掩蔽结束前的按键也记录（本版目的，用 Premask 标记）
                      % 1 = 抢按不计入，试次继续等待掩蔽结束后的按键（严格"掩蔽后反应"）
FILE_SUFFIX = '_v2';  % 数据文件名后缀

Screen('Preference', 'SkipSyncTests', 0);
KbName('UnifyKeyNames');   % 统一键名，保证 f/j 在不同键盘布局下名字一致
InitializeMatlabOpenGL;

%% 被试基础信息
% 初始化一个空的表格
data = table();

% 基本信息收集
prompt = {'被试组别', '被试编号', '性别[1 = 女, 2 = 男]', '年龄', '惯用手[1 = 左, 2 = 右]'};
title = '实验信息'; % 标题
definput = {'','', '','',''};% 默认值
% 使用 inputdlg 函数弹出对话框，收集数据
userInput = inputdlg(prompt, title, 1, definput);

% 将收集到的数据转换为合适的类型并存入表格
groupID = str2double(userInput{1});    % 被试组别
subjectID = str2double(userInput{2});  % 被试编号
gender = str2double(userInput{3});     % 性别
age = str2double(userInput{4});        % 年龄
handedness = str2double(userInput{5}); % 惯用手

% 主试确认回显：核对弹窗填写无误后再继续（填错请 Ctrl+C 终止后重开）
fprintf('==================================================\n');
fprintf(' 请主试核对本次实验信息：\n');
fprintf('   被试组别 groupID   = %d\n', groupID);
fprintf('   被试编号 subjectID = %d\n', subjectID);
fprintf('   性别(gender)       = %d  [1=女, 2=男]\n', gender);
fprintf('   年龄(age)          = %d\n', age);
fprintf('   惯用手(handedness) = %d  [1=左, 2=右]\n', handedness);
fprintf(' 确认无误请按回车继续；有误请 Ctrl+C 终止，重新运行。\n');
fprintf('==================================================\n');
input('', 's');

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
% （与 v1 相同；仅当 PTB 同步测试失败导致开窗报错时，打印真实原因并自动以
%   SkipSyncTests=1 重试一次，避免"See error message printed above"式的中断）
try
    [window, windowRect] = Screen('OpenWindow', screenNumber, [128, 128, 128], rect);
catch errOpen
    fprintf(2, '\n开窗失败：%s\n', errOpen.message);
    fprintf(2, '（PTB 的具体原因已打印在上方，常见为 SYNCHRONIZATION FAILURE / VBL 同步失败）\n');
    fprintf(2, '自动改用 SkipSyncTests=1 重试一次 ...\n');
    try, Screen('CloseAll'); catch, end %#ok<CTCH>
    Screen('Preference', 'SkipSyncTests', 1);
    [window, windowRect] = Screen('OpenWindow', screenNumber, [128, 128, 128], rect);
    fprintf(2, '*** 已用 SkipSyncTests=1 打开窗口：本会话未通过显示同步测试。***\n');
end
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
    linkName = 'square=self,circle=stranger';
else   % 奇数编号的被试
    correctOrder = correctPairs_1;  % 反转正确的匹配顺序
    linkName = 'circle=self,square=stranger';
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
selfMaskImages = {'self10-1.png', 'self10-2.png', 'self10-3.png', 'self10-4.png', 'self10-5.png'};
strangerMaskImages = {'stranger10-1.png', 'stranger10-2.png', 'stranger10-3.png', 'stranger10-4.png', 'stranger10-5.png'};

% 自定义实验条件(P,T,W,M)：M=1 有掩蔽；M=0 无掩蔽（掩蔽段翻空白，时间轴不变）
conditions = [
    0, 0.03, 0.3, 1;   % 第一组条件 (P=0, T=30ms, W=300ms,  掩蔽)
    0, 0.03, 0.6, 1;  % 第二组条件 (P=0, T=30ms, W=600ms,  掩蔽)
    120, 0.03, 0.6, 1;  % 第三组条件 (P=120, T=30ms, W=600ms,  掩蔽)
    120, 0.08, 0.6, 1;  % 第四组条件 (P=120, T=80ms, W=600ms,  掩蔽)
    8, 0.1, 1.1, 1;  % 第五组条件 (P=8, T=100ms, W=1100ms, 掩蔽)
    120, 0.5, 1.5, 1;  % 第六组条件 (P=120, T=500ms, W=1500ms, 掩蔽)
    8, 0.1, 1.1, 0;  % 第七组条件 (P=8, T=100ms, W=1100ms, 无掩蔽) ★ 与组5唯一差别=掩蔽
    120, 0.03, 0.8, 1; % 第八组条件 (P=120, T=30ms, W=800ms,  掩蔽)
    120, 0.08, 0.8, 1; % 第九组条件 (P=120, T=80ms, W=800ms,  掩蔽)
];
currentCondition = conditions(groupID, :);  % 每组一个条件

% 练习试次数量 P
P = currentCondition(1);

% 刺激呈现时间 T
T = currentCondition(2);

% 反应窗口 W
W = currentCondition(3);

% 掩蔽开关 M：1=有掩蔽，0=无掩蔽
M = currentCondition(4);

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
fileName = sprintf('exp_group%d_subject%d%s.txt', groupID, subjectID, FILE_SUFFIX);

% 打开文件，用于保存数据，'a' 表示追加模式，确保每个 trial 保存一行数据
fileID = fopen(fileName, 'a+');
if fileID == -1
    error('无法打开文件');
end

% 在文件头部添加列标题（如果文件是空的）
% 前 16 列为 v1 原有列，后 6 列为 v2 新增（掩蔽/联结/匹配键/抢按标记/按键计数）
if ftell(fileID) == 0
    fprintf(fileID, ['groupID\tsubjectID\tgender\tage\thandedness\tstage\ttrialID\tP\tT\tW\t' ...
        'Shape\tLabel\tCorrectKey\tResponse\tRT\tCorrect\t' ...
        'Mask\tLink\tMatchKey\tPremask\tNKeyBeforeMask\tNKeyTotal\n']);
end

% ★ v2 核心改动：按键事件队列（KbQueue）——整场实验只创建一次，每个试次开始时清空
%    这样刺激 onset 之后的所有按键（含刺激呈现期、掩蔽期）都会被带时间戳记录下来
keysOfInterest = [KbName('f'), KbName('j'), KbName('ESCAPE')];
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
    
        % 每个trial开始时，立即检查Esc键
        checkEscape();

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
      
        % 刷新屏幕并记录刺激呈现时间
        stimulusFlipTime = Screen('Flip', window); % 显示注视点、形状和标签，并记录刺激呈现时间

        % ★ v2：从刺激 onset 这一刻起开始采集按键（清空队列，丢弃注视期按键）
        KbQueueFlush();
        
        % 等待刺激呈现时间 T
        while GetSecs() - stimulusFlipTime < T
            % 等待持续时间
        end

        % 刺激呈现检查Esc键
        checkEscape(); 

        % 3. 掩蔽/空白段 200 ms（M=1 显示掩蔽图；M=0 显示空白，总时间轴保持不变）
        maskDuration = 0.2; % 掩蔽/空白段持续时间 (秒)
        if M == 1
            % 根据标签类别随机选择掩蔽图片并显示
            if strcmp(currentLabel, 'stranger')
                selectedMaskImage = strangerMaskImages{randi(numel(strangerMaskImages))};
                maskImage = imread(selectedMaskImage);  % 加载 stranger 掩蔽图片
            elseif strcmp(currentLabel, 'self')
                selectedMaskImage = selfMaskImages{randi(numel(selfMaskImages))};
                maskImage = imread(selectedMaskImage);  % 加载 self 掩蔽图片
            end
            
            % 获取图片的原始大小
            [maskHeight, maskWidth, ~] = size(maskImage);  % 获取图片的高度和宽度
            
            % 位置
            maskRect = [0 0 maskWidth maskHeight]; % 噪声矩形框
            maskRect = CenterRectOnPoint(maskRect, centerX, centerY + distance); % 在标签的位置显示
            
            % 将图片转换为纹理
            maskImageTexture = Screen('MakeTexture', window, maskImage);  % 将图片转换为纹理
            
            % 绘制并显示掩蔽刺激
            Screen('DrawTexture', window, maskImageTexture, [], maskRect); % 在屏幕上绘制噪声掩蔽
            maskFlipTime = Screen('Flip', window); % 显示掩蔽刺激
        else
            maskFlipTime = Screen('Flip', window); % 无掩蔽：翻到空白屏
        end
        maskOffsetTime = maskFlipTime + maskDuration;   % 掩蔽/空白段结束时刻
        while GetSecs() - maskFlipTime < maskDuration
            % 等待 200 ms
        end
        % 掩蔽刺激呈现检查Esc键
        checkEscape(); 
    
        % 4. 显示空白屏，等待键盘反应，持续反应窗口 W - maskDuration
        % 显示空白屏并记录flip时间
        responseFlipTime = Screen('Flip', window); 
    
        % ★ v2：按键采集改用事件队列（KbQueue）
        %   队列自刺激 onset 起持续记录 → 刺激呈现期/掩蔽期按下的键也会被读到；
        %   deadline 与 v1 完全一致（responseFlipTime + W - maskDuration）；
        %   无反应时 response/responseTime 保持 v1 的 NaN 约定
        [response, responseTime, premaskFlag, nBeforeMask, nTotalKeys] = ...
            collectResponse(stimulusFlipTime, maskOffsetTime, responseFlipTime, W, maskDuration, REJECT_PREMASK);

        % 空白屏呈现检查Esc键
        checkEscape(); 

        % 如果没有按键响应，则保持response为NaN（此时response默认是NaN，无需额外赋值）

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
        data{trialIndex, 14} = char(response);     % 存储被试按键
        data{trialIndex, 15} = responseTime; % 存储反应时（单位：秒）
        data{trialIndex, 17} = M;                    % v2 新增：掩蔽开关 1/0
        data{trialIndex, 18} = linkName;             % v2 新增：联结方向
        data{trialIndex, 19} = matchKey;             % v2 新增：匹配键 f/j
        data{trialIndex, 20} = double(premaskFlag);  % v2 新增：1 = 掩蔽结束前按下（抢按）
        data{trialIndex, 21} = nBeforeMask;          % v2 新增：掩蔽结束前按键次数
        data{trialIndex, 22} = nTotalKeys;           % v2 新增：本试次按键总次数
    
        % 判断是否正确
        if isempty(response)  % 如果没有响应
            data{trialIndex, 16} = NaN; % 无反应
        elseif strcmp(response, correctKey)  % 如果响应正确
            data{trialIndex, 16} = 1; % 正确
        else  % 如果响应错误
            data{trialIndex, 16} = 0; % 错误
        end
    
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

        % 写入数据到文件（v1 的 16 列 + v2 新增 6 列）
        fprintf(fileID, ['%d\t%d\t%d\t%d\t%d\t%s\t%d\t%d\t%.1f\t%.1f\t%s\t%s\t%s\t%s\t%.3f\t%d\t' ...
            '%d\t%s\t%s\t%d\t%d\t%d\n'], ...
            data{trialIndex, 1}, data{trialIndex, 2}, data{trialIndex, 3}, data{trialIndex, 4}, ...
            data{trialIndex, 5}, data{trialIndex, 6}, data{trialIndex, 7}, data{trialIndex, 8}, ...
            data{trialIndex, 9}, data{trialIndex, 10}, data{trialIndex, 11}, data{trialIndex, 12}, ...
            data{trialIndex, 13}, data{trialIndex, 14}, data{trialIndex, 15}, data{trialIndex, 16}, ...
            data{trialIndex, 17}, data{trialIndex, 18}, data{trialIndex, 19}, data{trialIndex, 20}, ...
            data{trialIndex, 21}, data{trialIndex, 22});

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
% 设置block的数量
block = 10;
blockTrials = 52;

% 循环多个block
for b = 1:block

    % 记录当前block的正确回答数
    correctCount = 0;

    % 初始化当前block的反应时间数组
    responseTimes = [];

    % 循环一个block
    for y = 1:(blockTrials/length(stimuli))
    
        % 打乱刺激顺序
        stimuli_bin = stimuli(randperm(size(stimuli, 1)), :);

        % 循环bin
        for i = 1:length(stimuli)

            % 每个trial开始时，立即检查Esc键
            checkEscape();

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
            stimuliFrames = round(T / FlipIntv);  % 计算所需的帧数
    
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
          
            % 刷新屏幕并记录刺激呈现时间
            stimulusFlipTime = Screen('Flip', window); % 显示注视点、形状和标签，并记录刺激呈现时间

            % ★ v2：从刺激 onset 这一刻起开始采集按键（清空队列，丢弃注视期按键）
            KbQueueFlush();
            
            % 等待刺激呈现时间 T
            while GetSecs() - stimulusFlipTime < T
                % 等待持续时间
            end

            % 刺激呈现检查Esc键
            checkEscape(); 

            % 3. 掩蔽/空白段 200 ms（M=1 显示掩蔽图；M=0 显示空白，总时间轴保持不变）
            maskDuration = 0.2; % 掩蔽/空白段持续时间 (秒)
            if M == 1
                % 根据标签类别随机选择掩蔽图片并显示
                if strcmp(currentLabel, 'stranger')
                    selectedMaskImage = strangerMaskImages{randi(numel(strangerMaskImages))};
                    maskImage = imread(selectedMaskImage);  % 加载 stranger 掩蔽图片
                elseif strcmp(currentLabel, 'self')
                    selectedMaskImage = selfMaskImages{randi(numel(selfMaskImages))};
                    maskImage = imread(selectedMaskImage);  % 加载 self 掩蔽图片
                end
                
                % 获取图片的原始大小
                [maskHeight, maskWidth, ~] = size(maskImage);  % 获取图片的高度和宽度
                
                % 位置
                maskRect = [0 0 maskWidth maskHeight]; % 噪声矩形框
                maskRect = CenterRectOnPoint(maskRect, centerX, centerY + distance); % 在标签的位置显示
                
                % 将图片转换为纹理
                maskImageTexture = Screen('MakeTexture', window, maskImage);  % 将图片转换为纹理
                
                % 绘制并显示掩蔽刺激
                Screen('DrawTexture', window, maskImageTexture, [], maskRect); % 在屏幕上绘制噪声掩蔽
                maskFlipTime = Screen('Flip', window); % 显示掩蔽刺激
            else
                maskFlipTime = Screen('Flip', window); % 无掩蔽：翻到空白屏
            end
            maskOffsetTime = maskFlipTime + maskDuration;   % 掩蔽/空白段结束时刻
            while GetSecs() - maskFlipTime < maskDuration
                % 等待 200 ms
            end
            % 掩蔽刺激呈现检查Esc键
            checkEscape(); 
        
            % 4. 显示空白屏，等待键盘反应，持续反应窗口 W - maskDuration
            % 显示空白屏并记录flip时间
            responseFlipTime = Screen('Flip', window); 
        
            % ★ v2：按键采集改用事件队列（KbQueue）；deadline 与 v1 完全一致
            [response, responseTime, premaskFlag, nBeforeMask, nTotalKeys] = ...
                collectResponse(stimulusFlipTime, maskOffsetTime, responseFlipTime, W, maskDuration, REJECT_PREMASK);

            % 空白屏呈现检查Esc键
            checkEscape(); 
    
            % 如果没有按键响应，则保持response为NaN（此时response默认是NaN，无需额外赋值）
    
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
            data{trialIndex, 9} = T; % 存储刺激呈现时间
            data{trialIndex, 10} = W; % 存储反应窗口
            data{trialIndex, 11} = currentShape; % 存储试次形状
            data{trialIndex, 12} = string(currentLabel); % 存储试次标签
            data{trialIndex, 13} = char(correctKey);   % 存储正确按键
            data{trialIndex, 14} = char(response);     % 存储被试按键
            data{trialIndex, 15} = responseTime; % 存储反应时（单位：秒）
            data{trialIndex, 17} = M;                    % v2 新增：掩蔽开关 1/0
            data{trialIndex, 18} = linkName;             % v2 新增：联结方向
            data{trialIndex, 19} = matchKey;             % v2 新增：匹配键 f/j
            data{trialIndex, 20} = double(premaskFlag);  % v2 新增：1 = 掩蔽结束前按下（抢按）
            data{trialIndex, 21} = nBeforeMask;          % v2 新增：掩蔽结束前按键次数
            data{trialIndex, 22} = nTotalKeys;           % v2 新增：本试次按键总次数
        
            % 判断是否正确
            if isempty(response)  % 如果没有响应
                data{trialIndex, 16} = NaN; % 无反应
            elseif strcmp(response, correctKey)  % 如果响应正确
                data{trialIndex, 16} = 1; % 正确
                correctCount = correctCount + 1; % 正确计数加1
            else  % 如果响应错误
                data{trialIndex, 16} = 0; % 错误
            end

            % 记录每次反应时间
            if ~isnan(responseTime)
                responseTimes = [responseTimes, responseTime]; % 将有效的反应时间加入数组
            end
            
            % 写入数据到文件（v1 的 16 列 + v2 新增 6 列）
            fprintf(fileID, ['%d\t%d\t%d\t%d\t%d\t%s\t%d\t%d\t%.1f\t%.1f\t%s\t%s\t%s\t%s\t%.3f\t%d\t' ...
                '%d\t%s\t%s\t%d\t%d\t%d\n'], ...
                data{trialIndex, 1}, data{trialIndex, 2}, data{trialIndex, 3}, data{trialIndex, 4}, ...
                data{trialIndex, 5}, data{trialIndex, 6}, data{trialIndex, 7}, data{trialIndex, 8}, ...
                data{trialIndex, 9}, data{trialIndex, 10}, data{trialIndex, 11}, data{trialIndex, 12}, ...
                data{trialIndex, 13}, data{trialIndex, 14}, data{trialIndex, 15}, data{trialIndex, 16}, ...
                data{trialIndex, 17}, data{trialIndex, 18}, data{trialIndex, 19}, data{trialIndex, 20}, ...
                data{trialIndex, 21}, data{trialIndex, 22});
    
            % 更新trialIndex
            trialIndex = trialIndex + 1;  % 确保在每次循环后trialIndex递增
    
        end
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
% v1 的 16 列 + v2 新增 6 列（顺序必须与逐试次写入/存储完全一致）
columnNames = {'groupID', 'subjectID', 'gender', 'age', 'handedness', 'stage', 'trialID', 'P', 'T', 'W', ...
    'Shape', 'Label', 'CorrectKey', 'Response', 'RT', 'Correct', ...
    'Mask', 'Link', 'MatchKey', 'Premask', 'NKeyBeforeMask', 'NKeyTotal'};
data.Properties.VariableNames = columnNames;
% 设置保存文件的路径（根据被试编号命名文件；v2 带 _v2 后缀，便于与 v1 数据区分）
filename = ['EXP_data_group' num2str(groupID) '_' num2str(subjectID) FILE_SUFFIX '.csv'];
% 保存为 CSV 文件
writetable(data, filename);
disp(['Data has been saved to ', filename]);

% 会话小结：让主试直接看到"刺激呈现期按键"被记录了多少（这些试次在 v1 中会变成无反应）
formalMask = (data.stage == "formal");
nPremaskTotal = sum(data.Premask(formalMask) == 1, 'omitnan');
nFormalTotal = sum(formalMask);
nRespTotal = sum(~isnan(data.RT(formalMask)));
fprintf('本会话（正式 %d 试次）：有反应 %d，其中掩蔽结束前按下（抢按）%d 次。\n', ...
    nFormalTotal, nRespTotal, nPremaskTotal);
fprintf('提示：这 %d 次抢按在旧版 Exp_Design_Formal.m 中会因"尚未开始采集"而丢失。\n', nPremaskTotal);

% 关闭文件、按键队列与窗口
if fileID ~= -1
    fclose(fileID);
end
KbQueueStop; KbQueueRelease;
Screen('CloseAll');

%% Functions
function [response, responseTime, premaskFlag, nBeforeMask, nTotalKeys] = ...
        collectResponse(stimulusFlipTime, maskOffsetTime, responseFlipTime, W, maskDuration, REJECT_PREMASK)
% v2 的按键采集函数（v1 用 KbCheck 轮询，本函数改用 KbQueue 事件队列）
%   - 队列自刺激 onset 起持续记录（试次开始时已 KbQueueFlush）
%   - 取"刺激 onset 之后最早的 f/j 按键"作为反应；RT = 按键时刻 − 刺激 onset（与 v1 同口径，
%     且用的是按键事件的真实时间戳，不受轮询间隔影响）
%   - REJECT_PREMASK = 0：掩蔽结束前的按键也生效，premaskFlag 标记为 1（本版的目的）
%   - REJECT_PREMASK = 1：忽略掩蔽结束前的按键，继续等到掩蔽结束后的按键
%   - deadline 与 v1 完全一致：responseFlipTime + (W − maskDuration)
%   - 无反应时 response / responseTime 返回 NaN（与 v1 相同）
    response = NaN;
    responseTime = NaN;
    premaskFlag = 0;
    pressTimes = [];
    pressKeys = {};

    while GetSecs() - responseFlipTime < W - maskDuration
        [pressed, firstPress] = KbQueueCheck();
        if pressed
            idx = find(firstPress > 0);
            for j = 1:numel(idx)
                pressTimes(end + 1) = firstPress(idx(j)); %#ok<AGROW>
                pressKeys{end + 1} = KbName(idx(j));      %#ok<AGROW>
            end
        end

        checkEscape();   % Esc 仍可随时中止

        if ~isempty(pressTimes)
            [~, order] = sort(pressTimes);
            for j = 1:numel(order)
                k = order(j);
                if ~ismember(pressKeys{k}, {'f', 'j'})
                    continue;   % 非 f/j 键忽略
                end
                if pressTimes(k) < maskOffsetTime && REJECT_PREMASK
                    continue;   % 抢按不计入时，继续等待掩蔽后的按键
                end
                response = pressKeys{k};
                responseTime = pressTimes(k) - stimulusFlipTime;   % RT 自刺激 onset 起算
                premaskFlag = double(pressTimes(k) < maskOffsetTime);
                break;
            end
        end
        if ~isnan(responseTime)
            break;   % 已取得有效反应
        end
        WaitSecs(0.001);
    end

    % 本试次（刺激 onset 之后）的 f/j 按键统计
    isFJ = false(1, numel(pressKeys));
    for j = 1:numel(pressKeys)
        isFJ(j) = ismember(pressKeys{j}, {'f', 'j'});
    end
    nTotalKeys = sum(isFJ);
    if isempty(pressTimes)
        nBeforeMask = 0;
    else
        nBeforeMask = sum(isFJ & (pressTimes < maskOffsetTime));
    end
end

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

function checkEscape()
    [keyIsDown, ~, keyCode] = KbCheck;
    if keyIsDown && keyCode(KbName('esc'))  % 如果按下Esc键
        disp('实验结束！');
        sca;  % 关闭屏幕
    end
end




         
 