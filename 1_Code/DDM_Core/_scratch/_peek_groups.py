"""从已落盘的组缓存里抽「模型小结」几行（只打印选定的行，不 dump 大对象）。"""
import json
import pathlib

D = pathlib.Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design"
                 r"\2_Data\Real_Data\New_Design\_pipeline\stage8_d123")
KEYS = ("**M-T", "ΔELPD", "n_flipped", "判定", "对照", "包络")

for p in sorted(D.glob("stage8_group_*.json")):
    o = json.loads(p.read_text(encoding="utf-8"))
    print(f"\n===== {p.name}（组 {o['tag']}）=====")
    for r in o["results"].values():
        lk = r["loo"]
        hyp = r.get("hyper") or {}
        print(f"  ELPD {lk['elpd_loo']:.1f} ± {lk['se']:.1f}  p_loo {lk['p_loo']:.1f}"
              f"（{lk['p_loo'] / lk['n_obs']:.4f}/obs）  n_obs {lk['n_obs']}"
              f"  k_max {lk['k_max']:.2f}  越界 {lk['n_k_gt_bad']}"
              f"  n_flipped {r.get('hyper', {}).get('n_flipped', '?')}"
              f"  {r['seconds'] / 60:.0f} min")
    for ln in o["lines"]:
        if any(k in ln for k in KEYS):
            print("   |", ln.strip()[:150])
