function check_ask_info()
%#ok<*INUSD>   % 假的 inputdlg/warndlg/input 用不到真实入参，全文件抑制该类提示
%CHECK_ASK_INFO `exp_ask_subject_info.m` 的无屏幕自测（不需要真实弹窗/屏幕）
%
%   用法（无窗口，命令行）：
%       matlab -batch "cd('.../1_Code/Experiment/exp_matlab'); addpath('test'); check_ask_info"
%
%   被测的是主试真正会踩到的那条路径：
%     * 按旧手册填了组别 7 ⇒ 弹「填写有误」说明（含 4 个 P 组速查）⇒ 回到弹窗重填，**不报错退出**；
%     * 组别/编号/性别/年龄/惯用手任何一项非法都同样处理；
%     * 只有点「取消」才终止；
%     * 填完回显 groupID 与「本组 P = ?」；确认时输入 r 可以再来一遍。
%
%   做法：把 inputdlg / warndlg / uiwait / input / fprintf 用 hooks 换掉（假的），
%   因此不需要屏幕、不会卡在对话框上，几秒钟跑完。

here = fileparts(mfilename('fullpath'));
addpath(fileparts(here));    % exp_matlab（被调函数在这层）
addpath(here);

P_groups = [0; 8; 32; 120];
n_pass = 0;
n_fail = 0;
fail_msg = {};

    function ok(name, cond, detail)
        if cond
            n_pass = n_pass + 1;
            fprintf('  ✅ %s\n', name);
        else
            n_fail = n_fail + 1;
            msg = name;
            if nargin >= 3 && ~isempty(detail)
                msg = sprintf('%s ｜ %s', name, detail);
            end
            fail_msg{end+1} = msg;
            fprintf('  ❌ %s\n', msg);
        end
    end

    function check_case()
        fprintf('\n[%s]\n', case_name);
    end

    function tf = logged(st, pat)
        % 回显日志里是否出现过某段文字（fprintf 被 hooks 截获后存在 st('log')）
        L = st('log');
        tf = false;
        for ii = 1:numel(L)
            if contains(L{ii}, pat)
                tf = true;
                return;
            end
        end
    end

fprintf('== check_ask_info：exp_ask_subject_info 无屏幕自测 ==\n');

% ============ S1：五项全合法，一次通过 ============
case_name = 'S1 五项合法 + 回车确认';
check_case;
[hooks, st] = make_hooks({{'1', '3', '1', '22', '2'}}, {''});
info = exp_ask_subject_info(P_groups, hooks);
ok('S1-1 groupID = 1', info.groupID == 1, num2str(info.groupID));
ok('S1-2 subjectID = 3', info.subjectID == 3, num2str(info.subjectID));
ok('S1-3 gender = 1', info.gender == 1);
ok('S1-4 age = 22', info.age == 22);
ok('S1-5 handedness = 2', info.handedness == 2);
ok('S1-6 弹窗只开 1 次', st('di') == 1, sprintf('%d 次', st('di')));
ok('S1-7 没有弹过错误说明', numel(st('warns')) == 0, sprintf('%d 次', numel(st('warns'))));
ok('S1-8 回显含「本组 P = 0」', logged(st, '本组 P = 0'));
ok('S1-9 回显含 D4 组别速查', logged(st, '组4 P120'));

% ============ S2：核心 bug —— 填 7 被拒后重填 1 ============
case_name = 'S2 填组别 7 ⇒ 拒绝并重填 1（用户报错的那条路径）';
check_case;
[hooks, st] = make_hooks({{'7', '3', '1', '22', '2'}, {'1', '3', '1', '22', '2'}}, {''});
info = exp_ask_subject_info(P_groups, hooks);
ok('S2-1 最终 groupID = 1（重填生效）', info.groupID == 1, num2str(info.groupID));
ok('S2-2 弹窗开了 2 次', st('di') == 2, sprintf('%d 次', st('di')));
ok('S2-3 弹了 1 次错误说明', numel(st('warns')) == 1, sprintf('%d 次', numel(st('warns'))));
if numel(st('warns')) >= 1
    W = st('warns');
    w = W{1};
    ok('S2-4 说明含「越界」', contains(w, '越界'));
    ok('S2-5 说明含「4 个 P 组」', contains(w, '4 个 P 组'));
    ok('S2-6 说明含速查「组1 P0」', contains(w, '组1 = P0'));
    ok('S2-7 说明没有出现 NaN 字样', ~contains(w, 'NaN'));
