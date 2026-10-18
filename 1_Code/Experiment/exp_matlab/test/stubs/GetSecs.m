function t = GetSecs()
% GetSecs 桩：虚拟时钟。每次调用前进 1 ms（保证 while GetSecs()-t0<d 的轮询循环一定会退出）
global SMOKE_TIME
if isempty(SMOKE_TIME), SMOKE_TIME = 0; end
SMOKE_TIME = SMOKE_TIME + 0.001;
t = SMOKE_TIME;
end
