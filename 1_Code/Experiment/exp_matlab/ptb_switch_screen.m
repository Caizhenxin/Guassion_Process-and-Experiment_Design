function ptb_switch_screen(mode)
% ptb_switch_screen - 在已安装的 Psychtoolbox 中切换 Screen 的"完整版"与"轻量版"
%
% 用法：
%   ptb_switch_screen('light')  % 切换到轻量版 ScreenLight（不依赖 GStreamer，立刻可用）
%   ptb_switch_screen('full')   % 还原完整版 Screen（需要已安装 64 位 GStreamer 1.22+ MSVC）
%   ptb_switch_screen('status') % 只查看当前是哪个版本（按文件大小/备份是否存在判断）
%
% 说明：
%   - 完整版 Screen.mexw64 静态依赖 GStreamer 运行库（glib-2.0-0.dll 等），
%     未安装 GStreamer 时 MATLAB 报 "MEX 文件无效：找不到指定的模块"（错误码 126）。
%   - 轻量版 ScreenLight.mexw64 没有这些依赖，PTB 官方也说明：无 GStreamer 时
%     "Only lightweight GStreamer-less Screen() mex file will work"。
%   - 本实验（Exp_Design_Formal）只用基础绘图/文字/纹理/Flip，轻量版足够。
%   - 切换后会自动 clear mex，使新 mex 在下次调用时重新加载。
%
% 作者：为本项目（GP-SPE 实验采集）编写，2026-09

if nargin < 1 || isempty(mode)
    mode = 'status';
end
mode = lower(mode);

% 定位 Psychtoolbox 的 mex 目录：兼容 3.0.19（MatlabWindowsFilesR2007a 子目录）
% 与 3.0.20+（直接放在 PsychBasic 下）两种布局。
candidates = {};
try
    root = PsychtoolboxRoot;
    candidates{end+1} = fullfile(root, 'PsychBasic', 'MatlabWindowsFilesR2007a'); %#ok<AGROW>
    candidates{end+1} = fullfile(root, 'PsychBasic');                             %#ok<AGROW>
catch
    root = '';
end
% 若 PTB 不在路径上，退回已知安装位置
candidates{end+1} = 'D:\学习\Coding Learning\Matlab\Psychtoolbox-3.0.19.16\Psychtoolbox\PsychBasic\MatlabWindowsFilesR2007a';
candidates{end+1} = 'D:\学习\Coding Learning\Matlab\Psychtoolbox-3.0.19.16\Psychtoolbox\PsychBasic';

targetDir = '';
for i = 1:numel(candidates)
    if exist(fullfile(candidates{i}, 'Screen.mexw64'), 'file')
        targetDir = candidates{i};
        break;
    end
end
if isempty(targetDir)
    error('未找到 Screen.mexw64，请检查 Psychtoolbox 安装路径。');
end

screenMex = fullfile(targetDir, 'Screen.mexw64');
lightMex  = fullfile(targetDir, 'ScreenLight.mexw64');
backupMex = fullfile(targetDir, 'Screen.mexw64.full.bak');

fprintf('目标目录: %s\n', targetDir);
d1 = dir(screenMex); d2 = dir(backupMex); d3 = dir(lightMex);
if ~isempty(d1); fprintf('当前 Screen.mexw64: %d 字节\n', d1.bytes); end
if ~isempty(d3); fprintf('ScreenLight.mexw64: %d 字节\n', d3.bytes); end
if ~isempty(d2); fprintf('备份(完整版)      : %d 字节\n', d2.bytes); end

switch mode
    case 'status'
        if ~isempty(d2) && ~isempty(d1) && d1.bytes == d3.bytes
            fprintf('当前状态：轻量版（ScreenLight 顶替）\n');
        elseif ~isempty(d2) && ~isempty(d1) && d1.bytes == d2.bytes
            fprintf('当前状态：完整版\n');
        else
            fprintf('当前状态：无法判定（缺少备份或文件大小均不同）\n');
        end

    case 'light'
        if ~exist(lightMex, 'file')
            error('未找到 ScreenLight.mexw64，该 PTB 版本可能不提供轻量版。');
        end
        if ~exist(backupMex, 'file')
            copyfile(screenMex, backupMex);
            fprintf('已备份原 Screen.mexw64 -> Screen.mexw64.full.bak\n');
        end
        copyfile(lightMex, screenMex);
        clear mex %#ok<CLMEX>
        fprintf('已切换为轻量版 ScreenLight（无需 GStreamer）。\n');

    case 'full'
        if ~exist(backupMex, 'file')
            error(['未找到完整版备份 Screen.mexw64.full.bak，无法还原。\n' ...
                   '请重新解压 Psychtoolbox-3.0.19.16.zip 获取原始 Screen.mexw64。']);
        end
        copyfile(backupMex, screenMex);
        clear mex %#ok<CLMEX>
        fprintf('已还原完整版 Screen。若随即报"找不到指定的模块"，说明 GStreamer 未安装。\n');
        fprintf('请安装 installers\\gstreamer-1.0-msvc-x86_64-1.22.12.msi（需管理员）后重启 MATLAB。\n');

    otherwise
        error('用法: ptb_switch_screen(''light'' | ''full'' | ''status'')');
end
end
