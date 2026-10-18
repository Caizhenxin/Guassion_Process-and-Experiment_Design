function check_input_validation()
%CHECK_INPUT_VALIDATION 无屏幕版自测：Exp_Design_Formal 的"实验信息"校验（v4.2）
%
%   cd 1_Code/Experiment/exp_matlab && addpath('test'); check_input_validation
%
% 覆盖的正是主试最容易填错的几类：旧版组号 7、空值、非整数、越界编号、
% 性别/年龄/惯用手非法、点取消、多项同时错。任何一条不符就 error（matlab -batch 退出码非 0）。
%
% 为什么要这个自测：这段校验过去是 `error(...)` 直接炸（主试填 7 就整场开不了机），
% 现在改成"返回值 + 弹窗重填"；如果没人钉住这些边界，下次改版很容易又把
% "该拦的"放过去或把"能重填的"变成崩溃。

P = [0; 8; 32; 120];     % D4 的 4 个 P 组
nPass = 0; nFail = 0;
failMsgs = {};

    function check(name, cond, detail)
        if cond
            nPass = nPass + 1;
            fprintf('  ✅ %s\n', name);
        else
            nFail = nFail + 1;
            failMsgs{end+1} = sprintf('%s ｜ %s', name, detail);
            fprintf('  ❌ %s ｜ %s\n', name, detail);
        end
    end

    function checkBad(name, userInput, mustContain)
        % 期望"判为非法"，且提示里含关键信息
        [ok, problems, ~] = exp_check_subject_info(userInput, P);
        txt = strjoin(problems, ' ');
        check(name, ~ok && ~isempty(problems), '期望判非法且给出理由');
        check([name ' · 提示可读'], contains(txt, mustContain), ...
              sprintf('提示里找不到"%s"：%s', mustContain, txt));
    end

fprintf('== Exp_Design_Formal 填写校验自测（D4）==\n');

% ---------- A. 合法输入：4 个组都要放行，且 P 对得上 ----------
fprintf('\n[A] 合法输入（4 组）\n');
legalCases = { {'1','1','2','21','2'}, 0; ...
               {'2','3','1','25','1'}, 8; ...
               {'3','10','2','19','2'}, 32; ...
               {'4','2','1','30','1'}, 120 };
for k = 1:size(legalCases, 1)
    ui = legalCases{k, 1};
    [ok, problems, info] = exp_check_subject_info(ui, P);
    check(sprintf('组%s 合法放行', ui{1}), ok && isempty(problems), ...
          sprintf('ok=%d problems=%s', ok, strjoin(problems, ' / ')));
    check(sprintf('组%s ⇒ P=%d', ui{1}, legalCases{k, 2}), info.P == legalCases{k, 2}, ...
          sprintf('info.P=%g', info.P));
    check(sprintf('组%s ⇒ 字段回填', ui{1}), ...
          info.subjectID == str2double(ui{2}) && info.gender == str2double(ui{3}) && ...
          info.age == str2double(ui{4}) && info.handedness == str2double(ui{5}), ...
          'subjectID/gender/age/handedness 回填不一致');
end

% ---------- B. 组别非法：这次事故的直接复现 ----------
fprintf('\n[B] 组别非法（含本次事故的 groupID=7）\n');
checkBad('组别=7（旧版无掩蔽组）被拦', {'7','1','2','21','2'}, 'P120');
checkBad('组别=7 提示写明"4 个 P 组"', {'7','1','2','21','2'}, '4 个 P 组');
checkBad('组别=7 提示点名旧版"组7"', {'7','1','2','21','2'}, '组7');
checkBad('组别=0 被拦', {'0','1','2','21','2'}, '越界');
checkBad('组别=5 被拦', {'5','1','2','21','2'}, '越界');
checkBad('组别=1.5 非整数被拦', {'1.5','1','2','21','2'}, '越界');
checkBad('组别为空被拦', {'','1','2','21','2'}, '越界');
checkBad('组别写汉字被拦', {'一','1','2','21','2'}, '越界');

% ---------- C. 其余四项非法 ----------
fprintf('\n[C] 编号/性别/年龄/惯用手非法\n');
checkBad('编号=0 被拦', {'1','0','2','21','2'}, '编号');
checkBad('编号为空被拦', {'1','','2','21','2'}, '编号');
checkBad('编号=2.5 被拦', {'1','2.5','2','21','2'}, '编号');
checkBad('性别=3 被拦', {'1','1','3','21','2'}, '性别');
checkBad('性别为空被拦', {'1','1','','21','2'}, '性别');
checkBad('年龄=5 被拦', {'1','1','2','5','2'}, '年龄');
checkBad('年龄=101 被拦', {'1','1','2','101','2'}, '年龄');
checkBad('惯用手=5 被拦', {'1','1','2','21','5'}, '惯用手');

% ---------- D. 多项同时错 / 取消 / 非字符串输入 ----------
fprintf('\n[D] 组合与异常输入\n');
[ok, problems, info] = exp_check_subject_info({'7','0','9','5','5'}, P);
check('五项全错 ⇒ 5 条提示', ~ok && numel(problems) == 5, ...
      sprintf('numel=%d', numel(problems)));
check('五项全错 ⇒ 合法字段仍为 NaN', isnan(info.groupID) && isnan(info.P), ...
      'groupID 或 P 被错误回填');

[ok, problems, ~] = exp_check_subject_info({}, P);
check('弹窗取消（空）⇒ 判非法且有提示', ~ok && ~isempty(problems), ...
      sprintf('ok=%d', ok));
check('弹窗取消 ⇒ 提示写明 4 组', contains(strjoin(problems, ' '), 'P0'), ...
      strjoin(problems, ' '));

[ok, ~, ~] = exp_check_subject_info({'1','1','2'}, P);   % 只有 3 项
check('不足 5 项 ⇒ 判非法而不是崩', ~ok, 'ok=true');

try
    [ok, ~, ~] = exp_check_subject_info({1, 1, 2, 21, 2}, P);  % 数值而非字符串
    check('数值型输入不报错（判非法即可）', ~ok, 'ok=true');
catch ME
    check('数值型输入不报错（判非法即可）', false, ME.message);
end

% ---------- E. 默认参数（不传 P_groups 也要工作）----------
fprintf('\n[E] 默认参数\n');
[ok, ~, info] = exp_check_subject_info({'4','1','1','20','1'});
check('不传 P_groups ⇒ 默认 4 组且 P=120', ok && info.P == 120, ...
      sprintf('ok=%d P=%g', ok, info.P));

% ---------- 汇总 ----------
fprintf('\n== 结果：%d 通过 / %d 失败 ==\n', nPass, nFail);
if nFail > 0
    fprintf('失败项：\n');
    for k = 1:numel(failMsgs)
        fprintf('  - %s\n', failMsgs{k});
    end
    error('check_input_validation:failed', '%d 项未通过', nFail);
end
fprintf('✅ 全部通过\n');
end
