# -*- coding: utf-8 -*-
"""check_full_session.py 追加 D83 的 tFloor 契约测试三条牙齿（26 → 29）。

为什么值得加：v4.6 的核心修法「onset 之前的键不算反应」只体现在一行 `> tFloor` 上，
一旦有人为了「修漏答」把比较改回 `>=` 或把参数删掉，整套冒烟测试仍然全绿
（冒烟桩的按键时刻与铺助线无关），只有把契约钉在代码上才拦得住。
"""
import io
import sys

p = sys.argv[1]
src = io.open(p, encoding="utf-8", newline="").read()

old = 'check("B26 驱动日志走 UTF-8（不靠 PowerShell 重定向）", "UTF-8" in batch)\n'
new = '''check("B26 驱动日志走 UTF-8（不靠 PowerShell 重定向）", "UTF-8" in batch)

# tFloor 契约测试（D83）：把「onset 之前的键不算反应」钉在可执行断言上
kq = TEST / "check_kq_floor.m"
kq_src = kq.read_text(encoding="utf-8") if kq.exists() else ""
ncase = kq_src.count("results{end+1} = run_case")
check("B27 tFloor 契约测试存在且十条用例齐（C1–C10）", ncase == 10, f"实测 {ncase} 条")
i_stub = kq_src.find("addpath(stubsDir, '-begin')")
i_tmp = kq_src.find("addpath(tmpDir, '-begin')")
check("B28 桩目录压在 PTB 之前（D83d：否则 KbName('f') 拿到 70，f/j 永远匹配不上）",
      i_stub >= 0 and i_tmp > i_stub and "addpath(stubsDir, '-end')" not in kq_src)
kqlog = TEST / "_kq_floor_result.txt"
kqlog_txt = read_any(kqlog) if kqlog.exists() else ""
check("B29 契约测试结果已落盘且 pass=10 fail=0",
      "SUMMARY pass=10 fail=0" in kqlog_txt and kqlog_txt.count("PASS case") == 10,
      "" if kqlog.exists() else "日志不存在（先跑一次 check_kq_floor.m）")
'''
assert src.count(old) == 1, "命中 %d 次" % src.count(old)
io.open(p, "w", encoding="utf-8", newline="\n").write(src.replace(old, new))
print("patched")
