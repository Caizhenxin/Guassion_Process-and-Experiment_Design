import json, sys
from pathlib import Path
sys.path.insert(0, r"1_Code/Tools")
import jobstatus
f = jobstatus.job_dir("stage8_d123") / "status.json"
d = json.loads(f.read_text(encoding="utf-8"))
d.update({"state": "done", "step": "4 组 × 2 模型全部落盘（stage8_results.json）",
          "done": 8, "total": 8, "eta_seconds": 0})
f.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
print("marked done:", d["state"], d["done"], d["total"])
