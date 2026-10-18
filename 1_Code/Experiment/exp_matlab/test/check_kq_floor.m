function res = check_kq_floor()
% check_kq_floor  契约测试：kqFirstPressUntil(deadline, tFloor) 的 tFloor 语义（D83 / 程序 v4.6）
%
% 为什么需要这个文件
% ------------------
% v4.6 的修法只有一句话：「早于刺激 onset 的按键不算本试次反应」。但这句话被写进
% 一行比较里（`firstPress(idx(m)) > tFloor`），而**无屏幕冒烟的 27 项判据抓不到它**——
% 冒烟里的抢按都发生在注视期前段，早被 flush 掉了，根本不会走到这个比较。
% 于是修法只以「静态字符串判据（A11/A12）+ 实机数据」为证据，缺一个**可执行的契约测试**。
%
% 本测试不做复制粘贴式的"重写一遍"，而是**从 Exp_Design_Formal.m 原文里抽取**
% `kqFirstPressUntil` / `kqScan` / `resolveEscKeyCode` 三个局部函数，写入临时目录后调用
% ⇒ 测的是正在生产的代码；改坏了就红（含一条"把 floor 拿掉应当变红"的反向用例）。
%
% 用法：
%   matlab -batch "cd('...\exp_matlab'); addpath('test'); check_kq_floor"
%
% 判据（10 条，全部必须通过）：
%   C1  早于 tFloor 的键：不返回            C2  同一条键、不传 floor：**必须**返回（反例，证明测试有牙）
%   C3  刚过 tFloor（+1 ms）：返回           C4  恰好等于 tFloor：不返回（严格大于）
%   C5  恰好等于 deadline：返回              C6  晚于 deadline：不返回
%   C7  同一批两键：取最早的那个             C8  无键：空、when 为 NaN
%   C9  Esc 只计数、不当成反应               C10 早键被挡住后，窗口内的后一键仍能被取到

% ---------- 0. 定位生产代码 ----------
hereDir = fileparts(mfilename('fullpath'));
progPath = fullfile(hereDir, '..', 'Exp_Design_Formal.m');
if ~isfile(progPath)
    error('check_kq_floor:noProg', '找不到生产代码：%s', progPath);
end
lines = regexp(fileread(progPath), '\r\n|\n', 'split');

fprintf('\n== check_kq_floor：tFloor 契约测试（源：%s）==\n', progPath);

% ---------- 1. 抽取三个局部函数（按原文，不复制逻辑） ----------
blocks = { ...
    extract_function(lines, 'function [key, when, nEsc] = kqFirstPressUntil('), ...
    extract_function(lines, 'function [key, when, nEsc] = kqScan('), ...
    extract_function(lines, 'function code = resolveEscKeyCode(')};
names = {'kqFirstPressUntil', 'kqScan', 'resolveEscKeyCode'};
for k = 1:numel(blocks)
    if isempty(blocks{k})
        error('check_kq_floor:extractFail', '抽取失败：%s（生产代码的函数签名变了？）', names{k});
    end
    fprintf('   抽取 %-18s %2d 行\n', names{k}, numel(blocks{k}));
end

% ---------- 2. 写临时目录（含受控的 GetSecs / WaitSecs / KbQueueCheck） ----------
tmpDir = fullfile(hereDir, '_kq_floor_tmp');
if isfolder(tmpDir), rmdir(tmpDir, 's'); end
mkdir(tmpDir);

write_lines(fullfile(tmpDir, 'kqFirstPressUntil.m'), [ ...
    {'% 由 check_kq_floor.m 从 Exp_Design_Formal.m 抽取，勿手改（改了会被测试覆盖）'}, ...
    blocks{1}, {''}, blocks{2}, {''}, blocks{3}]);

write_lines(fullfile(tmpDir, 'GetSecs.m'), { ...
    'function t = GetSecs()', ...
    '% 受控时钟：全局 KQF_NOW，每次调用前进 1 ms（保证轮询循环必然退出）', ...
    'global KQF_NOW', ...
    'if isempty(KQF_NOW), KQF_NOW = 0; end', ...
    'KQF_NOW = KQF_NOW + 0.001;', ...
    't = KQF_NOW;', ...
    'end'});

