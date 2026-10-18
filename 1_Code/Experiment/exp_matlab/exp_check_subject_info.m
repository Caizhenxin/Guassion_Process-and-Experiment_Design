function [ok, problems, info] = exp_check_subject_info(userInput, P_groups)
%EXP_CHECK_SUBJECT_INFO 校验 Exp_Design_Formal 的"实验信息"弹窗五项（D4：组别只有 1–4）
%
%   [ok, problems, info] = exp_check_subject_info(userInput, P_groups)
%
% 输入
%   userInput : inputdlg 返回的 1×5 cellstr（组别/编号/性别/年龄/惯用手），可为空
%   P_groups  : D4 的 4 个 P 组，默认 [0; 8; 32; 120]
%
% 输出
%   ok        : 五项全部合法 ⇒ true
%   problems  : cellstr，逐条说明哪一项填错（含 4 组速查）；ok 为 true 时是空 cell
%   info      : struct（groupID/subjectID/gender/age/handedness/P）；非法项为 NaN
%
% 背景（v4.2）
%   旧代码在 groupID 越界时直接 error ⇒ 主试填了旧版的"组 7"就整场开不了机，
%   只能重开。本函数把"填错"变成可解释、可重填的返回值，由调用方决定怎么提示。
%   独立成文件是为了能在没有屏幕/PTB 的情况下跑单元测试
%   （见 test/check_input_validation.m）。

if nargin < 2 || isempty(P_groups)
    P_groups = [0; 8; 32; 120];
end
numGroups = numel(P_groups);

ok = false;
problems = cell(5, 1);
nprob = 0;
info = struct('groupID', NaN, 'subjectID', NaN, 'gender', NaN, ...
              'age', NaN, 'handedness', NaN, 'P', NaN);

% ---- 0. 弹窗被取消/关窗 ----
if ~iscell(userInput) || numel(userInput) < 5
    nprob = nprob + 1;
    problems{nprob} = ['没有收到 5 项实验信息（"实验信息"弹窗可能被取消或关窗）。' ...
        'D4 只有 4 个 P 组：组1 P0 / 组2 P8 / 组3 P32 / 组4 P120。'];
    problems = problems(1:nprob);
    return;
end

% ---- 1. 五项一律按数字解析（空串 ⇒ NaN，下面逐项报错）----
v = nan(1, 5);
for k = 1:5
    s = userInput{k};
    if ischar(s)
        v(k) = str2double(strtrim(s));
    end
end

% ---- 2. 组别：D4 只有 1..numGroups ----
if ~isfinite(v(1)) || v(1) ~= round(v(1)) || v(1) < 1 || v(1) > numGroups
    nprob = nprob + 1;
    problems{nprob} = sprintf(['被试组别填的是"%s"，越界。\n' ...
        'D4 只有 %d 个 P 组（被试间）：\n' ...
        '    组1 = P0    组2 = P8    组3 = P32    组4 = P120\n' ...
        '旧版的"组7 = 无掩蔽"在 D4 中不存在（4 组的 12 个单元全部带掩蔽）。'], ...
        char(string(userInput{1})), numGroups);
else
    info.groupID = v(1);
    info.P = P_groups(v(1));
end

% ---- 3. 编号：≥1 的整数 ----
if ~isfinite(v(2)) || v(2) ~= round(v(2)) || v(2) < 1
    nprob = nprob + 1;
    problems{nprob} = sprintf('被试编号必须是 ≥1 的整数（填的是"%s"）。', ...
        char(string(userInput{2})));
else
    info.subjectID = v(2);
end

% ---- 4. 性别：1 = 女，2 = 男 ----
if ~isfinite(v(3)) || ~any(v(3) == [1, 2])
    nprob = nprob + 1;
    problems{nprob} = sprintf('性别只能填 1（女）或 2（男），填的是"%s"。', ...
        char(string(userInput{3})));
else
    info.gender = v(3);
end

% ---- 5. 年龄：10–100 的整数 ----
if ~isfinite(v(4)) || v(4) ~= round(v(4)) || v(4) < 10 || v(4) > 100
    nprob = nprob + 1;
    problems{nprob} = sprintf('年龄必须是 10–100 的整数（填的是"%s"）。', ...
        char(string(userInput{4})));
else
    info.age = v(4);
end

% ---- 6. 惯用手：1 = 左，2 = 右 ----
if ~isfinite(v(5)) || ~any(v(5) == [1, 2])
    nprob = nprob + 1;
    problems{nprob} = sprintf('惯用手只能填 1（左）或 2（右），填的是"%s"。', ...
        char(string(userInput{5})));
else
    info.handedness = v(5);
end

problems = problems(1:nprob);
ok = (nprob == 0);
end
