function [pressed, firstPress] = KbQueueCheck()
% KbQueueCheck 桩：按"试次序号"编排按键剧本
%   试次号 mod 4 == 0        -> 整窗不按键（走 timeout / 'NA' 分支）
%   试次号 mod 7 == 0        -> 注视期抢按（走 premature_press 分支；必须被 flush 掉）
%   试次号 mod 9 == 0        -> 刺激期内按键（走 D5 的 min(T, RT)：stimulus_dur_actual 应≈RT）
%   其余                     -> 在 Flush 之后 0.95 s 按一次（刺激+掩蔽都结束，落在反应窗内）
%   按键在 f / j 之间交替，保证两条正确/错误分支都被走到
global SMOKE_TIME SMOKE_TRIAL SMOKE_FLUSH
if isempty(SMOKE_TIME), SMOKE_TIME = 0; end
SMOKE_TIME = SMOKE_TIME + 0.001;    % ★ 轮询也推进时钟：任何 while 循环都必然前进
if isempty(SMOKE_TRIAL), SMOKE_TRIAL = 0; end
if isempty(SMOKE_FLUSH), SMOKE_FLUSH = SMOKE_TIME; end
pressed = 0;
firstPress = zeros(1, 256);
if SMOKE_TRIAL == 0
    return
end
if mod(SMOKE_TRIAL, 4) == 0
    return                              % 本试次永远不按
end
if mod(SMOKE_TRIAL, 7) == 0
    tPress = SMOKE_FLUSH + 0.15;        % 注视期抢按（在刺激 onset 之前）
elseif mod(SMOKE_TRIAL, 9) == 0
    tPress = SMOKE_FLUSH + 0.55;        % 刺激期内按键（onset 实测约 flush+0.42，≈100 ms 后）
else
    tPress = SMOKE_FLUSH + 0.95;
end
if SMOKE_TIME < tPress
    return
end
pressed = 1;
if mod(SMOKE_TRIAL, 2) == 0
    firstPress(6) = tPress;             % 'f'
else
    firstPress(7) = tPress;             % 'j'
end
end
