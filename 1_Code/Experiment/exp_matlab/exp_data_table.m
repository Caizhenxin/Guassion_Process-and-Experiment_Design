function T = exp_data_table(data, columnNames)
%EXP_DATA_TABLE 把逐试次累积的 cell 表转成 table（★ v4.4 / D78）
%
%   T = exp_data_table(data, columnNames)
%
%   data 是 exp_new_data 建出的 N×numel(columnNames) cell；本函数做两件事：
%   1) cell2table 转换（一次性，不做逐行增长）；
%   2) **把 char 矩阵列统一转成 string**。cell2table 遇到长度不一的字符向量
%      会用空格补齐成 char 矩阵（'self' / 'stranger' ⇒ 'self     '），
%      writetable 会把这些补齐空格原样写进 CSV，下游按 'self' 精确匹配就失败。
%      string(cellstr(...)) 逐行去掉尾随空格。
%
%   2026-10-18 的崩溃（D78）就是表格化太早：table 变量宽度被第一行锁死。
%
%   见 `test/check_data_accum.m`（B/C/D 组判据覆盖本函数）。

if isempty(data)
    error('exp_data_table: data 为空。至少要有 1 行才能建表（本被试一个试次都没跑完？）');
end
if size(data, 2) ~= numel(columnNames)
    error('exp_data_table: data 有 %d 列，columnNames 有 %d 个，不一致。', ...
        size(data, 2), numel(columnNames));
end

T = cell2table(data, 'VariableNames', columnNames);

for k = 1:numel(columnNames)
    name = columnNames{k};
    v = T.(name);
    if ischar(v)
        % char 矩阵（可能被空格补齐）⇒ 去尾随空格后的 string 列
        T.(name) = string(cellstr(v));
    elseif iscell(v) && all(cellfun(@ischar, v))
        T.(name) = string(v);
    end
end
end
