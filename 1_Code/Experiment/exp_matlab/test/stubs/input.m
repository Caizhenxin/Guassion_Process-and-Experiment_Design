function varargout = input(prompt, varargin)
% input 桩：不读键盘。's' 模式返回空串（主试确认直接回车），数值模式返回 NaN
if nargin > 1 && ischar(varargin{1}) && strcmpi(varargin{1}, 's')
    value = '';
else
    value = NaN;
end
if nargout > 0, varargout{1} = value; end
end
