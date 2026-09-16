# Optimizing the Experimental Design Space of the Self-Prioritization Effect

**Predicting and validating drift-diffusion model parameters with Gaussian process surrogates**

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue)](https://www.python.org/)
[![R](https://img.shields.io/badge/R-cross--validation-276DC3)](https://www.r-project.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

This repository contains the analysis pipeline for my master's thesis. It builds a **generative
framework that maps continuous experimental design variables onto drift-diffusion model (DDM)
parameters and then onto trial-level behaviour**, moving beyond the conventional practice of
comparing a handful of discrete experimental conditions.

---

## Overview

Most studies of the self-prioritization effect (SPE) compare a small number of experimenter-chosen
conditions — for example, one practice level and one stimulus duration. This design strategy is
inefficient: it leaves the shape of the relationship between design variables and psychological
parameters unknown, and it cannot tell you *which* design would most sensitively detect an effect.

This project treats the experimental design as a **continuous space** rather than a set of discrete
conditions, and asks three questions:

1. How do design variables jointly shape DDM parameters and, through them, observable behaviour?
2. Can a **Gaussian process surrogate** predict DDM parameters and effect size across regions of the
   design space that were never run?
3. Which design regions maximize the sensitivity of the self-prioritization effect — and are those
   predictions recoverable from simulated data?

### Design space

The design space is parameterized by four variables:

| Symbol | Variable | Role |
|---|---|---|
| **P** | Practice trials | Number of pre-experiment practice trials per identity |
| **T** | Stimulus presentation duration | How long the shape–label pair is displayed (ms) |
| **W** | Response window | Deadline for a response (ms) |
| **M** | Matching condition | Matching vs. non-matching; also used as the condition key for parameter mapping |

Grid values used in the standard configuration:
`P = [0, 32, 64, 120]` · `T = [30, 100, 200, 500]` · `W = [300, 600, 1000, 1500]`

---

## Methods

### Generative pipeline

```
Design space Ω = (P, T, W, M)
        │
        ▼
Sigmoid S2 mechanism      theoretical prior on how design variables map to (v, a)
        │
        ▼
Gaussian process residual correction
        │
        ▼
DDM simulation (Euler integration, deadline, omissions)
        │
        ▼
Trial-level behaviour (RT, response, accuracy, omission)
```

### Estimation and validation

- **Hierarchical Bayesian DDM fitting** with [HDDM](https://github.com/hddm-devs/hddm) via
  **dockerHDDM**, across 8 design configurations of real self-matching data.
- **Model comparison** using DIC, plus **posterior predictive checks**.
- **Prior-sensitivity checks** with 4 MCMC chains.
- **Parameter recovery**: simulated data with known ground-truth parameters are refitted to quantify
  how well each parameter is identifiable at a given design.
- **Omission sensitivity analysis**: two alternative treatments of omitted trials — censoring vs.
  dropping — compared head to head.
- **Bias parameterization comparison**: stimulus bias, response bias, and combined bias, to test how
  the choice of coding scheme shifts parameter estimates.
- **Independent cross-validation in R** (`1_Code/R_for_Check/`) as a check on the Python pipeline.

### Why Gaussian processes rather than a fixed parametric form

1. **Nonlinear mapping** — learns the relation `(P, T, W) → DDM parameters` without committing to a
   functional form.
2. **Uncertainty quantification** — returns a predictive variance alongside the mean, which
   identifies where the surrogate is reliable and where it is not.
3. **Boundary exploration** — supports asking where the effect is largest, and where the surrogate
   is most uncertain (and therefore where the next experiment is most informative).
4. **Extensibility** — accommodates additional parameters, conditions, and individual differences
   more naturally than a fixed sigmoid.

---

## Repository structure

```
.
├── 1_Code/
│   ├── Experiment/          # MATLAB/Psychtoolbox task implementation (exp_matlab/)
│   ├── Python_for_Generate/ # Design-space generation and data simulation (v1 → v3, v2.4.x mainline)
│   ├── Python_for_Check/    # Verification: parameter recovery, model comparison, PPC,
│   │                        #   omission sensitivity, bias coding, GP visualization
│   ├── Python_HDDM/         # Hierarchical Bayesian DDM fitting (dockerHDDM)
│   ├── Python_HDDM_Nonmatching/
│   └── R_for_Check/         # Independent R cross-validation
├── 2_Data/
│   ├── Generate_Data/       # Simulated datasets per model version
│   └── Real_Data/           # Behavioural data from the SPE database, HDDM-ready
├── 3_Figures/               # Output figures, including standardized GP visualization
├── 4_Reports/               # Slides, reports, references
├── 5_Reference/             # Thesis drafts, outlines, specification documents
└── automation/              # One-command reproducible pipeline (see automation/README.md)
```

### Version lineage

| Version family | Role |
|---|---|
| `v1` | Baseline: Sigmoid + DDM generative framework |
| `v2.1 – v2.3` | Transitional: parameter mapping and generation refined |
| **`v2.4 – v2.4.5`** | **Stable mainline**: generation, checks, recovery, real-data comparison |
| `v2.5` | Exploratory: extended GP-DDM parameterization |
| `v3` | Research branch: GP residual and boundary structure |
| `S2_gen_data_optimized_cp*` | Parallel optimization branch (Sigmoid) for comparison |

---

## Quickstart

The `automation/` package runs the whole pipeline end to end and writes a report.

```bash
cd automation
pip install -r requirements.txt

python cli.py --profile quick        # smoke test (~30 s)
python cli.py --profile standard     # ~2 min
python cli.py --profile research     # ~8 min, full report
```

| Profile | Design space | Subjects | Trials/condition | Rounds | Runtime |
|---|---|---|---|---|---|
| `quick` | 3×3×3 = 27 | 8 | 8 | 2 | ~30 s |
| `standard` | 8×8×8 = 512 | 30 | 20 | 5 | ~2 min |
| `research` | 14×13×9 = 1638 | 50 | 30 | 10 | ~8 min |

Outputs (JSON + Markdown report, design grids, simulated behaviour, model comparison, effect-size
analysis, run log) are written to `automation/logs/{run_id}/`.

### Programmatic use

```python
import sys; sys.path.insert(0, '.')
from automation.pipeline import ExperimentPipeline

pipeline = ExperimentPipeline(config={
    'experiment': {'n_subjects': 30, 'trials_per_condition': 20},
    'iteration':  {'n_rounds': 5},
})
results = pipeline.run()
print(results['effect_analysis']['synthetic_SPE']['SPE_ms_mean'])
```

See [`automation/README.md`](automation/README.md) for module-level documentation, configuration
options, and a FAQ.

---

## Environment

| Package | Minimum | Purpose |
|---|---|---|
| Python | 3.9+ (3.11+ recommended) | core pipeline |
| numpy | 1.20+ | numerical computation |
| pandas | 1.3+ | data handling |
| scikit-learn | 1.0+ | Gaussian process models |
| scipy | 1.7+ | statistical tests |
| matplotlib | 3.4+ | figures |

DDM fitting additionally requires **HDDM** and a Docker environment for **dockerHDDM**
(`Dockerfile.hssm` is included).

---

## Data

- **Real data** (`2_Data/Real_Data/`) is derived from the **Self-Prioritization Effect Database**, an
  open, standardized trial-level database of the self-matching task; the HDDM-ready subsets used here
  cover 8 design configurations. Source studies are cited in the thesis.
- **Simulated data** (`2_Data/Generate_Data/`) is reproducible from the scripts with fixed random
  seeds; each `*_checks` directory marks a version that has passed systematic validation.

## How to cite

```bibtex
@mastersthesis{cai2026designspace,
  author  = {Cai, Zhenxin},
  title   = {Optimizing the Experimental Design Space of the Self-Prioritization Effect:
             Predicting and Validating DDM Parameters via Gaussian Process Surrogates},
  school  = {Nanjing Normal University},
  year    = {2026},
  type    = {Master's thesis}
}
```

## Contact

Zhenxin Cai — Nanjing Normal University, School of Psychology
GitHub: [@Caizhenxin](https://github.com/Caizhenxin)

## Acknowledgements

Advisor: Prof. Chuan-Peng Hu (Hu Lab, Nanjing Normal University). The self-matching paradigm
originates with Sui, He & Humphreys (2012); this work builds directly on that paradigm and on the
open data shared by the self-prioritization research community.

## References

- Sui, J., He, X., & Humphreys, G. W. (2012). Perceptual effects of social salience: Evidence from
  self-prioritization effects on perceptual matching. *Journal of Experimental Psychology: Human
  Perception and Performance*, 38(5), 1105–1117.
- Ratcliff, R., & McKoon, G. (2008). The diffusion decision model: Theory and data for two-choice
  decision tasks. *Neural Computation*, 20(4), 873–922.
- Wiecki, T. V., Sofer, I., & Frank, M. J. (2013). HDDM: Hierarchical Bayesian estimation of the
  drift-diffusion model in Python. *Frontiers in Neuroinformatics*, 7, 14.
- Wilkinson, M. D., et al. (2016). The FAIR Guiding Principles for scientific data management and
  stewardship. *Scientific Data*, 3, 160018.

---

## License

MIT — see [`LICENSE`](LICENSE).