write_lines(fullfile(tmpDir, 'WaitSecs.m'), { ...
    'function WaitSecs(seconds)', ...
    'global KQF_NOW', ...
    'if isempty(KQF_NOW), KQF_NOW = 0; end', ...
    'if nargin < 1 || isempty(seconds), seconds = 0; end', ...
    'KQF_NOW = KQF_NOW + seconds;', ...
    'end'});

write_lines(fullfile(tmpDir, 'KbQueueCheck.m'), { ...
    'function [pressed, firstPress] = KbQueueCheck()', ...
    '% 受控按键脚本：KQF_TS / KQF_CODES 里时间戳 <= 当前时刻的键全部报出来（模拟驱动行为）', ...
    'global KQF_NOW KQF_TS KQF_CODES', ...
    'if isempty(KQF_NOW), KQF_NOW = 0; end', ...
    'KQF_NOW = KQF_NOW + 0.001;', ...
    'firstPress = zeros(1, 256);', ...
    'pressed = 0;', ...
    'if isempty(KQF_TS), return; end', ...
    'hit = find(KQF_TS(:)'' <= KQF_NOW);', ...
    'for k = hit', ...
    '    firstPress(KQF_CODES(k)) = KQF_TS(k);', ...
    '    pressed = 1;', ...
    'end', ...
    'end'});

stubsDir = fullfile(hereDir, 'stubs');
% 顺序要紧：PsychStartup 已把 PTB 的 KbName 放到 path 最前，
% 若桩用 '-end' 加在后面，KbName('f') 会拿到 70（PTB 口径）而不是桩的 6，
% f/j 就永远匹配不上（D83d 实测：只有 Esc=27 两种口径一致才绿）。
addpath(stubsDir, '-begin');
addpath(tmpDir, '-begin');
cleanup = onCleanup(@() rmdir(tmpDir, 's'));
rehash;   % 让 MATLAB 立刻看到临时目录里的新函数

% ---------- 3. 用例 ----------
F = 6;  J = 7;  ESC = 27;
deadline = 100.200;
tFloor   = 100.000;

results = {};
results{end+1} = run_case('C1  早于 tFloor 的键不返回', ...
    @() kqFirstPressUntil(deadline, tFloor), 99.990, F, true, @(k, w, e) isempty(k) && isnan(w) && e == 0);
results{end+1} = run_case('C2  反向：不传 floor 时必须返回同一条键（证明测试有牙）', ...
    @() kqFirstPressUntil(deadline), 99.990, F, true, @(k, w, e) strcmp(k, 'f') && abs(w - 99.990) < 1e-9);
results{end+1} = run_case('C3  刚过 tFloor（+1 ms）返回', ...
    @() kqFirstPressUntil(deadline, tFloor), 100.001, F, true, @(k, w, e) strcmp(k, 'f') && abs(w - 100.001) < 1e-9);
results{end+1} = run_case('C4  恰好等于 tFloor 不返回（严格大于）', ...
    @() kqFirstPressUntil(deadline, tFloor), 100.000, F, true, @(k, w, e) isempty(k));
results{end+1} = run_case('C5  恰好等于 deadline 返回（闭区间上界）', ...
    @() kqFirstPressUntil(deadline, tFloor), 100.200, F, true, @(k, w, e) strcmp(k, 'f') && abs(w - 100.200) < 1e-9);
results{end+1} = run_case('C6  晚于 deadline 不返回', ...
    @() kqFirstPressUntil(deadline, tFloor), 100.260, F, true, @(k, w, e) isempty(k));
results{end+1} = run_case('C9  Esc 只计数、不当反应', ...
    @() kqFirstPressUntil(deadline, tFloor), 100.010, ESC, true, @(k, w, e) isempty(k) && e >= 1);

