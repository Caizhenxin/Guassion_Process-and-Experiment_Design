%% keypress_timing_test.m
% -------------------------------------------------------------------------
% 目的
%   用实验设备自证「刺激呈现期间（T 秒内）的按键，硬件与 Psychtoolbox 到底能不能捕捉到」，
%   从而区分两种可能：
%     (1) 实验程序在刺激呈现期没有监听键盘（设计如此，见 Exp_Design_Formal.m 第 425/692 行）
%     (2) 键盘 / 显示器 / 系统硬件故障导致按键丢失
%
% 测试逻辑（同一套刺激时间轴，跑两个阶段）
%   阶段 A —— 复刻当前实验程序的做法：刺激呈现期与掩蔽期不监听，只在反应窗口用 KbCheck 轮询
%            （同时后台用 KbQueue 记录到底按了什么键，仅用于事后比对，不参与判定）
%   阶段 B —— 全程使用 KbQueue（事件队列）监听：从注视点开始就采集所有按键的时间戳
%   若阶段 A 出现"刺激期确实按了、程序没记录"，而阶段 B 同一时刻的按键被完整记录下来，
%   则证明：硬件与 PTB 工作正常，问题只在于程序当时的监听时机。
%
% 用法
%   MATLAB 中： cd 到本文件夹 → 运行  keypress_timing_test
%   主试按屏幕提示操作：每个试次「在刺激（形状+标签）出现期间故意抢按一次 f 或 j」，
%   然后观察命令行输出。
%
% 说明
%   - 本脚本不产生任何数据文件，也不修改 Exp_Design_Formal.m
%   - 时间参数默认模拟第六组（T=500ms, 掩蔽 200ms, W=1500ms）
%   - Esc 可随时退出
% -------------------------------------------------------------------------

Screen('Preference', 'SkipSyncTests', 1);
KbName('UnifyKeyNames');

%% 参数
T          = 0.5;    % 刺激呈现时间（秒）—— 模拟第六组 T=500ms
maskDur    = 0.2;    % 掩蔽/空白段（秒）
W          = 1.5;    % 反应窗口（相对刺激 onset 的截止，秒）
nTrials    = 6;      % 每个阶段的试次数
fixDur     = 0.5;    % 注视点（秒）

keys = [KbName('f'), KbName('j'), KbName('ESCAPE')];

%% 窗口
screenNumber = max(Screen('Screens'));
[window, windowRect] = Screen('OpenWindow', screenNumber, [128 128 128]);
Screen('TextFont', window, 'Simsun');
[screenXpixels, screenYpixels] = Screen('WindowSize', window);
centerX = screenXpixels / 2;
centerY = screenYpixels / 2;
stimColor = [255 255 255];
halfShape = 60;                                   % 简化：直接用像素画形状
shapeXY   = [centerX, centerY - 150];             % 形状位置
labelXY   = [centerX, centerY + 150];             % 标签位置

KbQueueCreate([], keys);

%% 阶段 A：复刻实验程序（刺激期不监听，仅反应窗口 KbCheck）
showLines(window, stimColor, centerX, centerY, { ...
    '【阶段 A】复刻当前实验程序的监听方式', ...
    '流程：注视点 0.5s → 刺激 0.5s（此期间请故意抢按 f 或 j）→ 掩蔽/空白 0.2s → 反应窗口 1.3s', ...
    '程序只在最后的反应窗口里监听键盘。', ...
    '请每个试次都在刺激出现时抢先按一次键，按空格开始。'});
waitKeySpace(window);

resA = runPhase(window, 1, nTrials, T, maskDur, W, fixDur, keys, ...
                centerX, centerY, halfShape, shapeXY, labelXY, stimColor);

%% 阶段 B：全程 KbQueue 监听
showLines(window, stimColor, centerX, centerY, { ...
    '【阶段 B】全程事件监听（KbQueue）', ...
    '完全相同的刺激时间轴，但程序从注视点开始就监听所有按键。', ...
    '同样请在刺激出现时抢先按一次键，按空格开始。'});
