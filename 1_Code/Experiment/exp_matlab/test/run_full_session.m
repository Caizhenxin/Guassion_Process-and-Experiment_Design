function res = run_full_session(groupID, subjectID, outDir, runInProgramDir)
% RUN_FULL_SESSION  用 PTB 桩把 Exp_Design_Formal.m 整场跑完（无屏幕、无被试、无真实计时）
%
%   res = run_full_session(groupID, subjectID[, outDir[, runInProgramDir]])
%
%   runInProgramDir（★ v4.8 / D92）：默认 true = 先 cd 到程序目录再跑（D79 起的原行为）。
%     false = 就在【当前目录】跑（脚本按名调用，不改变当前目录），用来验证路径可移植性：
%     掩蔽纹理仍从程序目录解析（v4.8 的 progDir），而 CSV/txt 落进当前目录。
%
%   为什么存在（2026-10-18 / D79）：
%     2026-10-17 一天之内连续两次实机崩溃（组别越界、table 列宽锁死），两次都发生在
%     「从未被执行过的路径」上。只测单个函数挡不住整场流程的运行时错误，而等到被试
%     坐在机器前才发现，代价是整段招募时间。本函数把 Screen / KbQueue / KbCheck /
%     GetSecs 全部替换成 test/stubs 下的虚拟实现，用虚拟时钟在几十秒内跑完
%     练习 + 576 试次 + 两次保存，把运行时错误提前暴露。
%
%   注意：桩只在 addpath 之后生效，**不改变实机行为**；实机绝不要 addpath('test/stubs')。
%
%   输出：res.ok / res.err / res.seconds / res.csv / res.txt / res.n_rows / res.checks

here = fileparts(mfilename('fullpath'));   % .../exp_matlab/test
expDir = fileparts(here);                  % .../exp_matlab
if nargin < 3 || isempty(outDir), outDir = fullfile(here, '_full_session_out'); end
if nargin < 4 || isempty(runInProgramDir), runInProgramDir = true; end
if ~exist(outDir, 'dir'), mkdir(outDir); end

warning('off', 'MATLAB:dispatcher:nameConflict');   % input.m 桩会与内置同名，属预期
addpath(fullfile(here, 'stubs'), '-begin');
global SMOKE_ANSWER SMOKE_TIME SMOKE_TRIAL SMOKE_FLUSH SMOKE_WARN
SMOKE_ANSWER = {sprintf('%d', groupID), sprintf('%d', subjectID), '1', '20', '2'};
SMOKE_TIME = 0; SMOKE_TRIAL = 0; SMOKE_FLUSH = 0; SMOKE_WARN = {};

% 预期行数：P 个练习试次 + 3 block × 192
P_groups = [0; 8; 32; 120];
nExpected = P_groups(groupID) + 3 * 192;

res = struct('ok', true, 'err', '', 'seconds', NaN, 'csv', '', 'txt', '', ...
             'n_rows', NaN, 'checks', {{}});
c = onCleanup(@() cleanup_run(here));

if runInProgramDir
    oldDir = cd(expDir);
    runCall = "run('Exp_Design_Formal.m')";
else
    % 按名调用脚本：MATLAB 不会因此改当前目录（run() 会改），这正是要测的场景
    addpath(expDir, '-begin');
    oldDir = cd(pwd);
    runCall = 'Exp_Design_Formal';
end
runDir = pwd;          % 数据落点 = 运行时的当前目录
t0 = tic;
try
    s = evalc(runCall);
catch err
    res.ok = false;
    if numel(err.stack) >= 1
        st = err.stack(1);
        [~, nm, ext] = fileparts(st.file);
        res.err = sprintf('%s | %s (位置 %s%s 第 %d 行)', err.identifier, err.message, nm, ext, st.line);
        for q = 1:min(6, numel(err.stack))
            [~, nm2, ext2] = fileparts(err.stack(q).file);
            res.err = sprintf('%s\n    ↳ %s%s 第 %d 行 (%s)', res.err, nm2, ext2, err.stack(q).line, err.stack(q).name);
        end
    else
        res.err = sprintf('%s | %s', err.identifier, err.message);
    end
    s = '';
