# -*- coding: utf-8 -*-
"""_gen_ptb_stubs.py —— 生成 PTB 桩（test/stubs/*.m），用于无屏幕跑完整实验会话

为什么需要：
  2026-10-17 连续两次实机崩溃（组别越界、table 宽度锁死）都发生在「从未被执行过的路径」上。
  只测单个函数（check_data_accum / check_ask_info）挡不住「整场流程」的运行时错误。
  本桩把 Screen / KbQueue / KbCheck / GetSecs 全部替换成虚拟实现，用虚拟时钟在几十秒内
  跑完 576 试次 + 练习 + 休息 + 两次保存，把运行时错误暴露在实机之前。

用法（桩只在加入路径时生效，不改变实机行为）：
  cd 1_Code/Experiment/exp_matlab
  addpath('test/stubs','-begin')
  run('Exp_Design_Formal.m')
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent          # .../exp_matlab/test
STUBS = HERE / "stubs"
STUBS.mkdir(exist_ok=True)

FILES = {}

FILES["GetSecs.m"] = r"""function t = GetSecs()
% GetSecs 桩：虚拟时钟。每次调用前进 1 ms（保证 while GetSecs()-t0<d 的轮询循环一定会退出）
global SMOKE_TIME
if isempty(SMOKE_TIME), SMOKE_TIME = 0; end
SMOKE_TIME = SMOKE_TIME + 0.001;
t = SMOKE_TIME;
end
"""

FILES["WaitSecs.m"] = r"""function WaitSecs(seconds)
% WaitSecs 桩：只推进虚拟时钟，不真的等
global SMOKE_TIME
if isempty(SMOKE_TIME), SMOKE_TIME = 0; end
if nargin < 1 || isempty(seconds), seconds = 0; end
SMOKE_TIME = SMOKE_TIME + seconds;
end
"""

FILES["Screen.m"] = r"""function varargout = Screen(cmd, varargin)
% Screen 桩：覆盖 Exp_Design_Formal.m 用到的全部子命令，其余命令静默忽略
res = {0};
switch lower(cmd)
    case 'preference'
        res = {0};                      % 优先级设置返回值
    case 'screens'
        res = {0};                      % 只有一块屏
    case 'openwindow'
        res = {1, [0 0 1024 768]};      % [window, windowRect]
    case 'windowsize'
        res = {[1024 768]};
    case 'getflipinterval'
        res = {1/60};
    case 'flip'
        res = {GetSecs()};              % 返回虚拟的 vbl 时刻
    case 'maketexture'
        res = {numel(varargin)};        % 任意非零句柄
    case {'closeall', 'filloval', 'fillrect', 'drawtexture', 'drawtext', ...
          'textfont', 'textsize', 'textstyle', 'textcolor'}
        res = {0};
    otherwise
        res = {0};
end
nout = max(nargout, 0);
for k = 1:nout
    if k <= numel(res)
        varargout{k} = res{k};
    else
        varargout{k} = 0;
    end
end
end
"""

FILES["KbName.m"] = r"""function varargout = KbName(name)
% KbName 桩：只认程序用到的几个键名；'UnifyKeyNames' 当无操作
if isnumeric(name)
    table = {'f', 'j', 'space', 'return', 'esc'};
    codes = [6, 7, 32, 13, 27];
    idx = find(codes == name, 1);
    if isempty(idx), varargout{1} = ''; else, varargout{1} = table{idx}; end
    return
end
switch lower(strtrim(char(name)))
    case 'f',        code = 6;
    case 'j',        code = 7;
    case 'space',    code = 32;
    case 'return',   code = 13;
    case {'esc', 'escape'}, code = 27;
    case 'unifykeynames'
        code = 0;                       % 无操作（程序故意不开启，见 v4 头注）
    otherwise
        code = [];                      % 未知键名 -> 空，让调用方走 fallback
end
if nargout > 0
    varargout{1} = code;
end
end
"""

FILES["KbCheck.m"] = r"""function [keyIsDown, secs, keyCode] = KbCheck(~)
% KbCheck 桩：周期性"按下 space + return"，从不按 Esc
%   - 周期性而不是恒为 1：万一程序里有"等松键"的循环也能退出
%   - 从不按 Esc：checkEscape 不会误触发中止
global SMOKE_TIME
if isempty(SMOKE_TIME), SMOKE_TIME = 0; end
secs = SMOKE_TIME;
keyCode = zeros(1, 256);
phase = mod(SMOKE_TIME, 0.55);
keyIsDown = double(phase < 0.05);
if keyIsDown
    keyCode(32) = 1;    % space
    keyCode(13) = 1;    % return
