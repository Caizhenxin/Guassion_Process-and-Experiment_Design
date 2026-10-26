"""自检：`stage8_run.py` 的单实例锁是否真的互斥。

拿同一个 `--out` 目录先后起两个 `--plan-only` 进程（A 先占锁并睡 6 s），B 应当
打印「⏸ 另一个实例正在写」并立刻退出、退出码 0。
"""
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")
OUT = ROOT / "_stage8_lock_test"

cmd = [sys.executable, "-u", "-X", "utf8", str(ROOT / "1_Code/DDM_Core/stage8_run.py"),
       "--data", str(ROOT / "2_Data/Real_Data/New_Design/_stage8_in"),
       "--out", str(OUT), "--plan-only"]

# A 先起，稍等让它拿到锁
a = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
time.sleep(3.0)
b = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
print("B 退出码 =", b.returncode)
print("B 输出末行 =", (b.stdout or "").strip().splitlines()[-1] if b.stdout else "")
ok_b = b.returncode == 0 and "另一个实例正在写" in (b.stdout or "")
a.wait(timeout=120)
print("A 退出码 =", a.returncode)
print("[ok] 单实例锁互斥" if ok_b else "[FAIL] 锁没有互斥")

import shutil
shutil.rmtree(OUT, ignore_errors=True)
