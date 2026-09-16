%% ptb_window_diagnostic.m
% =========================================================================
% PTB 开窗诊断脚本（用于排查 "错误使用 Screen / See error message printed above"）
%
% 用法：
%   1) 先在 MATLAB 中运行同目录上一层的 setup_paths（确认 PTB 免费版就绪）
%   2) cd 到本文件夹，运行  ptb_window_diagnostic
%   3) 屏幕上会自动进行若干次开窗尝试，结果打印在命令行，并同时写入
%      ptb_window_diagnostic_log.txt（把该文件内容发回即可定位问题）
%
% 诊断内容：
%   - PTB 版本 / MATLAB 版本 / 操作系统 / 显卡与 OpenGL 渲染器
%   - 每个屏幕的分辨率与刷新率
%   - 每屏幕 × {全屏, 小窗口} × SkipSyncTests{1} 的可开窗性（快速筛查显示可用性）
%   - 首选屏幕 × 全屏 × SkipSyncTests{0}（严格同步测试）是否通过
% =========================================================================

logFile = 'ptb_window_diagnostic_log.txt';
logID = fopen(logFile, 'w');
log = @(varargin) both_print(logID, varargin{:});

log('==== PTB 开窗诊断 %s ====\n', datestr(now, 'yyyy-mm-dd HH:MM:SS'));
log('MATLAB : %s (%s)\n', version, computer('arch'));

% --- 环境与路径检查 ---
scr = -1;
try
    scr = Screen('Screens');
    log('Screen mex : %s\n', which('Screen'));
catch e
    log('!! 无法调用 Screen：%s\n', e.message);
    log('   请先运行上一层的 setup_paths.m 配置 Psychtoolbox（免费版）。\n');
    fclose(logID);
    error('Psychtoolbox 不可用：%s', e.message);
end
try, log('Psychtoolbox: %s\n', PsychtoolboxVersion); catch, log('Psychtoolbox: 版本查询失败\n'); end
try, log('OS         : %s\n', feature('getos')); catch, log('OS         : 查询失败\n'); end

log('\n---- 屏幕列表 ----\n');
for s = scr
    try
        [sw, sh] = Screen('WindowSize', s);
        res = Screen('Resolution', s);
        log('screen %d : %d x %d, 报告刷新率 %.1f Hz\n', s, sw, sh, res.hz);
    catch e
        log('screen %d : 查询失败（%s）\n', s, e.message);
    end
end

% --- 阶段 1：快速筛查（SkipSyncTests=1，不跑同步测试）---
log('\n---- 阶段1：SkipSyncTests=1（快速）----\n');
okScreens = [];
for s = scr
    for mode = {'fullscreen', 'window'}
        if strcmp(mode{1}, 'fullscreen')
            rect = [];
        else
            rect = [0 0 800 600];
        end
        try
            Screen('Preference', 'SkipSyncTests', 1);
            [w, wr] = Screen('OpenWindow', s, [128 128 128], rect);
            log('OK   screen=%d %-10s rect=%s\n', s, mode{1}, mat2str(wr));
            % 取一次显卡/渲染器信息
            try, glinfo = Screen('GetWindowInfo', w); catch, glinfo = []; end %#ok<NASGU>
            Screen('CloseAll');
            okScreens(end + 1) = s; %#ok<AGROW>
        catch e
            log('FAIL screen=%d %-10s -> %s\n', s, mode{1}, e.message);
            try, Screen('CloseAll'); catch, end %#ok<CTCH>
        end
    end
end

% --- 阶段 2：严格同步测试（SkipSyncTests=0）---
log('\n---- 阶段2：SkipSyncTests=0（严格，等同正式采集）----\n');
if isempty(okScreens)
    log('阶段1 没有任何屏幕能开窗，跳过阶段2。\n');
else
    target = max(okScreens);
    log('测试屏幕：screen=%d（全屏）\n', target);
    t0 = GetSecs();
    try
        Screen('Preference', 'SkipSyncTests', 0);
        [w, wr] = Screen('OpenWindow', target, [128 128 128], []);
        dt = (GetSecs() - t0) * 1000;
        log('OK   同步测试通过（耗时 %.0f ms）rect=%s\n', dt, mat2str(wr));
        try
            ifi = Screen('GetFlipInterval', w);
            log('     GetFlipInterval = %.3f ms（约 %.1f Hz）\n', ifi * 1000, 1 / ifi);
        catch
        end
        Screen('CloseAll');
    catch e
        dt = (GetSecs() - t0) * 1000;
        log('FAIL 同步测试未通过（耗时 %.0f ms）-> %s\n', dt, e.message);
        log('     → 结论：需把 SkipSyncTests 设为 1 或 2，或先排查显示配置。\n');
        try, Screen('CloseAll'); catch, end %#ok<CTCH>
    end
end

% --- 汇总与建议 ---
log('\n---- 结论与建议 ----\n');
if isempty(okScreens)
    log('* 所有屏幕都无法开窗：优先检查\n');
    log('  1) 是否有其它程序占用显示（旧 MATLAB 会话 / 录屏 / 投屏 / 全屏程序）\n');
    log('  2) MATLAB 路径顺序（setup_paths 会修正：mex 目录必须排在 PsychBasic 之前）\n');
    log('  3) 显卡驱动是否正常；重启 MATLAB 后重试\n');
else
    log('* 可开窗屏幕：%s\n', mat2str(unique(okScreens)));
    log('* 若阶段2 失败：在 Exp_Design_Formal_v2.m 中把 CFG.skipSyncTest 设为 1（或 2）。\n');
    log('  v2 已内置自动回退，会自行完成这一步并打印警告。\n');
end
log('* 完整日志：%s\n', fullfile(pwd, logFile));

fclose(logID);
fprintf('\n诊断完成，日志已保存：%s\n', fullfile(pwd, logFile));
fprintf('请把该日志内容发给开发者以便定位。\n');

%% ---------- 本地函数 ----------
function both_print(logID, varargin)
    fprintf(varargin{:});
    if logID ~= -1
        fprintf(logID, varargin{:});
    end
end
