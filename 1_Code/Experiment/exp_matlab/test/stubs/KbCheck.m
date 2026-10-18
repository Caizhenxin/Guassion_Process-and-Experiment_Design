function [keyIsDown, secs, keyCode] = KbCheck(~)
% KbCheck 桩：周期性"按下 space + return"，从不按 Esc
%   - 周期性而不是恒为 1：万一程序里有"等松键"的循环也能退出
%   - 从不按 Esc：checkEscape 不会误触发中止
global SMOKE_TIME
if isempty(SMOKE_TIME), SMOKE_TIME = 0; end
SMOKE_TIME = SMOKE_TIME + 0.001;   % ★ 轮询本身也推进时钟：否则 while ~keyIsDown 会死转
secs = SMOKE_TIME;
keyCode = zeros(1, 256);
phase = mod(SMOKE_TIME, 0.55);
keyIsDown = double(phase < 0.05);
if keyIsDown
    keyCode(32) = 1;    % space
    keyCode(13) = 1;    % return
end
end
