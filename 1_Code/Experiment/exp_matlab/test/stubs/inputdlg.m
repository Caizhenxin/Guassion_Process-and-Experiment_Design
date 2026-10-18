function answer = inputdlg(varargin)
% inputdlg 桩：返回 driver 预设的 5 项（默认组2/编号99/女/20/右）
%   用 SMOKE_ANSWER 可在 driver 里改；为空则用默认值
global SMOKE_ANSWER
if isempty(SMOKE_ANSWER) || numel(SMOKE_ANSWER) ~= 5
    answer = {'2', '99', '1', '20', '2'};
else
    answer = SMOKE_ANSWER;
end
end