waitKeySpace(window);

resB = runPhase(window, 2, nTrials, T, maskDur, W, fixDur, keys, ...
                centerX, centerY, halfShape, shapeXY, labelXY, stimColor);

%% 汇总
fprintf('\n==================== 汇总 ====================\n');
summaryTable('阶段A (仅反应窗口 KbCheck，同实验程序)', resA);
summaryTable('阶段B (全程 KbQueue 监听)', resB);
fprintf('\n结论判读：\n');
fprintf('  - 若阶段A在"刺激期"记录了按键次数 > 0，但"被程序记录"为 0 → 程序当时没在监听（设计如此）\n');
fprintf('  - 若阶段B能把刺激期按键完整记录下来 → 键盘与 Psychtoolbox 硬件链路正常\n');
fprintf('  - 两阶段"刺激期按键次数"接近，说明按键本身从未丢失，只是阶段A选择不采集\n');
fprintf('==============================================\n');

showLines(window, stimColor, centerX, centerY, {'测试结束，结果见 MATLAB 命令行。', '按任意键关闭窗口。'});
KbStrokeWait;
KbQueueStop; KbQueueRelease;
Screen('CloseAll');

%% ======================= 局部函数 =======================
function res = runPhase(window, phase, nTrials, T, maskDur, W, fixDur, keys, ...
                        centerX, centerY, halfShape, shapeXY, labelXY, stimColor)
% 运行一个阶段的全部试次，返回逐试次结果
res = struct('phase', {}, 'trial', {}, 'nFix', {}, 'nStim', {}, 'nMask', {}, ...
             'nWin', {}, 'recorded', {}, 'rt', {}, 'key', {});

KbQueueFlush();
KbQueueStart();

for i = 1:nTrials
    % 清空队列
    KbQueueFlush();

    % 1) 注视点
    Screen('TextSize', window, 40);
    DrawFormattedText(window, '+', 'center', 'center', stimColor);
    tFix = Screen('Flip', window);
    preciseWait(fixDur);
    evFix = drainQueue();

    % 2) 刺激（形状+标签）
    Screen('TextSize', window, 40);
    DrawFormattedText(window, '+', 'center', 'center', stimColor);
    Screen('FillOval', window, stimColor, ...
        [shapeXY(1)-halfShape, shapeXY(2)-halfShape, shapeXY(1)+halfShape, shapeXY(2)+halfShape]);
    Screen('TextSize', window, 60);
    DrawFormattedText(window, double('自我'), 'center', labelXY(2), stimColor);
    tStim = Screen('Flip', window);
    preciseWait(T);
    evStim = drainQueue();

    % 3) 掩蔽/空白 200ms
    tMask = Screen('Flip', window);
    preciseWait(maskDur);
    evMask = drainQueue();

    % 4) 反应窗口
    response = ''; rt = NaN; tPress = NaN;
    if phase == 1
        % 复刻实验程序：只在反应窗口轮询 KbCheck
        tResp = Screen('Flip', window);
        while GetSecs() - tResp < W - maskDur
            [keyIsDown, ~, keyCode] = KbCheck;
            if keyIsDown
                pk = find(keyCode);
                if ~isempty(pk)
                    name = KbName(pk(1));
                    if any(strcmp(name, {'f', 'j'}))
                        response = name;
                        tPress = GetSecs();
                        rt = tPress - tStim;
                        break;
                    elseif strcmp(name, 'ESCAPE')
                        cleanupAndQuit(window);
                    end
                end
            end
        end
    else
        % 阶段B：用事件队列判定（从反应窗口开始时刻起算的有效反应）
        tResp = Screen('Flip', window);
        while GetSecs() - tResp < W - maskDur
            [pressed, firstPress] = KbQueueCheck();
            if pressed
                idx = find(firstPress > 0);
                if ~isempty(idx)
                    [~, k] = min(firstPress(idx));
                    keyIdx = idx(k);
                    tPress = firstPress(keyIdx);
                    name = KbName(keyIdx);
                    if strcmp(name, 'ESCAPE')
                        cleanupAndQuit(window);
                    end
                    response = name;
                    rt = tPress - tStim;
                    break;
                end
            end
            WaitSecs(0.001);
        end
    end
    evWin = drainQueue();   % 反应窗口内（未被上面取走）的其余按键

    % 归类统计（相对刺激 onset 的时间）
    nFix  = countInWindow(evFix,  -inf, tStim);
    nStim = countInWindow(evStim, tStim, tStim + T);
    nMask = countInWindow(evMask, tStim + T, tStim + T + maskDur);
    nWin  = countInWindow(evWin,  tStim + T + maskDur, inf);

    res(end+1) = struct('phase', phase, 'trial', i, 'nFix', nFix, 'nStim', nStim, ...
        'nMask', nMask, 'nWin', nWin, 'recorded', ~isempty(response), 'rt', rt, 'key', response); %#ok<AGROW>

    fprintf('[阶段%d 试次%d] 注视期按键=%d | 刺激期按键=%d | 掩蔽期按键=%d | 反应窗口按键(队列)=%d || 程序记录: %s\n', ...
        phase, i, nFix, nStim, nMask, nWin, ...
        ternary(isempty(response), '无', sprintf('%s @ %.3fs', response, rt)));