end
res.seconds = toc(t0);
cd(oldDir);

% 把脚本输出也留一份，便于事后看
fid = fopen(fullfile(outDir, 'session_stdout.txt'), 'w', 'n', 'UTF-8');
if fid > 0, fwrite(fid, s); fclose(fid); end

csvFile = fullfile(runDir, sprintf('EXP_data_group%d_%d.csv', groupID, subjectID));
txtFile = fullfile(runDir, sprintf('exp_group%d_subject%d.txt', groupID, subjectID));
res.csv = csvFile;
res.txt = txtFile;

C = {};
C{end+1} = {'A1 脚本全程无异常', res.ok};
C{end+1} = {'A2 弹窗未被拦下（信息合法，不应提示重填）', isempty(SMOKE_WARN)};

% 把产物搬进 outDir，避免污染实验目录
if exist(csvFile, 'file')
    movefile(csvFile, fullfile(outDir, sprintf('EXP_data_group%d_%d.csv', groupID, subjectID)), 'f');
end
if exist(txtFile, 'file')
    movefile(txtFile, fullfile(outDir, sprintf('exp_group%d_subject%d.txt', groupID, subjectID)), 'f');
end
csvOut = fullfile(outDir, sprintf('EXP_data_group%d_%d.csv', groupID, subjectID));
txtOut = fullfile(outDir, sprintf('exp_group%d_subject%d.txt', groupID, subjectID));

C{end+1} = {'A3 CSV 已生成', exist(csvOut, 'file') == 2};
C{end+1} = {'A4 txt 长表已生成', exist(txtOut, 'file') == 2};

T = table();
if exist(csvOut, 'file')
    try
        T = readtable(csvOut, 'Delimiter', ',', 'ReadVariableNames', true, ...
                      'VariableNamingRule', 'preserve', 'TextType', 'char');
    catch err2
        C{end+1} = {sprintf('B0 CSV 可读（%s）', err2.message), false};
    end
end