end

% ============ S3：组别留空（取消输入框 ⇒ NaN） ============
case_name = 'S3 组别留空 ⇒ 拒绝';
check_case;
[hooks, st] = make_hooks({{'', '3', '1', '22', '2'}, {'2', '3', '1', '22', '2'}}, {''});
info = exp_ask_subject_info(P_groups, hooks);
ok('S3-1 重填后 groupID = 2', info.groupID == 2, num2str(info.groupID));
ok('S3-2 弹了 1 次说明', numel(st('warns')) == 1);

% ============ S4–S7：其余四项各自非法 ============
case_name = 'S4 性别填 3 ⇒ 拒绝';
check_case;
[hooks, st] = make_hooks({{'1', '3', '3', '22', '2'}, {'1', '3', '2', '22', '2'}}, {''});
info = exp_ask_subject_info(P_groups, hooks);
ok('S4-1 重填后 gender = 2', info.gender == 2);
W = st('warns');
ok('S4-2 说明含「性别」', numel(W) == 1 && contains(W{1}, '性别'));

case_name = 'S5 年龄填 5 ⇒ 拒绝';
check_case;
[hooks, st] = make_hooks({{'1', '3', '1', '5', '2'}, {'1', '3', '1', '22', '2'}}, {''});
info = exp_ask_subject_info(P_groups, hooks);
ok('S5-1 重填后 age = 22', info.age == 22);
W = st('warns');
ok('S5-2 说明含「年龄」', numel(W) == 1 && contains(W{1}, '年龄'));

case_name = 'S6 惯用手填 9 ⇒ 拒绝';
check_case;
[hooks, st] = make_hooks({{'1', '3', '1', '22', '9'}, {'1', '3', '1', '22', '2'}}, {''});
info = exp_ask_subject_info(P_groups, hooks);
ok('S6-1 重填后 handedness = 2', info.handedness == 2);
W = st('warns');
ok('S6-2 说明含「惯用手」', numel(W) == 1 && contains(W{1}, '惯用手'));

case_name = 'S7 编号填 0 ⇒ 拒绝';
check_case;
[hooks, st] = make_hooks({{'1', '0', '1', '22', '2'}, {'1', '3', '1', '22', '2'}}, {''});
info = exp_ask_subject_info(P_groups, hooks);
ok('S7-1 重填后 subjectID = 3', info.subjectID == 3);
W = st('warns');
ok('S7-2 说明含「编号」', numel(W) == 1 && contains(W{1}, '编号'));

% ============ S8：点取消 ⇒ 唯一会终止的情况 ============
case_name = 'S8 点取消 ⇒ error';
check_case;
[hooks, ~] = make_hooks({{}}, {''});
threw = false;
msg = '';
try
    exp_ask_subject_info(P_groups, hooks);
catch err
    threw = true;
    msg = err.message;
end
ok('S8-1 抛异常', threw);
ok('S8-2 文案含「已取消」', contains(msg, '已取消'));
ok('S8-3 文案含「重新运行」', contains(msg, '重新运行'));

