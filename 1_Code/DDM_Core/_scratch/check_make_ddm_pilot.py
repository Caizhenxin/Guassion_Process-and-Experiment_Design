# -*- coding: utf-8 -*-
"""`_scratch/_make_ddm_pilot.py` 的自测 —— 确保「正向对照」的数据确实是 DDM 生成的。

为什么需要它：

* `make_fake_pilot.py` 没有证据累积过程，用它跑 Stage 8 时 PPC 必然失配（阴性
  对照成功）。补正向对照的前提是**生成器真的用 DDM 生成数据**——如果它悄悄退化成
  「按规则表造 RT」，那 Stage 8 的 PPC 通过就什么都证明不了；
* 生成器与 `read_formal_data` 的**约定**（`Response=NA` ⇒ `RT`/`Correct` 都是 NaN、
  `timeout=1`；`Correct == (Response == CorrectKey)`）必须逐条钉住，否则文件能被
  读进来但语义是错的——那比读不进来更危险。

跑法：``python -X utf8 1_Code/DDM_Core/_scratch/check_make_ddm_pilot.py``
"""

from __future__ import annotations

import inspect
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
CORE = HERE.parent
REPO = CORE.parent.parent
EXP_DIR = REPO / "1_Code" / "Experiment"
for _p in (CORE, EXP_DIR, HERE):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import read_formal_data as RF                      # noqa: E402

FAILS: list[str] = []
N_OK = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global N_OK
    if ok:
        N_OK += 1
        print(f"  ✅ {name}" + (f"：{detail}" if detail else ""))
    else:
        FAILS.append(name)
        print(f"  ❌ {name}" + (f"：{detail}" if detail else ""))


def raw_rows(path: Path) -> list[list[str]]:
    txt = path.read_text(encoding="utf-8")
    return [ln.split("\t") for ln in txt.rstrip("\n").split("\n")]


def main() -> int:
    print("=" * 100)
    print("  `_make_ddm_pilot.py` 自测")
    print("=" * 100)

    with tempfile.TemporaryDirectory() as td:
        # G4 要看「遗漏行」，但一次小样本常常零遗漏 ⇒ 换几个种子直到出现遗漏
        # （最多 3 次）。这是**为了让那条判据真的被触发**，不是放宽它。
        proc = None
        chosen = None
        for seed in (11, 12, 13):
            out = Path(td) / f"pilot{seed}"
            proc = subprocess.run(
                [sys.executable, "-X", "utf8", str(HERE / "_make_ddm_pilot.py"), str(out),
                 "--n-subjects", "1", "--n-rep", "2", "--seed", str(seed)],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                cwd=str(REPO))
            files = sorted(out.glob("*.txt"))
            if proc.returncode != 0 or not files:
                continue
            cand = raw_rows(files[0])
            i_to = cand[0].index("timeout")
            if any(r[i_to] == "1" for r in cand[1:]):
                chosen = (files[0], cand)
                break

        check("G1 生成器能跑通且样本里出现遗漏行（exit 0、1 份 txt）",
              proc is not None and proc.returncode == 0 and chosen is not None,
              f"exit={None if proc is None else proc.returncode}")

        if chosen is not None:
            path, rows = chosen
            hdr, body = rows[0], rows[1:]
            check("G2 表头与 `read_formal_data.HEADER25` 逐字一致",
                  tuple(hdr) == tuple(RF.HEADER25), f"{len(hdr)} 列")
            check("G3 试次数与设计一致（4 T × 3 W × 4 类 × 2 次 = 96）",
                  len(body) == 96, f"{len(body)} 行")

            i_resp, i_rt = hdr.index("Response"), hdr.index("RT")
            i_corr, i_rbd = hdr.index("Correct"), hdr.index("responded_by_deadline")
            i_ck, i_T = hdr.index("CorrectKey"), hdr.index("T")
            om = [r for r in body if r[i_to] == "1"]
            ok_om = all(r[i_resp] == "NA" and r[i_rt] == "NaN" and r[i_corr] == "NaN"
                        and r[i_rbd] == "0" for r in om)
            check("G4 遗漏行：`Response=NA`、`RT`/`Correct` 为 NaN、`timeout=1`、"
                  "`responded_by_deadline=0`", ok_om and om, f"{len(om)} 行")
            resp = [r for r in body if r[i_to] == "0"]
            check("G5 已响应行的 `Correct == (Response == CorrectKey)`",
                  all(int(r[i_corr]) == (1 if r[i_resp] == r[i_ck] else 0) for r in resp),
                  f"{len(resp)} 行")
            tvals = {round(float(r[i_T]), 5) for r in body}
            check("G6 T 水平是 4 档", len(tvals) == 4, f"T = {sorted(tvals)}")

            rec, rep = RF.load_file(path)
            tr = RF.to_trials(rec)
            n_om = int(np.sum(tr["omission"]))
            n_bad_side = int(np.sum(~np.isin(tr["side"], [0, 1])))
            check("G7 经 `to_trials` 后 omission/side 的形状合法",
                  n_bad_side == 0 and n_om == len(om),
                  f"omission={n_om}、非法 side={n_bad_side}")
            check("G8 响应的 RT 全为有限正值",
                  bool(np.all(np.isfinite(tr["rt"][tr["omission"] == 0]))),
                  f"max rt = {np.nanmax(tr['rt']):.3f} s")
    src = (HERE / "_make_ddm_pilot.py").read_text(encoding="utf-8")
    check("G9 静态：生成器用 `twophase.simulate_euler_subject` 且把 rho 传进去",
          "simulate_euler_subject" in src and "float(args.rho)" in src)
    check("G10 静态：文档里写明「正向对照」与「阴性对照」的分工",
          "正向对照" in src and "阴性对照" in src)
    check("G11 静态：默认 rho = 0.8（即 M-T1 是生成模型）",
          "default=0.8" in src)
    check("G12 静态：写文件时钉死 `newline=\"\\n\"`（否则 Windows 上写成 CRLF，"
          "与仓库「裸 LF」的约定冲突）",
          'newline="\\n"' in src)

    print()
    print("=" * 100)
    if FAILS:
        print(f"  {len(FAILS)} 项未通过：" + "、".join(FAILS))
        return 1
    print(f"  全部 {N_OK} 项通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
