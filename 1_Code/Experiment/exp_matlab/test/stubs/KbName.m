function varargout = KbName(name)
% KbName 桩：只认程序用到的几个键名；'UnifyKeyNames' 当无操作
if isnumeric(name)
    table = {'f', 'j', 'space', 'return', 'esc'};
    codes = [6, 7, 32, 13, 27];
    idx = find(codes == name, 1);
    if isempty(idx), varargout{1} = ''; else, varargout{1} = table{idx}; end
    return
end
switch lower(strtrim(char(name)))
    case 'f',        code = 6;
    case 'j',        code = 7;
    case 'space',    code = 32;
    case 'return',   code = 13;
    case {'esc', 'escape'}, code = 27;
    case 'unifykeynames'
        code = 0;                       % 无操作（程序故意不开启，见 v4 头注）
    otherwise
        code = [];                      % 未知键名 -> 空，让调用方走 fallback
end
if nargout > 0
    varargout{1} = code;
end
end
