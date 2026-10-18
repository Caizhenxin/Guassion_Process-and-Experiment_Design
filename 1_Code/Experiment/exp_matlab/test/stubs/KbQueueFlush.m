function KbQueueFlush(varargin)
% KbQueue 桩：每个试次都会 Flush 一次 => 用它当作"新试次开始"的信号
global SMOKE_TRIAL SMOKE_FLUSH SMOKE_TIME
if isempty(SMOKE_TIME), SMOKE_TIME = 0; end
if isempty(SMOKE_TRIAL), SMOKE_TRIAL = 0; end
SMOKE_TRIAL = SMOKE_TRIAL + 1;
SMOKE_FLUSH = SMOKE_TIME;
end
