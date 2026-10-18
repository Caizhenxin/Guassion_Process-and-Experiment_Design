function varargout = Screen(cmd, varargin)
% Screen 桩：覆盖 Exp_Design_Formal.m 用到的全部子命令，其余命令静默忽略
res = {0};
switch lower(cmd)
    case 'preference'
        res = {0};                      % 优先级设置返回值
    case 'screens'
        res = {0};                      % 只有一块屏
    case 'openwindow'
        res = {1, [0 0 1024 768]};      % [window, windowRect]
    case 'windowsize'
        res = {1024, 768};              % 真 PTB 是两个独立输出： [w, h]
    case 'getflipinterval'
        res = {1/60};
    case 'flip'
        res = {GetSecs()};              % 返回虚拟的 vbl 时刻
    case 'maketexture'
        res = {numel(varargin)};        % 任意非零句柄
    case {'closeall', 'filloval', 'fillrect', 'drawtexture', 'drawtext', ...
          'textfont', 'textsize', 'textstyle', 'textcolor'}
        res = {0};
    otherwise
        res = {0};
end
nout = max(nargout, 0);
for k = 1:nout
    if k <= numel(res)
        varargout{k} = res{k};
    else
        varargout{k} = 0;
    end
end
end
