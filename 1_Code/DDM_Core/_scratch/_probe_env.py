"""环境探针：Stage 8 需要的贝叶斯/诊断库是否存在。"""
import importlib
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
print("python", sys.version.split()[0])

MODS = ["numpy", "scipy", "pandas", "matplotlib", "pymc", "numpyro", "jax",
        "arviz", "cmdstanpy", "emcee", "torch", "sklearn", "hddm", "ssm"]
for m in MODS:
    try:
        mod = importlib.import_module(m)
        ver = getattr(mod, "__version__", "?")
        print("%-12s OK   %s" % (m, ver))
    except Exception as exc:
        print("%-12s --   %s" % (m, type(exc).__name__))
