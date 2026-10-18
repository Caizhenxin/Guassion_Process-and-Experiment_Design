# -*- coding: utf-8 -*-
"""D92 牙齿：给 check_full_session.py 加 A14（v4.8 静态判据）与 B30（可移植性回归）。

为什么：v4.8 把掩蔽纹理从裸文件名改成按程序目录解析，这类「路径写在哪」的改动
静态上很容易被后人改回去而又不留痕迹（裸文件名在开发机上永远能跑通，因为当前目录
恰好就是程序目录）。所以既要静态钉住形状，也要有可执行回归。

幂等；逐处断言命中 1 次。
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
F = ROOT / "1_Code/Experiment/exp_matlab/test/check_full_session.py"

OLD_COUNT = "本脚本只负责「四条防线都还在、产物也真的被读通过」，秒级、可进 CI（共 30 项）。"
NEW_COUNT = "本脚本只负责「四条防线都还在、产物也真的被读通过」，秒级、可进 CI（共 32 项）。"

OLD_B_LIST = (
    "B 驱动侧（run_full_session 的 B20–B23 判据、桩目录完整、日志走 UTF-8、"
    "D84 的 tFloor 契约测试 B27–B29）"
)
NEW_B_LIST = (
    "B 驱动侧（run_full_session 的 B20–B23 判据、桩目录完整、日志走 UTF-8、"
    "D84 的 tFloor 契约测试 B27–B29、D92 的路径可移植性回归 B30）"
)

OLD_A13 = '''check("A13 v4.7 松键门槛：8 处空格等待之前都先等一次松键（D90）",
      "function waitForSpaceRelease()" in code
      and code.count("waitForSpaceRelease();") == 8
      and "★★ v4.7 本次修正" in prog)
'''
NEW_A13 = OLD_A13 + '''
check("A14 v4.8 路径可移植：掩蔽纹理按程序目录解析、启动即自检 10 张 PNG（D92）",
      "★★ v4.8 本次修正" in prog
      and "progDir = fileparts(mfilename('fullpath'));" in code
      and code.count("fullfile(progDir, f)") == 2
      and "assert(isempty(missingMask)" in code
      and "selfMaskImages = {'self10-1.png'" not in code   # 裸文件名列表必须已消失
      and code.find("progDir = fileparts") < code.find("screenXpixels"))
'''

OLD_B29 = '''check("B29 契约测试结果已落盘且 pass=10 fail=0",
      "SUMMARY pass=10 fail=0" in kqlog_txt and kqlog_txt.count("PASS case") == 10,
      "" if kqlog.exists() else "日志不存在（先跑一次 check_kq_floor.m）")
'''
NEW_B29 = OLD_B29 + '''
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
'''

src = F.read_text(encoding="utf-8")
assert "A14 v4.8" not in src, "已打过 D92 补丁"
for old, new, tag in [
    (OLD_COUNT, NEW_COUNT, "项数"),
    (OLD_B_LIST, NEW_B_LIST, "B 说明"),
    (OLD_A13, NEW_A13, "A13"),
    (OLD_B29, NEW_B29, "B29"),
]:
    n = src.count(old)
    assert n == 1, f"{tag}: 命中 {n} 次"
    src = src.replace(old, new)

F.write_text(src, encoding="utf-8", newline="\n")
print(f"D92 牙齿补丁完成：{F.name} {len(src.splitlines())} 行")