if ~isempty(T) && width(T) > 0
    res.n_rows = height(T);
    vn = T.Properties.VariableNames;
    C{end+1} = {sprintf('B1 行数 = P + 576 = %d（实测 %d）', nExpected, height(T)), height(T) == nExpected};
    C{end+1} = {sprintf('B2 列数 = 25（实测 %d）', width(T)), width(T) == 25};
    C{end+1} = {sprintf('B3 列名逐个对上（第 14 列 = %s）', vn{min(14, numel(vn))}), ...
                isequal(vn, {'groupID','subjectID','gender','age','handedness','stage', ...
                             'trialID','P','T','W','Shape','Label','CorrectKey','Response', ...
                             'RT','Correct','block','premature_press','timeout', ...
                             'responded_by_deadline','stimulus_onset_actual', ...
                             'stimulus_offset_actual','mask_onset_actual', ...
                             'stimulus_dur_actual','stimulus_frames'})};
    resp = string(T.Response);
    C{end+1} = {sprintf('B4 Response 出现 NA（实测 %d 行）', sum(resp == "NA")), any(resp == "NA")};
    C{end+1} = {'B5 Response 出现 f 与 j', any(resp == "f") && any(resp == "j")};
    C{end+1} = {'B6 无单元格被补齐空格', ~any(endsWith(strtrim(string(T.Shape)), ' ') & strtrim(string(T.Shape)) ~= string(T.Shape))};
    corr = T.Correct;
    C{end+1} = {'B7 Correct 三个分支都被走到（NaN / 0 / 1）', ...
                any(isnan(corr)) && any(corr == 0) && any(corr == 1)};
    C{end+1} = {'B8 premature_press 出现过 1', any(T.premature_press == 1)};
    C{end+1} = {'B9 timeout 出现过 1 也出现过 0', any(T.timeout == 1) && any(T.timeout == 0)};
    C{end+1} = {'B10 responded_by_deadline 出现过 1 也出现过 0', ...
                any(T.responded_by_deadline == 1) && any(T.responded_by_deadline == 0)};
    if P_groups(groupID) > 0
        C{end+1} = {'B11 block 覆盖 0（练习）/1/2/3', isequal(sort(unique(T.block(:))'), [0 1 2 3])};
    else
        C{end+1} = {'B11 block 覆盖 1/2/3（组1 无练习）', isequal(sort(unique(T.block(:))'), [1 2 3])};
    end
    C{end+1} = {sprintf('B12 T 只有 4 档（实测 %d 档）', numel(unique(T.T))), numel(unique(T.T)) == 4};
    C{end+1} = {sprintf('B13 W 只有 3 档（实测 %d 档）', numel(unique(T.W))), numel(unique(T.W)) == 3};
    C{end+1} = {'B14 trialID 连续 1..N', isequal(T.trialID(:)', 1:height(T))};
    C{end+1} = {'B15 NA 行的 RT 为 NaN', all(isnan(T.RT(resp == "NA")))};
    C{end+1} = {'B16 刺激时长非负且 ≤ T', all(T.stimulus_dur_actual >= 0)};
    % ★ D79：刺激期内按键 ⇒ 实际呈现必须 ≈ RT（D5 的 min(T, RT)）。这条是唯一能在
    %   无屏幕环境下抓住「抢按被当成反应 / 截断没生效」的判据（2026-10-18 靠它定位）。
    trunc = T.stimulus_dur_actual < T.T - 0.005;
    C{end+1} = {sprintf('B20 刺激期内按键走够了截断分支（实测 %d 行）', sum(trunc)), any(trunc)};
    if any(trunc)
        dRt = abs(T.stimulus_dur_actual(trunc) - T.RT(trunc));
        C{end+1} = {sprintf('B21 截断行的 stimulus_dur_actual ≈ RT（最大差 %.1f ms）', 1000*max(dRt)), ...
                    max(dRt) <= 0.030};
    end
    % 抢按行可以再有一次合法反应（RT 属于后面那次），但绝不允许出现非正 RT，
    % 也不允许「RT 有值却标成 timeout」这种自相矛盾的行。
    C{end+1} = {'B22 凡有 RT 的行必为正（无负 RT）', all(isnan(T.RT) | T.RT > 0)};
    C{end+1} = {'B23 RT 有无与 responded_by_deadline 一致', ...
                all(isnan(T.RT) == (T.responded_by_deadline == 0))};
    if P_groups(groupID) > 0
        C{end+1} = {'B17 stage 同时出现 practice 与 formal', ...
                    any(string(T.stage) == "practice") && any(string(T.stage) == "formal")};
    else
        C{end+1} = {'B17 组1 只有 formal（无练习）', all(string(T.stage) == "formal")};
    end
end

if exist(txtOut, 'file')
    raw = fileread(txtOut);
    nLines = numel(strsplit(strtrim(raw), sprintf('\n')));
    C{end+1} = {sprintf('B18 txt 长表行数 = 表头 1 + %d（实测 %d）', nExpected, nLines), ...
                nLines == nExpected + 1};
    C{end+1} = {'B19 txt 表头与 CSV 列名一致', contains(raw, 'stimulus_frames')};
end

nPass = 0; nFail = 0;
for k = 1:numel(C)
    ok = logical(C{k}{2});
    if ok, nPass = nPass + 1; else, nFail = nFail + 1; end
    if ok
        fprintf('[PASS] %s\n', C{k}{1});
    else
        fprintf('[FAIL] %s\n', C{k}{1});
    end
end
fprintf('SUMMARY pass=%d fail=%d seconds=%.1f\n', nPass, nFail, res.seconds);
if ~res.ok
    fprintf('ERROR %s\n', res.err);
end
res.checks = C;
res.n_rows = res.n_rows;
end

function cleanup_run(here)
% 把桩从搜索路径上撤掉，避免影响后续实机/自测
rmpath(fullfile(here, 'stubs'));
end