end

KbQueueStop;
end

function ev = drainQueue()
% 取出队列中自上次调用以来的所有按键（名称+绝对时间戳）
ev = struct('name', {}, 'time', {});
[pressed, firstPress] = KbQueueCheck();
if pressed
    idx = find(firstPress > 0);
    for j = 1:numel(idx)
        ev(end+1) = struct('name', KbName(idx(j)), 'time', firstPress(idx(j))); %#ok<AGROW>
    end
end
end

function n = countInWindow(ev, lo, hi)
n = 0;
for j = 1:numel(ev)
    if ev(j).time >= lo && ev(j).time < hi
        n = n + 1;
    end
end
end

function summaryTable(label, res)
nStim = sum([res.nStim]);
nMask = sum([res.nMask]);
nRec  = sum([res.recorded]);
rtAll = [res.rt];
rtAll = rtAll(~isnan(rtAll));
fprintf('%s\n', label);
fprintf('   刺激呈现期按键次数 : %d 次（其中被程序记录: %d 次）\n', nStim, sum([res([res.nStim] > 0).recorded]));
fprintf('   掩蔽/空白期按键次数: %d 次\n', nMask);
fprintf('   程序记录的反应     : %d / %d 试次\n', nRec, numel(res));
if ~isempty(rtAll)
    fprintf('   记录到的 RT        : 最小 %.3fs，最大 %.3fs（理论下限 T+0.2 = %.3fs）\n', ...
        min(rtAll), max(rtAll), 0.7);
end
fprintf('\n');
end

function preciseWait(sec)
t0 = GetSecs();
while GetSecs() - t0 < sec
end
end

function showLines(window, color, cx, cy, lines)
Screen('TextSize', window, 26);
y = cy - 40 * numel(lines);
for i = 1:numel(lines)
    DrawFormattedText(window, double(lines{i}), 'center', y + 60 * (i - 1), color);
end
Screen('Flip', window);
end

function waitKeySpace(window) %#ok<INUSD>
KbQueueFlush();
while true
    [keyIsDown, ~, keyCode] = KbCheck;
    if keyIsDown
        name = KbName(find(keyCode, 1));
        if strcmp(name, 'space')
            break;
        elseif strcmp(name, 'ESCAPE')
            Screen('CloseAll');
            error('用户按 Esc 退出测试。');
        end
    end
    WaitSecs(0.005);
end
KbQueueFlush();
end

function cleanupAndQuit(window) %#ok<INUSD>
KbQueueStop; KbQueueRelease; Screen('CloseAll');
error('用户按 Esc 退出测试。');
end

function out = ternary(cond, a, b)
if cond, out = a; else, out = b; end
end
