function h = warndlg(message, title, varargin)
% warndlg 桩：不弹窗，只把文本记进 SMOKE_WARN，便于断言"确实提示过"
global SMOKE_WARN
if isempty(SMOKE_WARN), SMOKE_WARN = {}; end
SMOKE_WARN{end+1} = sprintf('%s | %s', char(title), char(message));
h = [];
end
