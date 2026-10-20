# -*- coding: utf-8 -*-
"""修两处：
1. offpeak_gate.py —— 15 分钟网格对齐 + 中文星期；
2. design_search.py —— P=0 的漂移簇 CRLB 是「pinv 退化出的精确 0」，必须当
   「无信息水平」剔除，而不是当成「完美精度」，更不该把整个设计判死。
"""
from pathlib import Path

# ---------------------------------------------------------------- 1. gate
g = Path(r"C:\Users\蔡振辛\AppData\Roaming\dsh-desktop\harness\offpeak_gate.py")
s = g.read_text(encoding="utf-8")
s = s.replace(
    "PEAK_WINDOWS = [(dtime(9, 0), dtime(12, 0)), (dtime(14, 0), dtime(18, 0))]",
    "PEAK_WINDOWS = [(dtime(9, 0), dtime(12, 0)), (dtime(14, 0), dtime(18, 0))]\n"
    "ZH_DAYS = [\"周一\", \"周二\", \"周三\", \"周四\", \"周五\", \"周六\", \"周日\"]")
old = "    cur = now.replace(second=0, microsecond=0)\n    for _ in range(limit_days * 24 * 4):"
new = ("    cur = now.replace(second=0, microsecond=0)\n"
       "    cur += timedelta(minutes=(-cur.minute) % 15)     # 对齐到 15 分钟网格\n"
       "    for _ in range(limit_days * 24 * 4):")
assert s.count(old) == 2, s.count(old)
s = s.replace(old, new)
s = s.replace('now.strftime("%A")', "ZH_DAYS[now.weekday()]")
g.write_text(s, encoding="utf-8", newline="\n")
print("gate patched")

# ------------------------------------------------ 2. design_search 的 keep 逻辑
d = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\1_Code\Experiment\design_search.py")
t = d.read_text(encoding="utf-8")
old_keep = """            n_bp = n_tp = None
            if (se_ds > SE_D_UNUSABLE).all() or (se_ds <= 0).any():
                unusable = True
            else:
                # 低 P 水平的漂移 SE 大到 SE_D_UNUSABLE 时，只保留可用水平
                keep = se_ds < SE_D_UNUSABLE
                if keep.sum() < 3:
                    unusable = True
                else:"""
new_keep = """            n_bp = n_tp = None
            # P=0 组的漂移≈0 ⇒ 漂移簇信息矩阵近奇异 ⇒ pinv 给出的 SE 恰好为 0，
            # 这是「无信息」而不是「完美精度」；SE 过大（>1.0）同样是不可用水平。
            keep = np.isfinite(se_ds) & (se_ds > 1e-9) & (se_ds < SE_D_UNUSABLE)
            if keep.sum() < 3:
                unusable = True
            else:
                if True:"""
assert t.count(old_keep) == 1
t = t.replace(old_keep, new_keep)
# 记录真正参与估计的水平数
t = t.replace('"n_P_levels": len(levels),', '"n_P_levels": int(keep.sum()) if not unusable else 0,')
t = t.replace('"n_P_levels": len(levels),\n                "trials_per_subject"',
              '"n_P_levels": int(keep.sum()) if not unusable else 0,\n                "trials_per_subject"')
d.write_text(t, encoding="utf-8", newline="\n")
print("design_search patched")
