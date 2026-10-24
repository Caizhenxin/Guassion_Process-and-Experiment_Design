from pathlib import Path

p = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design\1_Code\Experiment\intake.py")
s = p.read_text(encoding="utf-8")

# ---------- 1) 在 main() 之前插入 screen() ----------
anchor = "def main(argv: list[str] | None = None) -> int:"
assert s.count(anchor) == 1

screen_fn = '''def screen(sessions: list[dict], expect_n: int = 40) -> dict:
    """跑完整五层（技术/结构/一致/质量/统计），返回逐场裁决 + 质量表 + 统计层。

    `main()` 与 `run_pipeline.py` 的第 1 步都调这一个函数——判据只有一份，
    不要在别处另写一遍裁决逻辑（D120）。
    """
    res, qmap, frames = [], {}, []
    for x in sessions:
        r = audit_one(x["gid"], x["sid"], x["csv"], x["txt"], x["shadowed"])
        if r["csv"] is not None:
            df = R.load_files([r["csv"]])
            gid = pd.to_numeric(df["groupID"], errors="coerce").fillna(-1).astype(int)
            sid = pd.to_numeric(df["subjectID"], errors="coerce").fillna(-1).astype(int)
            df = df[(gid == r["gid"]) & (sid == r["sid"])]
            if len(df):
                q = quality_one(df)
                frames.append(df)
            else:
                q = {"metrics": {}, "hard": [f"CSV 里找不到组 {r['gid']} 被试 {r['sid']} 的行"],
                     "notes": []}
            r["hard"] += q["hard"]
            r["notes"] += q["notes"]
            r["verdict"] = EXCLUDE if r["hard"] else (REVIEW if r["soft"] else KEEP)
            qmap[(r["gid"], r["sid"])] = q
        res.append(r)

    st = None
    if frames:
        keep_ids = {f"{r['gid']}-{r['sid']}" for r in res if r["verdict"] != EXCLUDE}
        st = stats_layer(pd.concat(frames, ignore_index=True), keep_ids, expect_n)
    return {"res": res, "qmap": qmap, "stats": st}


'''

s = s.replace(anchor, screen_fn + anchor)

# ---------- 2) main() 里的内联循环改成调 screen() ----------
old_loop = '''    res, qmap, frames = [], {}, []
    for x in sessions:
        r = audit_one(x["gid"], x["sid"], x["csv"], x["txt"], x["shadowed"])
        if r["csv"] is not None:
            df = R.load_files([r["csv"]])
            gid = pd.to_numeric(df["groupID"], errors="coerce").fillna(-1).astype(int)
            sid = pd.to_numeric(df["subjectID"], errors="coerce").fillna(-1).astype(int)
            df = df[(gid == r["gid"]) & (sid == r["sid"])]
            if len(df):
                q = quality_one(df)
                frames.append(df)
            else:
                q = {"metrics": {}, "hard": [f"CSV 里找不到组 {r['gid']} 被试 {r['sid']} 的行"], "notes": []}
            r["hard"] += q["hard"]
            r["notes"] += q["notes"]
            r["verdict"] = EXCLUDE if r["hard"] else (REVIEW if r["soft"] else KEEP)
            qmap[(r["gid"], r["sid"])] = q
        res.append(r)

    print(render(res))

    st = None
    if frames:
        keep_ids = {f"{r['gid']}-{r['sid']}" for r in res if r["verdict"] != EXCLUDE}
        st = stats_layer(pd.concat(frames, ignore_index=True), keep_ids, args.expect_n)
        ov = st["stats"]["overall"]
'''
assert s.count(old_loop) == 1, s.count(old_loop)

new_loop = '''    sc = screen(sessions, args.expect_n)
    res, qmap, st = sc["res"], sc["qmap"], sc["stats"]

    print(render(res))

    if st is not None:
        ov = st["stats"]["overall"]
'''
s = s.replace(old_loop, new_loop)

p.write_text(s, encoding="utf-8", newline="\n")
print("[ok] screen() 已抽出")
