function res = check_portability()
% CHECK_PORTABILITY  v4.8 / D92 回归：当前目录 ≠ 程序目录时，整场仍跑通、数据落在当前目录
%
%   为什么需要（2026-10-18 / D92）：
%     v4.8 把掩蔽纹理从「裸文件名 imread('self10-1.png')」改成「按程序目录解析」
%     （progDir = fileparts(mfilename('fullpath'))），目的是让主试把 exp_matlab 整个文件夹
%     拷到实验室机器后，无论当前目录是什么都能跑。这条改动如果被改回裸文件名，本文件必须变红
%     —— 否则它就只是一段文档。
%
%   做法：造一个临时目录冒充「实验室的数据文件夹」并 cd 进去，用
%     run_full_session(1, 98, outDir, false)（false = 不 cd 到程序目录；脚本按名调用，
%     MATLAB 不会因此改当前目录）跑完整场，然后查 5 件事。
%
%   输出：res.ok / res.checks / res.log；日志写 test/_portability_result.txt（UTF-8）

here = fileparts(mfilename('fullpath'));
expDir = fileparts(here);
stamp = char(datetime('now', 'Format', 'yyyyMMdd_HHmmss'));
workDir = fullfile(tempdir, ['d92_port_' stamp]);
mkdir(workDir);
logFile = fullfile(here, '_portability_result.txt');

nPngBefore = numel(dir(fullfile(expDir, '*.png')));

oldDir = cd(workDir);
cleaner = onCleanup(@() portability_cleanup(oldDir, workDir)); %#ok<NASGU>
r = run_full_session(1, 98, fullfile(workDir, '_out'), false);
cd(oldDir);

outDir = fullfile(workDir, '_out');
stdoutFile = fullfile(outDir, 'session_stdout.txt');
stdout = '';
if exist(stdoutFile, 'file')
    fid = fopen(stdoutFile, 'r', 'n', 'UTF-8');
    if fid > 0, stdout = fread(fid, '*char')'; fclose(fid); end
end
nPngAfter = numel(dir(fullfile(expDir, '*.png')));

csvInWork = fullfile(outDir, 'EXP_data_group1_98.csv');
txtInWork = fullfile(outDir, 'exp_group1_subject98.txt');
csvInProg = fullfile(expDir, 'EXP_data_group1_98.csv');
txtInProg = fullfile(expDir, 'exp_group1_subject98.txt');

C = {};
C{end+1} = {'P1 当前目录 ≠ 程序目录时整场无异常', r.ok};
C{end+1} = {'P2 行数 = 576（组 1 + 被试 98）', r.n_rows == 576};
C{end+1} = {'P3 CSV/txt 落在【运行目录】而不是程序目录', ...
            exist(csvInWork, 'file') == 2 && exist(txtInWork, 'file') == 2};
C{end+1} = {'P4 程序目录里没有留下产物（没污染 exp_matlab）', ...
            exist(csvInProg, 'file') == 0 && exist(txtInProg, 'file') == 0};
C{end+1} = {'P5 启动回显报出程序目录与输出目录，且程序目录 = exp_matlab', ...
            ~isempty(strfind(stdout, '[路径] 程序目录')) && ...
            ~isempty(strfind(stdout, expDir)) && ...
            ~isempty(strfind(stdout, '[路径] 输出目录'))};
C{end+1} = {'P6 掩蔽纹理没有被拷进工作目录（10 张仍在程序目录）', ...
            nPngAfter == nPngBefore && nPngBefore >= 10 && ...
            isempty(dir(fullfile(workDir, '*.png')))};

nPass = 0;
lines = {};
lines{end+1} = sprintf('程序目录 = %s', expDir);
lines{end+1} = sprintf('运行目录 = %s', workDir);
for k = 1:numel(C)
    nm = C{k}{1}; ok = logical(C{k}{2});
    if ok
        nPass = nPass + 1;
        lines{end+1} = sprintf('PASS %s', nm);
    else
        lines{end+1} = sprintf('FAIL %s', nm);
    end
end
lines{end+1} = sprintf('SUMMARY pass=%d fail=%d', nPass, numel(C) - nPass);

fid = fopen(logFile, 'w', 'n', 'UTF-8');
if fid > 0
    fprintf(fid, '%s\n', lines{:});
    fclose(fid);
end
fprintf('%s\n', lines{:});

res = struct('ok', nPass == numel(C), 'checks', {C}, 'log', logFile);
if ~res.ok
    error('check_portability:fail', '路径可移植性回归未通过（日志 %s）', logFile);
end
end

function portability_cleanup(oldDir, workDir)
try, cd(oldDir); catch, end %#ok<CTCH>
try, rmdir(workDir, 's'); catch, end %#ok<CTCH>
end
