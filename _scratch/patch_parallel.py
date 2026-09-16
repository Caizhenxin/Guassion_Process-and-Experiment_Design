# -*- coding: utf-8 -*-
"""临时：为 param_recovery_frozen6.py 增加并行执行能力。"""
from pathlib import Path

p = Path(__file__).resolve().parent.parent / "1_Code" / "Python_for_Check" / \
    "TenRules_Revision_20260912" / "param_recovery_frozen6.py"
s = p.read_text(encoding="utf-8")

# 1) 每个容器 2 核（20 核机器上 4 并行不超配）
s = s.replace('"docker", "run", "--rm", "--cpus=4",', '"docker", "run", "--rm", "--cpus=2",')

# 2) run_docker 支持并行
old = '''    for i, job in enumerate(todo, 1):
        print(f"[fit-docker] ({i}/{len(todo)}) {job['tag']} ...", flush=True)
        r = subprocess.run(_docker_cmd(job, image, mount))
        if r.returncode != 0:
            print(f"  ⚠️ {job['tag']} 拟合失败（returncode={r.returncode}）")
    print("[fit-docker] 全部作业执行完毕")'''
new = '''    box = {"ok": 0, "fail": 0, "lock": None}
    import threading
    box["lock"] = threading.Lock()

    def _one(idx_job):
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
                      f"{(r.stderr or '')[-200:]}", flush=True)

    if parallel and parallel > 1:
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=int(parallel)) as ex:
            list(ex.map(_one, list(enumerate(todo, 1))))
    else:
        for item in enumerate(todo, 1):
            _one(item)
    print(f"[fit-docker] 全部作业执行完毕（成功 {box['ok']} / 失败 {box['fail']}）")'''
assert s.count(old) == 1, f"run_docker 循环未匹配：{s.count(old)}"
s = s.replace(old, new)

# 3) 函数签名与参数
s = s.replace('def run_docker(jobs: list[dict], image: str, mount: str, dry_run: bool, skip_existing: bool):',
              'def run_docker(jobs: list[dict], image: str, mount: str, dry_run: bool, skip_existing: bool,\n               parallel: int = 1):')
s = s.replace('    ap.add_argument("--skip-existing", action="store_true", default=True)',
              '    ap.add_argument("--skip-existing", action="store_true", default=True)\n'
              '    ap.add_argument("--parallel", type=int, default=4, help="并行运行的 docker 容器数（默认 4）")')
s = s.replace('run_docker(jobs, args.image, args.mount, args.dry_run, args.skip_existing)',
              'run_docker(jobs, args.image, args.mount, args.dry_run, args.skip_existing, args.parallel)')

p.write_text(s, encoding="utf-8")
print("patched:", p.name)
print("检查：", "parallel" in s, "| --cpus=2:", '"--cpus=2"' in s)
