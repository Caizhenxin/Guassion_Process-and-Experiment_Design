% setup_paths.m
% Psychtoolbox 环境配置脚本（当前路线：免费版 PTB 3.0.19.16，无需任何许可证）
% -----------------------------------------------------------------------------
% 背景：
%   PTB 3.0.20 起，Windows/macOS 上的官方预编译 mex 需要付费许可证
%   （仅首次使用后 14 天免费）；Linux 版本仍免费。
%   3.0.19.16（2024-12-14 发布）是最后一个在 Windows 上"完全免费"的版本，
%   本机安装位置：D:\学习\Coding Learning\Matlab\Psychtoolbox-3.0.19.16\Psychtoolbox
%
% 用法：
%   首次使用在 MATLAB 中运行本脚本一次；之后可直接运行 Exp_Design_Formal。
%   换机器时：解压 installers\Psychtoolbox-3.0.19.16.zip，并修改下面的 ptbRoot。
%
% GStreamer 说明：
%   PTB 完整版 Screen 需要 64 位 GStreamer 1.22+ MSVC 运行库（免费）。
%   本机尚未安装 GStreamer，因此已把轻量版 ScreenLight 顶替为 Screen
%   （无 GStreamer 依赖；本实验只用基础绘图/文字/纹理/Flip，够用）。
%   若之后安装了 GStreamer，可运行 ptb_switch_screen('full') 还原完整版。
%
% 需要许可证的旧路线（3.0.20+ master 版）已保留在
%   D:\学习\Coding Learning\Matlab\Psychtoolbox-3-master
% 若将来购买订阅（单机 50 欧/年）可用 setup_paths_licensed_master.m 切回。
% -----------------------------------------------------------------------------

fprintf('=== Psychtoolbox 环境配置（免费版 3.0.19.16）===\n\n');

%% 步骤0: 检查 MATLAB 架构
if ~isunix && ~strcmp(computer('arch'), 'win64')
    error('需要 64 位 MATLAB。当前架构: %s', computer('arch'));
end

%% 步骤1: 定位 Psychtoolbox 目录（免费版）
ptbRoot = 'D:\学习\Coding Learning\Matlab\Psychtoolbox-3.0.19.16\Psychtoolbox';

if ~exist(ptbRoot, 'dir')
    error(['Psychtoolbox 目录未找到: %s\n' ...
           '请解压 installers\\Psychtoolbox-3.0.19.16.zip 后修改本脚本中的 ptbRoot。'], ptbRoot);
end
fprintf('[1/5] Psychtoolbox 目录: %s\n', ptbRoot);

%% 步骤2: 判断该版本是否需要许可证（3.0.20+ 才有 PsychLicenseHandling）
needsLicense = exist(fullfile(ptbRoot, 'PsychLicenseHandling.m'), 'file') ~= 0;
if needsLicense
    fprintf('[2/5] 注意：该版本需要许可证管理（首次 14 天免费，之后需订阅）。\n');
else
    fprintf('[2/5] 免费版确认：该版本不含许可证管理，可长期免费使用。\n');
end

%% 步骤3: 清理所有旧的 Psychtoolbox 路径，再加入免费版
fprintf('[3/5] 正在清理旧 Psychtoolbox 路径并添加免费版...\n');
w = warning('off', 'all');
paths = regexp(path, ['[^' pathsep ']+'], 'match');
for i = 1:length(paths)
    s = char(paths{i});
    if ~isempty(strfind(upper(s), 'PSYCHTOOLBOX')) %#ok<STREMP>
        rmpath(s);
    end
end
warning(w);
addpath(genpath(ptbRoot));

% 关键：Windows mex 目录必须排在 PsychBasic 之前，否则 Screen.m 会遮蔽 mex，
% 导致 "Missing or dysfunctional Psychtoolbox Mex file" 报错。
mexDir = fullfile(ptbRoot, 'PsychBasic', 'MatlabWindowsFilesR2007a');
if exist(mexDir, 'dir')
    addpath(mexDir, '-begin');
else
    mexDir = fullfile(ptbRoot, 'PsychBasic');
    if exist(mexDir, 'dir')
        addpath(mexDir, '-begin');
    end
end
fprintf('[3/5] 路径已更新（mex 目录已置顶: %s）。\n', mexDir);

%% 步骤4: 运行 PsychStartup 配置运行时 DLL 搜索路径
fprintf('[4/5] 正在配置运行时 DLL 搜索路径...\n');
try
    PsychStartup;
    fprintf('[4/5] 完成（若提示 GStreamer 缺失，见本脚本开头说明，属正常）。\n');
catch e
    fprintf('[4/5] 警告: PsychStartup 出错: %s\n', e.message);
end

%% 步骤5: 持久化保存路径
fprintf('[5/5] 正在保存 MATLAB 搜索路径...\n');
try
    savepath;
    fprintf('[5/5] 已保存：下次启动 MATLAB 无需重复配置。\n');
catch
    fprintf('[5/5] 警告：无法保存搜索路径（权限不足）。每次启动 MATLAB 后请重新运行本脚本。\n');
end

%% 自检
fprintf('\n=== 自检 ===\n');
try
    fprintf('PsychtoolboxVersion: %s\n', PsychtoolboxVersion);
catch e
    fprintf('PsychtoolboxVersion 调用失败: %s\n', e.message);
end
try
    clear mex; %#ok<CLMEX>
    w = which('Screen', '-all');
    if isempty(strfind([w{:}], 'mexw64')) %#ok<STREMP>
        fprintf('警告：Screen 当前解析到 .m 文件而非 mex，路径顺序可能被改动，请重新运行本脚本。\n');
    end
    Screen('Preference', 'SkipSyncTests');   % 查询式调用：只加载 mex，不修改任何设置
    fprintf('Screen 加载成功 —— 环境就绪，可以运行 Exp_Design_Formal。\n');
catch e
    fprintf('Screen 加载失败: %s\n', e.message);
    fprintf('若报"找不到指定的模块"，多为缺 GStreamer。可执行以下任一操作：\n');
    fprintf('  1) ptb_switch_screen(''light'')  —— 切换到轻量版（立刻可用，无需 GStreamer）\n');
    fprintf('  2) 安装 installers\\gstreamer-1.0-msvc-x86_64-1.22.12.msi（需管理员）后 ptb_switch_screen(''full'')\n');
end
fprintf('\n=== 配置结束 ===\n');
