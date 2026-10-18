function runbatch_full_session(groupID, subjectID)
% RUNBATCH_FULL_SESSION  无屏幕驱动入口：跑整场并在 test/ 下留 UTF-8 日志
%
%   matlab -batch "cd('...\exp_matlab'); addpath('test'); runbatch_full_session(2, 99)"
%
% 为什么包一层：-batch 的 stdout 是 GBK，直接重定向中文会乱码；这里在 MATLAB 内部
% 用 evalc 抓取 + fopen(...,'UTF-8') 写盘，日志才能被 Python 检查器正确读取。

here = fileparts(mfilename('fullpath'));
fn = fullfile(here, sprintf('_full_session_g%d_s%d.txt', groupID, subjectID));
a = onCleanup(@() none());
try
    s = evalc('run_full_session(groupID, subjectID)');
catch err
    s = sprintf('DRIVER-ERROR %s | %s\n', err.identifier, err.message);
end
fid = fopen(fn, 'w', 'n', 'UTF-8');
if fid < 0
    error('无法写日志：%s', fn);
end
fwrite(fid, s);
fclose(fid);
fprintf(1, '%s', s);
end

function none()
end
