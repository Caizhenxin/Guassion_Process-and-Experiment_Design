# -*- coding: utf-8 -*-
"""check_full_session.py —— D79 的仓库侧牙齿（静态 + 已落盘日志）

它不替代 MATLAB：真正跑整场的是
    matlab -batch "cd('1_Code/Experiment/exp_matlab'); addpath('test'); runbatch_full_session(1, 99);"
本脚本只负责「四条防线都还在、产物也真的被读通过」，秒级、可进 CI（共 32 项）。

分组：
  A 程序侧（v4.5 三处 + v4.6 onset 边界修正仍在，且没有回退到旧写法）—— 一律先剥掉注释行再判
  B 驱动侧（run_full_session 的 B20–B23 判据、桩目录完整、日志走 UTF-8、D84 的 tFloor 契约测试 B27–B29、D92 的路径可移植性回归 B30）
  C 产物侧（两组冒烟日志 pass=27 fail=0；read_formal_data.py 判通过）
  D 反例侧（把修正拿掉后 A 组确实会失败 —— 证明判据不是空的）
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
MP = ROOT / "1_Code" / "Experiment" / "exp_matlab"
TEST = MP / "test"
PROG = MP / "Exp_Design_Formal.m"
RUNNER = TEST / "run_full_session.m"
BATCH = TEST / "runbatch_full_session.m"
STUBS = TEST / "stubs"

fails: list[str] = []
npass = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global npass
    if ok:
        npass += 1
        print(f"[PASS] {name}")
    else:
        fails.append(name)
        print(f"[FAIL] {name}{('  ' + detail) if detail else ''}")


def read_any(path: Path) -> str:
    """日志可能是 PowerShell `*>` 写出的 UTF-16，也可能是 UTF-8。"""
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "utf-16", "gbk"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def strip_comments(matlab_src: str) -> str:
    """去掉整行注释（程序里 % 开头的行），保留代码行。"""
    return "\n".join(ln for ln in matlab_src.split("\n") if not ln.lstrip().startswith("%"))


prog = PROG.read_text(encoding="utf-8")
code = strip_comments(prog)
runner = RUNNER.read_text(encoding="utf-8")
batch = BATCH.read_text(encoding="utf-8")

# ---------------- A 程序侧 ----------------
check("A1 程序文件存在且 >1000 行", len(prog.split("\n")) > 1000)
check("A2 抢按后立即 KbQueueFlush（练习段 + 正式段各一处，代码里另有 2 处试次开头的 flush）",
      code.count("KbQueueFlush();") == 4 and prog.count("D79）：抢按已经记进 premature_press") == 2)
check("A3 反应时为正的兜底（2 处）", code.count("responseTime <= 0") == 2)
check("A4 抢按清理紧跟在 prematurePress 之后",
      len(re.findall(r"prematurePress = double\(nPreKey > 0\);\s*\n\s*if prematurePress > 0", code)) == 2)
check("A5 保存前 fclose 逐试次 txt 通道", "fclose(fileID);" in code and "D79）：关闭逐试次 txt 通道" in prog)
check("A6 关窗之前完成落盘（fclose 在 Screen('CloseAll') 之前）",
      code.find("fclose(fileID);") >= 0 and code.find("fclose(fileID);") < code.find("Screen('CloseAll');"))
check("A7 两段的 RT 都来自同一个算式（respAbs − stimulusFlipTime，共 4 处：刺激期 ×2、反应窗 ×2）",
      code.count("responseTime = respAbs - stimulusFlipTime;") == 4)
check("A8 v4.5 变更段已在头注", "★ v4.5 本次修正" in prog)
check("A8b v4.6 变更段已在头注（onset 之前的键不算反应）", "★ v4.6 本次修正" in prog)
check("A11 四个反应窗口都传了 tFloor = stimulusFlipTime（练习/正式 × 刺激期/反应窗）",
      code.count("kqFirstPressUntil(stimulusFlipTime + ") == 4
      and code.count(", stimulusFlipTime);   % ★ v4.6") == 4)
check("A12 kqFirstPressUntil / kqScan 都已接 tFloor，且扫描时用它裁边界",
      "function [key, when, nEsc] = kqFirstPressUntil(deadline, tFloor)" in code
      and code.count("escCode, tFloor);") == 2
      and "firstPress(idx(m)) > tFloor" in code)
check("A9 数据容器仍走 exp_new_data / exp_data_table（v4.4 未回退）",
      "exp_new_data(25)" in code and "exp_data_table(data, columnNames)" in code)
check("A10 代码里不再出现 `data = table()`（注释里的来历说明不算）",
      "data = table()" not in code)

check("A13 v4.7 松键门槛：8 处空格等待之前都先等一次松键（D90）",
      "function waitForSpaceRelease()" in code
      and code.count("waitForSpaceRelease();") == 8
      and "★★ v4.7 本次修正" in prog)

check("A14 v4.8 路径可移植：掩蔽纹理按程序目录解析、启动即自检 10 张 PNG（D92）",
      "★★ v4.8 本次修正" in prog
      and "progDir = fileparts(mfilename('fullpath'));" in code
      and code.count("fullfile(progDir, f)") == 3   # 1 处 PNG 自检 + 2 处纹理列表
      and "assert(isempty(missingMask)" in code
      and "selfMaskImages = {'self10-1.png'" not in code   # 裸文件名列表必须已消失
      and code.find("progDir = fileparts") < code.find("screenXpixels"))

# ---------------- B 驱动侧 ----------------
for tag, desc in [
    ("B20", "刺激期内按键走够了截断分支"),
    ("B21", "截断行的 stimulus_dur_actual ≈ RT"),
    ("B22", "凡有 RT 的行必为正"),
    ("B23", "RT 有无与 responded_by_deadline 一致"),
]:
    check(f"B {tag} 判据仍在驱动里（{desc}）", tag in runner)
nstub = len(list(STUBS.glob("*.m")))
check("B24 桩目录 24 个文件", nstub == 24, f"实测 {nstub}")
check("B25 产物被搬出程序目录（避免与真实数据混）",
      "_full_session_out" in runner or "_full_session_out" in batch)
check("B26 驱动日志走 UTF-8（不靠 PowerShell 重定向）", "UTF-8" in batch)

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

# 路径可移植性回归（D92）：当前目录 ≠ 程序目录时整场仍能跑通、数据落在当前目录
port = TEST / "check_portability.m"
port_src = port.read_text(encoding="utf-8") if port.exists() else ""
portlog = TEST / "_portability_result.txt"
portlog_txt = read_any(portlog) if portlog.exists() else ""
check("B30 可移植性回归存在且 6/6 通过（当前目录 ≠ 程序目录跑整场）",
      port_src.count("C{end+1} = {'P") == 6
      and "runInProgramDir" in runner
      and "SUMMARY pass=6 fail=0" in portlog_txt,
      "" if portlog.exists() else "日志不存在（先跑一次 check_portability.m）")

# ---------------- C 产物侧 ----------------
for g in (1, 2):
    log = TEST / f"_full_session_g{g}_s99.txt"
    ok = log.exists() and "pass=27 fail=0" in read_any(log)
    check(f"C{g} 组 {g} 冒烟日志 pass=27 fail=0", ok, "" if log.exists() else "日志不存在")

reader_log = TEST / "_read_formal_session.txt"
if reader_log.exists():
    rt = read_any(reader_log)
    check("C3 read_formal_data.py 端到端判通过（2 个文件）", "2 个文件全部通过" in rt)
else:
    check("C3 read_formal_data.py 端到端判通过（2 个文件）", False, "日志不存在")
check("C4 产物目录里两组 CSV/txt 都在",
      all((TEST / "_full_session_out" / n).exists() for n in (
          "EXP_data_group1_99.csv", "EXP_data_group2_99.csv",
          "exp_group1_subject99.txt", "exp_group2_subject99.txt")))

# ---------------- D 反例侧 ----------------
broke = code.replace("responseTime <= 0", "false", 1)
check("D1 去掉一处兜底后 A3 会失败（反例自检）", broke.count("responseTime <= 0") != 2)
broke2 = code.replace("KbQueueFlush();", "", 1)
check("D2 去掉一处 flush 后 A2 会失败（反例自检）", broke2.count("KbQueueFlush();") != 4)

print()
print(f"== 通过 {npass} / 未通过 {len(fails)} ==")
for f in fails:
    print("  ✗", f)
sys.exit(1 if fails else 0)