end
end
"""

FILES["KbQueueCreate.m"] = r"""function KbQueueCreate(varargin)
% KbQueue 桩：无操作
end
"""

FILES["KbQueueStart.m"] = r"""function KbQueueStart(varargin)
% KbQueue 桩：无操作
end
"""

FILES["KbQueueStop.m"] = r"""function KbQueueStop(varargin)
% KbQueue 桩：无操作
end
"""

FILES["KbQueueFlush.m"] = r"""function KbQueueFlush(varargin)
% KbQueue 桩：每个试次都会 Flush 一次 => 用它当作"新试次开始"的信号
global SMOKE_TRIAL SMOKE_FLUSH SMOKE_TIME
if isempty(SMOKE_TIME), SMOKE_TIME = 0; end
if isempty(SMOKE_TRIAL), SMOKE_TRIAL = 0; end
SMOKE_TRIAL = SMOKE_TRIAL + 1;
SMOKE_FLUSH = SMOKE_TIME;
end
"""

FILES["KbQueueRelease.m"] = r"""function KbQueueRelease(varargin)
% KbQueue 桩：无操作
end
"""

FILES["KbQueueCheck.m"] = r"""function [pressed, firstPress] = KbQueueCheck()
% KbQueueCheck 桩：按"试次序号"编排按键剧本
%   试次号 mod 4 == 0        -> 整窗不按键（走 timeout / 'NA' 分支）
%   试次号 mod 7 == 0        -> 注视期抢按（走 premature_press 分支）
%   其余                     -> 在 Flush 之后 0.95 s 按一次（刺激+掩蔽都结束，落在反应窗内）
%   按键在 f / j 之间交替，保证两条正确/错误分支都被走到
global SMOKE_TIME SMOKE_TRIAL SMOKE_FLUSH
if isempty(SMOKE_TIME), SMOKE_TIME = 0; end
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
    tPress = SMOKE_FLUSH + 0.15;        % 注视期抢按
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
"""

FILES["HideCursor.m"] = r"""function HideCursor(varargin)
% 桩：无操作
end
"""

FILES["ShowCursor.m"] = r"""function ShowCursor(varargin)
% 桩：无操作
end
"""

FILES["ListenChar.m"] = r"""function ListenChar(varargin)
% 桩：无操作
end
"""

FILES["sca.m"] = r"""function sca()
% 桩：无操作（等价 Screen('CloseAll')）
end
"""

FILES["Priority.m"] = r"""function oldPriority = Priority(varargin)
% 桩：无操作
oldPriority = 0;
end
"""

FILES["RestrictKeysForKbCheck.m"] = r"""function RestrictKeysForKbCheck(varargin)
% 桩：无操作
end
"""

FILES["DrawFormattedText.m"] = r"""function varargout = DrawFormattedText(varargin)
% 桩：无操作（文本不真的画）
if nargout > 0, varargout{1} = 0; end
end
"""

FILES["InitializeMatlabOpenGL.m"] = r"""function InitializeMatlabOpenGL(varargin)
% 桩：无操作
end
"""

FILES["inputdlg.m"] = r"""function answer = inputdlg(varargin)
% inputdlg 桩：返回 driver 预设的 5 项（默认组2/编号99/女/20/右）
%   用 SMOKE_ANSWER 可在 driver 里改；为空则用默认值
global SMOKE_ANSWER
if isempty(SMOKE_ANSWER) || numel(SMOKE_ANSWER) ~= 5
    answer = {'2', '99', '1', '20', '2'};
else
    answer = SMOKE_ANSWER;
end
end
"""

FILES["warndlg.m"] = r"""function h = warndlg(message, title, varargin)
% warndlg 桩：不弹窗，只把文本记进 SMOKE_WARN，便于断言"确实提示过"
global SMOKE_WARN
if isempty(SMOKE_WARN), SMOKE_WARN = {}; end
SMOKE_WARN{end+1} = sprintf('%s | %s', char(title), char(message));
h = [];
end
"""

FILES["uiwait.m"] = r"""function uiwait(varargin)
% uiwait 桩：不阻塞
end
"""

FILES["msgbox.m"] = r"""function h = msgbox(varargin)
% msgbox 桩：不弹窗
h = [];
end
"""

FILES["input.m"] = r"""function varargout = input(prompt, varargin)
% input 桩：不读键盘。's' 模式返回空串（主试确认直接回车），数值模式返回 NaN
if nargin > 1 && ischar(varargin{1}) && strcmpi(varargin{1}, 's')
    value = '';
else
    value = NaN;
end
if nargout > 0, varargout{1} = value; end
end
"""

for name, body in FILES.items():
    (STUBS / name).write_text(body, encoding="utf-8", newline="\n")
print(f"[ok] {len(FILES)} 个桩写入 {STUBS}")
