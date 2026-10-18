function data = exp_new_data(nCols)
%EXP_NEW_DATA 为逐试次数据表创建累积容器（★ v4.4 / D78）
%
%   data = exp_new_data(25)
%
%   返回 0×nCols 的 cell。**必须用 cell 而不是 table()**：
%   table 的变量类型由第一次赋值锁定——第一行写了 'f'（char 宽度 1），
%   这一列就固定成 1 字符宽的 char 矩阵；等到第一个 timeout 试次写 'NA'
%   （宽度 2）时报「赋值右侧的值的宽度错误。赋值需要宽度为 1 的值」并整场退出。
%   2026-10-18 实机踩过（D78）。cell 不锁定宽度，保存时用 exp_data_table 转换。
%
%   另：table 逐行 data{r,c}= 增长会反复打印
%   「赋值时将各行添加到了表格中，但并未对表格中所有现有的变量赋值」的警告，
%   并且 O(n^2) 复制；cell 累积没有这两个问题。
%
%   见 `test/check_data_accum.m`（A/B/C/D/E 五组判据）。

if nargin < 1 || isempty(nCols)
    nCols = 25;
end
assert(isscalar(nCols) && nCols > 0 && nCols == fix(nCols), ...
    'exp_new_data: nCols 必须是正整数标量。');
data = cell(0, nCols);
end
