# -*- coding: utf-8 -*-
"""_fold_probe_into_check.py —— 把「按行号写入」探针（F 组 9 项）并入 check_data_accum.m

主程序 v4.4 实际用的是 `data{trialIndex, c} = ...`（按行号写），而不是 `data(end+1,:)`；
原 check_data_accum 只测了 `end+1` 写法 ⇒ 补 F 组覆盖真实写法（自动扩行、行数自检、
无空单元格、cell2table、写读回环）。
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CHK = ROOT / "1_Code/Experiment/exp_matlab/test/check_data_accum.m"

F_BLOCK = r"""
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

% ---------- 汇总 ----------"""

t = CHK.read_text(encoding="utf-8")
if "[F] 实际写入模式" in t:
    print("[跳过] F 组已存在")
else:
    anchor = "\n% ---------- 汇总 ----------"
    if t.count(anchor) != 1:
        raise SystemExit(f"❌ 汇总锚点命中 {t.count(anchor)} 次")
    t = t.replace(anchor, F_BLOCK)
    CHK.write_text(t, encoding="utf-8", newline="\n")
    print("[插入] F 组 9 项")
