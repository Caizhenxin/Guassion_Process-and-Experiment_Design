function check_data_accum()
%CHECK_DATA_ACCUM 无屏幕自测：逐试次数据累积 → 保存（v4.4 / D78）
%
%   cd 1_Code/Experiment/exp_matlab && addpath('test'); check_data_accum
%
% 为什么要这个自测：2026-10-18 主试实跑，跑到第一个 timeout 试次就崩——
%   `data = table()` 后逐行 `data{trialIndex,14} = respStr`，table 的变量宽度
%   被第一行 'f'（宽度 1）锁死，'NA'（宽度 2）⇒「赋值右侧的值的宽度错误」。
%   这条路径在"能跑完全程"的测试里永远看不到：只有真的出现一次未响应才会炸。
%
% 覆盖：
%   A 容器类型（cell，不是 table）+ 非法列数；
%   B 崩溃复现：'f' 之后写 'NA' 必须不报错，且 Response 保留 'NA'；
%   C 不等长文本（'self' / 'stranger'）不得留补齐空格（writetable 会写进 CSV）；
%   D 静态守卫：Exp_Design_Formal.m 里不得再出现 `data = table()` / `data.Properties`；
%   E 端到端：3 行混合响应 → 写 CSV → readtable 读回，逐列核对；
%   F 主程序实际写法 `data{trialIndex, c}`（按行号写，不是 end+1）：自动扩行不留空洞、
%     行数自检成立、cell2table 与写读回环。
%
% 任何一条不符就 error（matlab -batch 退出码非 0）。

nPass = 0; nFail = 0; failMsgs = {};

    function check(name, cond, detail)
        if cond
            nPass = nPass + 1;
            fprintf('  ✅ %s\n', name);
        else
            nFail = nFail + 1;
            failMsgs{end+1} = sprintf('%s ｜ %s', name, detail);
            fprintf('  FAIL %s ｜ %s\n', name, detail);
        end
    end

fprintf('== check_data_accum：逐试次累积与保存自测（D78）==\n');

COL = {'groupID','subjectID','gender','age','handedness','stage','trialID','P','T','W', ...
       'Shape','Label','CorrectKey','Response','RT','Correct', ...
       'block','premature_press','timeout','responded_by_deadline', ...
       'stimulus_onset_actual','stimulus_offset_actual','mask_onset_actual', ...
       'stimulus_dur_actual','stimulus_frames'};

% ---------- A. 容器 ----------
fprintf('\n[A] 累积容器\n');
data = exp_new_data(25);
check('A1 exp_new_data(25) 是 0×25 cell', iscell(data) && isequal(size(data), [0 25]), ...
      sprintf('class=%s size=%s', class(data), mat2str(size(data))));
check('A2 默认参数也是 25 列', isequal(size(exp_new_data()), [0 25]), mat2str(size(exp_new_data())));
check('A3 不是 table（table 会锁死 char 列宽）', ~istable(data), class(data));
try
    exp_new_data(0);
    check('A4 非法列数报错', false, '没有报错');
catch
    check('A4 非法列数报错', true, '');
end

% ---------- B. 崩溃复现：'f' → 'NA' ----------
fprintf('\n[B] 崩溃复现：先 ''f'' 后 ''NA''（旧版在这里 error）\n');
data = exp_new_data(25);
r1 = make_row(1, 'f', 'self', 0.42, 1);
data(end+1, :) = r1;           % 第 1 行：正常按键
r2 = make_row(1, 'NA', 'self', NaN, NaN);
data(end+1, :) = r2;           % 第 2 行：未响应 ⇒ 旧版在这里崩（'NA' 宽度 2 > 'f' 宽度 1）

check('B1 第二行写入 ''NA'' 不报错', size(data, 1) == 2, mat2str(size(data)));
check('B2 内存里 Response 两行分别是 f / NA', ...
      strcmp(data{1,14}, 'f') && strcmp(data{2,14}, 'NA'), ...
      sprintf('%s / %s', data{1,14}, data{2,14}));

