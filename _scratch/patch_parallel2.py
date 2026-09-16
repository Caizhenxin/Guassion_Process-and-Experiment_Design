# -*- coding: utf-8 -*-
"""临时：修复 param_recovery_frozen6.py 的编码与并行日志方式。"""
from pathlib import Path

p = Path(__file__).resolve().parent.parent / "1_Code" / "Python_for_Check" / \
    "TenRules_Revision_20260912" / "param_recovery_frozen6.py"
s = p.read_text(encoding="utf-8")

# 1) stdout 编码兜底
if "sys.stdout.reconfigure" not in s:
    s = s.replace(
        "sys.path.insert(0, str(Path(__file__).resolve().parent))",
        "sys.path.insert(0, str(Path(__file__).resolve().parent))\n"
        "try:  # 控制台编码兜底（避免 ⚠️ 等字符在 GBK 控制台报错）\n"
        "    sys.stdout.reconfigure(encoding=\"utf-8\", errors=\"replace\")\n"
        "except Exception:\n"
        "    pass", 1)

# 2) 并行执行：改为每作业写日志文件（不捕获管道）
old = '''    def _one(idx_job):
        idx, job = idx_job
        r = subprocess.run(_docker_cmd(job, image, mount), capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        with box["lock"]:
            if r.returncode == 0:
                box["ok"] += 1
                print(f"[fit-docker] ({idx}/{len(todo)}) {job['tag']} 完成 ✓", flush=True)
            else:
                box["fail"] += 1
                print(f"[fit-docker] ({idx}/{len(todo)}) {job['tag']} 失败：{r.returncode} "
                      f"{(r.stderr or '')[-200:]}", flush=True)'''
new = '''    def _one(idx_job):
        idx, job = idx_job
        log_path = FITS / job["scheme"] / f"{job['tag']}.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "w", encoding="utf-8", errors="replace") as fh:
            r = subprocess.run(_docker_cmd(job, image, mount), stdout=fh, stderr=subprocess.STDOUT)
        with box["lock"]:
            if r.returncode == 0:
                box["ok"] += 1
                print(f"[fit-docker] ({idx}/{len(todo)}) {job['tag']} 完成", flush=True)
            else:
                box["fail"] += 1
                print(f"[fit-docker] ({idx}/{len(todo)}) {job['tag']} 失败：returncode={r.returncode}"
                      f"（详见 {log_path.name}）", flush=True)'''
assert s.count(old) == 1, f"并行块未匹配 {s.count(old)}"
s = s.replace(old, new)

# 3) 防御：若某作业已有 log 但无 stats，视为失败并重试
p.write_text(s, encoding="utf-8")
print("patched:", p.name, "| reconfigure:", "sys.stdout.reconfigure" in s)