% 两条"多键"用例：stub 支持一次报多个键
results{end+1} = run_case_multi('C7  同一批两键取最早', ...
    @() kqFirstPressUntil(deadline, tFloor), [100.050 100.020], [J F], ...
    @(k, w, e) strcmp(k, 'f') && abs(w - 100.020) < 1e-9);
results{end+1} = run_case_multi('C10 早键被挡住后，窗口内后一键仍取到（D83 机制）', ...
    @() kqFirstPressUntil(deadline, tFloor), [99.900 100.050], [F J], ...
    @(k, w, e) strcmp(k, 'j') && abs(w - 100.050) < 1e-9);
results{end+1} = run_case('C8  无键：空 + when=NaN', ...
    @() kqFirstPressUntil(deadline, tFloor), [], F, false, @(k, w, e) isempty(k) && isnan(w));

% ---------- 4. 汇总 ----------
nPass = 0;
for k = 1:numel(results)
    if results{k}, nPass = nPass + 1; end
end
nAll = numel(results);
fprintf('\n%s\n', repmat('-', 1, 62));
fprintf('SUMMARY pass=%d fail=%d\n', nPass, nAll - nPass);
res.pass = nPass;
res.fail = nAll - nPass;

% 结果落盘（UTF-8）：check_full_session.py 读这一行断言，仓库校验不必调用 MATLAB
logPath = fullfile(hereDir, '_kq_floor_result.txt');
fid = fopen(logPath, 'w', 'n', 'UTF-8');
if fid >= 0
    fprintf(fid, 'SUMMARY pass=%d fail=%d\n', nPass, nAll - nPass);
    for k = 1:numel(results)
        if results{k}, tag = 'PASS'; else, tag = 'FAIL'; end
        fprintf(fid, '%s case%d\n', tag, k);
    end
    fclose(fid);
else
    warning('check_kq_floor:log', '结果日志写不进去：%s', logPath);
end

if nPass ~= nAll
    error('check_kq_floor:fail', 'tFloor 契约测试未通过：%d/%d', nPass, nAll);
end
end

% ================= 以下为测试自身的小工具（不复刻被测逻辑） =================

function out = extract_function(lines, sig)
% 按签名找到函数起点，再找其后第一个"列 1 的 end"作为终点；返回行元胞数组
out = {};
i0 = [];
for i = 1:numel(lines)
    if startsWith(lines{i}, sig)
        i0 = i; break
    end
end
if isempty(i0), return; end
for j = i0:numel(lines)
    if strcmp(lines{j}, 'end')
        out = lines(i0:j);
        return
    end
end
end

function write_lines(path, cellLines)
fid = fopen(path, 'w');
if fid < 0, error('check_kq_floor:write', '无法写 %s', path); end
for i = 1:numel(cellLines)
    fprintf(fid, '%s\n', cellLines{i});
end
fclose(fid);
end

function tf = run_case(label, fn, ts, code, hasKey, pred)
% 单键（或无键）用例：清全局 → 装脚本 → 调用 → 判
global KQF_NOW KQF_TS KQF_CODES
KQF_NOW = 100.000;   % 从 tFloor 起步，让时钟在窗口内走动
if hasKey
    KQF_TS = ts; KQF_CODES = code;
else
    KQF_TS = []; KQF_CODES = [];
end
[k, w, e] = fn();
tf = pred(k, w, e);
report(label, tf, k, w, e);
end

function tf = run_case_multi(label, fn, tsVec, codeVec, pred)
global KQF_NOW KQF_TS KQF_CODES
KQF_NOW = 100.000;
KQF_TS = tsVec; KQF_CODES = codeVec;
[k, w, e] = fn();
tf = pred(k, w, e);
report(label, tf, k, w, e);
end

function report(label, tf, k, w, e)
if isempty(k), ks = '(空)'; else, ks = k; end
if isnan(w), ws = 'NaN'; else, ws = sprintf('%.3f', w); end
tag = 'FAIL';
if tf, tag = 'PASS'; end
fprintf('[%s] %s ⇒ key=%s when=%s nEsc=%d\n', tag, label, ks, ws, e);
end
