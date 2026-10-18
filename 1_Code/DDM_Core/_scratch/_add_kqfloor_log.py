# -*- coding: utf-8 -*-
"""check_kq_floor.m 把结果落盘成 UTF-8 日志，供 check_full_session.py 断言。

为什么：契约测试要跑 MATLAB（几十秒），而仓库校验是纯 Python、零依赖、秒级完成。
把一次跑出的事实（pass=10 fail=0）落成文件，校验脚本读文件即可，既保留了牙齿，
又不必让 check_full_session.py 去调 MATLAB。
"""
import io
import sys

p = sys.argv[1]
src = io.open(p, encoding="utf-8", newline="").read()

old = """res.fail = nAll - nPass;
if nPass ~= nAll"""
new = """res.fail = nAll - nPass;

% 结果落盘（UTF-8）：check_full_session.py 读这一行断言，仓库校验不必调用 MATLAB
logPath = fullfile(hereDir, '_kq_floor_result.txt');
fid = fopen(logPath, 'w', 'n', 'UTF-8');
if fid >= 0
    fprintf(fid, 'SUMMARY pass=%d fail=%d\\n', nPass, nAll - nPass);
    for k = 1:numel(results)
        if results{k}, tag = 'PASS'; else, tag = 'FAIL'; end
        fprintf(fid, '%s case%d\\n', tag, k);
    end
    fclose(fid);
else
    warning('check_kq_floor:log', '结果日志写不进去：%s', logPath);
end

if nPass ~= nAll"""
assert src.count(old) == 1, "命中 %d 次" % src.count(old)
io.open(p, "w", encoding="utf-8", newline="\n").write(src.replace(old, new))
print("patched")
