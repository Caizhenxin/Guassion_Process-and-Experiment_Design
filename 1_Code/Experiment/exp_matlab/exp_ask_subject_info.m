function info = exp_ask_subject_info(P_groups, hooks)
%EXP_ASK_SUBJECT_INFO 收集被试五项信息（组别/编号/性别/年龄/惯用手），非法则重填
%
%   info = exp_ask_subject_info(P_groups)
%   info = exp_ask_subject_info(P_groups, hooks)   % 仅用于无屏幕自测
%
%   为什么单独成函数（v4.2）
%   -----------------------
%   旧版把「弹窗 → str2double → error 退出」写在脚本正文里，主试按旧手册填了组别 7
%   就直接 `error('D4 只有 %d 个 P 组（被试间），groupID=%d 越界。')` 退出，必须重开。
%   现在：
%     * 组别只接受 1..numel(P_groups)（D4 = 1..4），越界给「4 个 P 组速查」后**重填**；
%     * 编号/性别/年龄/惯用手任何一项非法同样重填（逻辑在 exp_check_subject_info.m）；
%     * 只有「点取消/关窗」才终止（不把 NaN 带进实验）；
%     * 填完之后把结果回显给主试核对，输入 r 可回到弹窗重填，不必 Ctrl+C 重开。
%   放进函数还带来一个好处：`test/check_ask_info.m` 可以用 hooks 注入假的
%   inputdlg/warndlg/input，在**无屏幕**下把「先填 7 被拒 → 改填 1 通过」这条真实路径跑一遍。
%
%   hooks（可选结构体，字段名即被替换的函数名；缺省用真实函数）
%     inputdlg / warndlg / uiwait / input / fprintf

if nargin < 2 || isempty(hooks)
    hooks = struct();
end

numGroups = numel(P_groups);
prompt = { sprintf('被试组别（只能填 1–%d）', numGroups), '被试编号', ...
           '性别[1 = 女, 2 = 男]', '年龄', '惯用手[1 = 左, 2 = 右]' };
title = '实验信息';
definput = {'', '', '', '', ''};

info = struct();

while true   % 外层：填写 → 主试确认（确认时输入 r 可回到弹窗重填）
    while true   % 内层：弹窗 + 校验（非法则弹说明并重来）
        userInput = callout(hooks, 'inputdlg', prompt, title, 1, definput);

        % 点"取消"/关窗：不把 NaN 带进实验，直接终止（这是唯一会主动退出的情况）
        if isempty(userInput)
            error(['已取消"实验信息"弹窗，本次未启动实验。\n' ...
                   'D4 只有 4 个 P 组：组1 P0 / 组2 P8 / 组3 P32 / 组4 P120。重新运行即可。']);
        end

        [infoOK, problems, info] = exp_check_subject_info(userInput, P_groups);
        if infoOK
            break;   % 五项全部合法，跳出弹窗循环
        end

        % 有非法项：弹窗逐条说明（含组别速查），关掉后自动回到信息窗重填
        hErr = callout(hooks, 'warndlg', problems, '填写有误，请重新填写');
        callvoid(hooks, 'uiwait', hErr);
    end

    % 主试确认回显：核对弹窗填写无误后再继续（填错可以输入 r 重填，不必 Ctrl+C 重开）
    callvoid(hooks, 'fprintf', '==================================================\n');
    callvoid(hooks, 'fprintf', ' 请主试核对本次实验信息：\n');
    callvoid(hooks, 'fprintf', '   被试组别 groupID   = %d   ⇒ 本组 P = %d 个额外练习试次\n', ...
             info.groupID, P_groups(info.groupID));
    callvoid(hooks, 'fprintf', '   被试编号 subjectID = %d\n', info.subjectID);
    callvoid(hooks, 'fprintf', '   性别(gender)       = %d  [1=女, 2=男]\n', info.gender);
    callvoid(hooks, 'fprintf', '   年龄(age)          = %d\n', info.age);
    callvoid(hooks, 'fprintf', '   惯用手(handedness) = %d  [1=左, 2=右]\n', info.handedness);
    callvoid(hooks, 'fprintf', ' D4 组别速查：组1 P0 ｜ 组2 P8 ｜ 组3 P32 ｜ 组4 P120（4 组全部带掩蔽）\n');
    callvoid(hooks, 'fprintf', '==================================================\n');

    choice = callout(hooks, 'input', '确认无误请按回车继续；输入 r 回车则重新填写信息：', 's');
    if ~strcmpi(strtrim(choice), 'r')
        break;   % 退出"填写 → 确认"大循环，正式进入实验
    end
end
end

% ------------------------------------------------------------------------
function out = callout(hooks, name, varargin)
%CALLOUT 调用 hooks.name（若提供）或同名真实函数，取 1 个返回值
if isfield(hooks, name)
    fn = hooks.(name);
else
    fn = str2func(name);
end
out = fn(varargin{:});
end

% ------------------------------------------------------------------------
function callvoid(hooks, name, varargin)
%CALLVOID 同上，但忽略返回值（fprintf/uiwait 这类）
if isfield(hooks, name)
    fn = hooks.(name);
else
    fn = str2func(name);
end
fn(varargin{:});
end
