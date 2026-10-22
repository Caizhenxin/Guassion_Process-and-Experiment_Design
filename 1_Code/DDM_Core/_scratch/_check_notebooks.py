"""检查三个 notebook 的执行结果：错误数、自检结果、产物行数。"""
import glob
import json
from pathlib import Path

PAT = str(Path(__file__).resolve().parents[2] / "Python_for_Generate" / "M-T*.ipynb")

for f in sorted(glob.glob(PAT)):
    nb = json.load(open(f, encoding="utf-8"))
    outs, errs, texts = 0, 0, []
    for c in nb["cells"]:
        if c["cell_type"] != "code":
            continue
        for o in c.get("outputs", []):
            outs += 1
            if o.get("output_type") == "error":
                errs += 1
                texts.append("ERROR " + o.get("ename", "?"))
            if o.get("output_type") == "stream":
                t = o["text"]
                texts.append("".join(t) if isinstance(t, list) else t)
    body = "\n".join(texts)
    print(f"=== {Path(f).name}")
    print(f"    cells={len(nb['cells'])} outputs={outs} errors={errs}")
    for line in body.splitlines():
        s = line.strip()
        if s.startswith(("✅", "❌")) or s.startswith("全部通过") or "有项目未通过" in s:
            print("   ", s)
    heads = [s for s in body.splitlines() if s.strip().startswith(("trials_long", "figures"))][:2]
    print("    产物行:", " | ".join(h.strip() for h in heads))