T = exp_data_table(data, COL);
check('B3 转成 table 后 Response 是 string 列', isstring(T.Response), class(T.Response));
check('B4 Response 值未被补齐空格', ...
      isequal(T.Response, ["f"; "NA"]), mat2str(T.Response'));
check('B5 未响应行的 Correct 是 NaN（不是 0）', isnan(T.Correct(2)), mat2str(T.Correct'));

% ---------- C. 不等长文本不得留补齐空格 ----------
fprintf('\n[C] 不等长文本（''self'' / ''stranger''）\n');
data = exp_new_data(25);
data(end+1, :) = make_row(1, 'f', 'self', 0.5, 1);
data(end+1, :) = make_row(2, 'f', 'stranger', 0.5, 1);
T = exp_data_table(data, COL);
check('C1 Shape 两行原样保留', isequal(T.Shape, ["self"; "stranger"]), mat2str(T.Shape'));
check('C2 无尾随空格（长度 4 / 8）', strlength(T.Shape(1)) == 4 && strlength(T.Shape(2)) == 8, ...
      sprintf('%d / %d', strlength(T.Shape(1)), strlength(T.Shape(2))));

% ---------- D. 静态守卫 ----------
fprintf('\n[D] 静态守卫：Exp_Design_Formal.m\n');
srcPath = fullfile(fileparts(fileparts(mfilename('fullpath'))), 'Exp_Design_Formal.m');
check('D1 找不到 Exp_Design_Formal.m', exist(srcPath, 'file') == 2, srcPath);
srcLines = splitlines(string(fileread(srcPath)));
% 只查可执行代码：剥掉注释行（头注里会引用 `data = table()` 这个旧写法，不能算命中）
isComment = startsWith(strtrim(srcLines), '%');
code = strjoin(cellstr(srcLines(~isComment)), newline);
check('D2 用 exp_new_data 建容器', contains(code, 'data = exp_new_data(25);'), '缺 exp_new_data(25)');
check('D3 不再有 data = table()', ~contains(code, 'data = table()'), '仍有 data = table()');
check('D4 不再访问 data.Properties', ~contains(code, 'data.Properties'), '仍有 data.Properties');
check('D5 保存前用 exp_data_table 转换', contains(code, 'exp_data_table(data, columnNames)'), ...
      '缺 exp_data_table(data, columnNames)');
check('D6 仍有行数自检 warning', contains(code, 'Exp_Design_Formal:rowCount'), '缺 rowCount 自检');

% ---------- E. 端到端：写 CSV 再读回 ----------
fprintf('\n[E] 端到端：3 行 → CSV → readtable\n');
data = exp_new_data(25);
data(end+1, :) = make_row(1, 'j', 'stranger', 0.61, 1);
data(end+1, :) = make_row(2, 'NA', 'stranger', NaN, NaN);
data(end+1, :) = make_row(3, 'j', 'stranger', 0.33, 1);

T = exp_data_table(data, COL);
tmp = [tempname '.csv'];
writetable(T, tmp);
check('E1 CSV 已生成', exist(tmp, 'file') == 2, tmp);

T2 = readtable(tmp, 'TextType', 'string', 'Delimiter', ',');
check('E2 读回 3 行 25 列', isequal(size(T2), [3 25]), mat2str(size(T2)));
check('E3 Response 读回 = j / NA / j', isequal(T2.Response, ["j"; "NA"; "j"]), mat2str(T2.Response'));
check('E4 Shape 读回无补空格', isequal(T2.Shape, ["stranger"; "stranger"; "stranger"]), mat2str(T2.Shape'));
check('E5 第 2 行 Correct 是 NaN', isnan(T2.Correct(2)), mat2str(T2.Correct'));
check('E6 RT 保留数值', abs(T2.RT(3) - 0.33) < 1e-9, num2str(T2.RT(3)));

raw = fileread(tmp);
check('E7 CSV 里没有连续空格补位', isempty(regexp(raw, '\S  +\S', 'once')), ...
      regexp(raw, '\S  +\S', 'match', 'once'));

delete(tmp);

% ---------- F. 主程序实际写入模式：data{trialIndex, c}（按行号写） ----------
fprintf('\n[F] 实际写入模式：data{trialIndex, c}（v4.4 主程序就这么写）\n');
data = exp_new_data(25);
trialIndex = 1;
specs = {'practice','f','self',0.5,1; 'practice','NA','self',NaN,NaN; ...
         'formal','f','self',0.4,1; 'formal','j','stranger',0.6,0; 'formal','NA','stranger',NaN,NaN};
for k = 1:size(specs, 1)
    r = specs(k, :);
    data{trialIndex, 1} = 1;  data{trialIndex, 2} = 1;
    data{trialIndex, 3} = 2;  data{trialIndex, 4} = 21;  data{trialIndex, 5} = 2;  data{trialIndex, 8} = 0;
    data{trialIndex, 6} = r{1};  data{trialIndex, 7} = trialIndex;
    data{trialIndex, 9} = 0.033333;  data{trialIndex, 10} = 0.79998;
    data{trialIndex, 11} = r{3};     data{trialIndex, 12} = string(r{3});
    data{trialIndex, 13} = 'f';      data{trialIndex, 14} = r{2};
    data{trialIndex, 15} = r{4};     data{trialIndex, 16} = r{5};
    for c = 17:25, data{trialIndex, c} = 0; end
    trialIndex = trialIndex + 1;
end
check('F1 按行号写入后行数 = 5', size(data, 1) == 5, mat2str(size(data)));
check('F2 行数自检公式成立（size(data,1) == trialIndex-1）', size(data, 1) == trialIndex - 1, ...
      sprintf('%d vs %d', size(data,1), trialIndex-1));
check('F3 没有空单元格（自动扩行不留空洞）', ~any(cellfun(@isempty, data(:))), ...
      sprintf('%d 个空 cell', sum(cellfun(@isempty, data(:)))));
TF = exp_data_table(data, COL);
check('F4 cell2table 成功（5×25）', isequal(size(TF), [5 25]), mat2str(size(TF)));
check('F5 Response = f/NA/f/j/NA', isequal(TF.Response, ["f";"NA";"f";"j";"NA"]), mat2str(TF.Response'));
check('F6 stage 前两行 practice、后三行 formal', ...
      isequal(TF.stage, ["practice";"practice";"formal";"formal";"formal"]), mat2str(TF.stage'));
tmpF = [tempname '.csv'];
writetable(TF, tmpF);
TF2 = readtable(tmpF, 'TextType', 'string', 'Delimiter', ',');
check('F7 写 CSV 再读回 5×25', isequal(size(TF2), [5 25]), mat2str(size(TF2)));
check('F8 读回 Response 一致', isequal(TF2.Response, ["f";"NA";"f";"j";"NA"]), mat2str(TF2.Response'));
check('F9 读回 Shape 无补空格', isequal(TF2.Shape, ["self";"self";"self";"stranger";"stranger"]), ...
      mat2str(TF2.Shape'));
delete(tmpF);

% ---------- 汇总 ----------
fprintf('\n== 通过 %d / 未通过 %d ==\n', nPass, nFail);
if nFail > 0
    fprintf('失败项：\n');
    for k = 1:numel(failMsgs)
        fprintf('  - %s\n', failMsgs{k});
    end
    error('check_data_accum:failed', '%d 项未通过', nFail);
end
fprintf('✅ 全部通过\n');
end

function row = make_row(trialID, resp, shapeName, rt, correct)
%MAKE_ROW 构造一行 25 列、类型与正式程序一致的试次记录
row = cell(1, 25);
row{1}  = 1;              % groupID
row{2}  = 1;              % subjectID
row{3}  = 2;              % gender
row{4}  = 21;             % age
row{5}  = 2;              % handedness
row{6}  = "formal";       % stage
row{7}  = trialID;        % trialID
row{8}  = 0;              % P
row{9}  = 0.033333;       % T（秒）
row{10} = 0.79998;        % W（秒）
row{11} = shapeName;      % Shape（char，可能不等长）
row{12} = string(shapeName);  % Label
row{13} = 'f';            % CorrectKey
row{14} = resp;           % Response（'f' / 'j' / 'NA'）
row{15} = rt;             % RT（秒，未响应 NaN）
row{16} = correct;        % Correct（1/0/NaN）
row{17} = 1;              % block
row{18} = 0;              % premature_press
row{19} = double(isnan(correct));   % timeout
row{20} = double(~isnan(correct));  % responded_by_deadline
row{21} = 100.1;          % stimulus_onset_actual
row{22} = 100.14;         % stimulus_offset_actual
row{23} = 100.14;         % mask_onset_actual
row{24} = 0.04;           % stimulus_dur_actual
row{25} = 2;              % stimulus_frames
end