% ============ S9：确认时输入 r ⇒ 重填一遍 ============
case_name = 'S9 确认输入 r ⇒ 回弹窗重填（组别 2 → 3）';
check_case;
[hooks, st] = make_hooks({{'2', '3', '1', '22', '2'}, {'3', '4', '2', '31', '1'}}, {'r', ''});
info = exp_ask_subject_info(P_groups, hooks);
ok('S9-1 最终 groupID = 3', info.groupID == 3, num2str(info.groupID));
ok('S9-2 最终 subjectID = 4', info.subjectID == 4);
ok('S9-3 弹窗开了 2 次', st('di') == 2, sprintf('%d 次', st('di')));
ok('S9-4 回显含「本组 P = 32」', logged(st, '本组 P = 32'));
ok('S9-5 回显含「本组 P = 8」（第一次的值）', logged(st, '本组 P = 8'));

% ============ S10：大写 R 同样重填 ============
case_name = 'S10 确认输入大写 R ⇒ 同样重填';
check_case;
[hooks, st] = make_hooks({{'4', '3', '1', '22', '2'}, {'1', '3', '1', '22', '2'}}, {'R', ''});
info = exp_ask_subject_info(P_groups, hooks);
ok('S10-1 最终 groupID = 1', info.groupID == 1);
ok('S10-2 弹窗开了 2 次', st('di') == 2);

% ============ S11：连续 3 次非法后合法 ============
case_name = 'S11 连续 3 次非法（7 / 空 / 5）后填 4';
check_case;
[hooks, st] = make_hooks( ...
    {{'7', '3', '1', '22', '2'}, {'', '3', '1', '22', '2'}, {'0', '3', '1', '22', '2'}, {'4', '9', '1', '40', '1'}}, {''});
info = exp_ask_subject_info(P_groups, hooks);
ok('S11-1 最终 groupID = 4', info.groupID == 4);
ok('S11-2 弹窗开了 4 次', st('di') == 4, sprintf('%d 次', st('di')));
ok('S11-3 弹了 3 次说明', numel(st('warns')) == 3, sprintf('%d 次', numel(st('warns'))));
ok('S11-4 回显含「本组 P = 120」', logged(st, '本组 P = 120'));

% ============ 汇总 ============
fprintf('\n== check_ask_info：通过 %d / 未通过 %d ==\n', n_pass, n_fail);
if n_fail > 0
    fprintf('未通过项：\n');
    for kk = 1:numel(fail_msg)
        fprintf('  - %s\n', fail_msg{kk});
    end
    error('check_ask_info：有 %d 项未通过', n_fail);
end
fprintf('✅ exp_ask_subject_info 的「非法即重填、只有取消才退出」行为全部成立\n');

% ------------------------------------------------------------------------
    function [hooks, st] = make_hooks(dialogs, confirms)
        % 用 containers.Map（handle 类）做共享状态，闭包读到的都是最新值
        st = containers.Map();
        st('di') = 0;          % inputdlg 调用次数
        st('ci') = 0;          % input 调用次数
        st('warns') = {};
        st('log') = {};

        hooks = struct();
        hooks.inputdlg = @fake_inputdlg;
        hooks.warndlg  = @fake_warndlg;
        hooks.uiwait   = @(h) [];
        hooks.input    = @fake_input;
        hooks.fprintf  = @fake_fprintf;

        function out = fake_inputdlg(varargin)
            kd = st('di') + 1;
            st('di') = kd;
            if kd > numel(dialogs)
                why = sprintf('inputdlg 被调用第 %d 次，但脚本只准备了 %d 个回包', kd, numel(dialogs));
                error('check_ask_info:TooManyDialogs', '%s', why);
            end
            out = dialogs{kd};
        end

        function h = fake_warndlg(msg, varargin)
            w = st('warns');
            w{end+1} = msg;
            st('warns') = w;
            h = 42;
        end

        function out = fake_input(varargin)
            kc = st('ci') + 1;
            st('ci') = kc;
            if kc > numel(confirms)
                out = '';
            else
                out = confirms{kc};
            end
        end

        function fake_fprintf(fmt, varargin)
            L = st('log');
            L{end+1} = sprintf(fmt, varargin{:});
            st('log') = L;
        end
    end
end
