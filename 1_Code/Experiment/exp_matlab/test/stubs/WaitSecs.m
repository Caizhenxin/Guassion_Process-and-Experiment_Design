function WaitSecs(seconds)
% WaitSecs 桩：只推进虚拟时钟，不真的等
global SMOKE_TIME
if isempty(SMOKE_TIME), SMOKE_TIME = 0; end
if nargin < 1 || isempty(seconds), seconds = 0; end
SMOKE_TIME = SMOKE_TIME + seconds;
end
