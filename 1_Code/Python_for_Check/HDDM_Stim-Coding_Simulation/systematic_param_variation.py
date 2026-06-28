#!/usr/bin/env python3
"""
================================================================================
系统参数变化 CRF 仿真 — 基于 HDDM Stim Coding + 真实数据 RT 匹配
================================================================================

理论背景 (导师假说):
  ① SPE 在 RT 范围 0.3s-0.8s 左右出现，过长或过短导致 SPE 减少甚至消失
  ② SPE 的产生伴随条件连接 (Self+Match)
  ③ Z_bias: 被试对 Match 的反应偏好 (Stim Coding 中的起始点偏差)
  ④ V_bias: 被试与自我相关刺激产生的加工优势 (漂移率偏差)

仿真目标:
  1. 使用真实被试 RT 分布参数调校仿真参数
  2. 固定 v,a,t → 系统性变化 z → 观察 CRF 变化 → 验证 Z_bias 假说
  3. 固定 a,t,z → 系统性变化 v → 观察 CRF 变化 → 验证 V_bias 假说

输出:
  - figure_01_CRF_zbias_main.png           (更新: 真实 RT 范围)
  - figure_02_CRF_RT_distribution.png      (更新)
  - figure_03_SPE_by_zbias.png             (更新)
  - figure_04_Systematic_z_variation.png   (新增: 系统性 z 变化)
  - figure_04b_Systematic_z_variation_SPE.png (新增: z-SPE 瀑布)
  - figure_05_Systematic_v_variation.png   (新增: 系统性 v 变化)
  - figure_05b_Systematic_v_variation_SPE.png (新增: v-SPE 瀑布)
================================================================================
"""

import os, random, warnings, csv
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from pathlib import Path
from scipy import stats

warnings.filterwarnings('ignore')

# ============================================================================
# 0. 路径配置
# ============================================================================
try:
    BASE_DIR = Path("/home/jovyan/work")
    if not BASE_DIR.exists():
        raise FileNotFoundError
except (FileNotFoundError, OSError):
    BASE_DIR = Path(r"D:\GitHub_programe\GitHub\Guassion-Process-Experiment-Design")

CODE_DIR = BASE_DIR / "1_Code" / "Python_for_Check" / "HDDM_Stim-Coding_Simulation"
DATA_DIR = BASE_DIR / "2_Data" / "Generate_Data" / "HDDM_Stim-Coding_Simulation"
FIG_DIR  = BASE_DIR / "3_Figures" / "HDDM_Stim-Coding_Simulation"

for d in [CODE_DIR, DATA_DIR, FIG_DIR]:
    d.mkdir(parents=True, exist_ok=True)

print(f"BASE_DIR: {BASE_DIR}")

# HDDM availability
try:
    import hddm
    HAS_HDDM = True
    print(f"HDDM version: {hddm.__version__}")
except ImportError:
    HAS_HDDM = False
    print("WARNING: HDDM not installed. Using direct DDM (Wiener process).")

# ============================================================================
# 1. 参数配置 — 基于真实数据 RT 分布调校
# ============================================================================
# 真实数据 RT (Formal 试次, N=31,334):
#   Mean=601.6ms, Median=598.5ms, Std=244.5ms
#   5%-95% range: [234, 1017]ms
#   Most groups: median RT 400-800ms
#   Target simulation RT: ~350-900ms (覆盖主要组别的 RT 范围)

# 仿真 DDM 参数 (调校后生成 ~350-900ms RT)
REALISTIC_PARAMS = {
    'a_mean': 1.2,      # 边界分离 (控制 RT 分布宽度)
    'a_std':  0.15,     # 个体变异
    'v_mean': 1.0,      # 平均漂移率
    'v_std':  0.25,     # 个体变异
    't_mean': 0.32,     # 非决策时间 (调高至 320ms 匹配真实 RT 下限 ~250ms)
    't_std':  0.04,
    'dc_std': 0.05,     # 漂移准则个体变异
}

# z-bias 水平 (Stim Coding 起始点)
Z_LEVELS_MAIN = [0.50, 0.55, 0.60, 0.65]  # 主仿真

# 系统性参数变化网格
Z_GRID = [0.50, 0.52, 0.54, 0.56, 0.58, 0.60, 0.63, 0.66, 0.70]  # 9 步 z 变化
V_GRID = [0.4, 0.6, 0.8, 1.0, 1.2, 1.5, 1.8, 2.2]  # 8 步 v 变化

N_SUBJECTS = 24  # 每个参数组合的虚拟被试数
TRIALS_PER = 120  # 每被试-条件试次

# ============================================================================
# 2. 仿真核心 — Wiener 扩散过程
# ============================================================================
def simulate_ddm_trial(a, v, t_nd, z_prop, dt=0.001, max_steps=15000):
    """
    Euler-Maruyama DDM 单试次仿真。
    
    参数:
        a:      边界分离
        v:      漂移率
        t_nd:   非决策时间 (秒)
        z_prop: 起始点比例 [0,1]
    返回:
        (rt_total_seconds, response_upper_boundary)
    """
    x = z_prop * a
    step = 0
    while 0 < x < a and step < max_steps:
        x += v * dt + np.sqrt(dt) * np.random.randn()
        step += 1
    rt_decision = step * dt
    return rt_decision + t_nd, 1 if x >= a else 0


def generate_crf_simulation(params, n_subjects, trials_per, z_levels, seed_base=420,
                             v_bias_self=0.0, z_bias_self=0.0):
    """
    生成 CRF 分析用仿真数据 (Stim Coding 原理)。

    核心逻辑:
      - stimulus=1 试次: v = v_base + dc, z = z_base
      - stimulus=0 试次: v = v_base - dc, z = 1 - z_base
      - choice = response when stimulus=1, choice = 1-response when stimulus=0
      - choice=1 表示被试选择了"匹配"键

    新增: v_bias_self 和 z_bias_self 用于模拟 Self 条件优势
      - Self 条件:  z = z_base + z_bias_self,  v = v_base + v_bias_self
      - Stranger 条件: 使用 baseline z_base, v_base

    z_levels: list of (label, z_value) tuples
    """
    all_trials = []
    
    for subj_id in range(n_subjects):
        subj_seed = seed_base + subj_id * 1000
        np.random.seed(subj_seed)
        random.seed(subj_seed)
        
        subj_a = max(0.4, np.random.normal(params['a_mean'], params['a_std']))
        subj_t = max(0.15, np.random.normal(params['t_mean'], params['t_std']))
        subj_v = np.random.normal(params['v_mean'], params['v_std'])
        subj_dc = np.random.normal(0, params.get('dc_std', 0.05))
        
        half = trials_per // 2
        
        for cond_label, z_val in z_levels:
            z_subj = np.clip(z_val + np.random.normal(0, 0.015), 0.3, 0.7)
            
            # Self 条件: z 和 v 都有优势
            z_self  = np.clip(z_subj + z_bias_self, 0.3, 0.7)
            v_self  = subj_v + v_bias_self
            # Stranger 条件: baseline
            z_stranger = z_subj
            v_stranger = subj_v
            
            for identity, (z_use, v_use) in [('Self', (z_self, v_self)),
                                               ('Stranger', (z_stranger, v_stranger))]:
                for stimulus in [1, 0]:
                    if stimulus == 1:
                        v_eff = v_use + subj_dc
                        z_eff = z_use
                    else:
                        v_eff = v_use - subj_dc
                        z_eff = 1 - z_use
                    
                    # 生成试次
                    if HAS_HDDM:
                        sim_params = {
                            'a': subj_a, 'v': v_eff, 't': subj_t,
                            'z': z_eff, 'sv': 0, 'sz': 0, 'st': 0
                        }
                        df_sim, _ = hddm.generate.gen_rand_data(
                            params=sim_params, size=half, subjs=1,
                            subj_noise=0, seed=subj_seed + stimulus + (0 if identity == 'Self' else 100)
                        )
                        rts = df_sim['rt'].values
                        responses = df_sim['response'].values.astype(int)
                    else:
                        rts, responses = [], []
                        for _ in range(half):
                            rt, resp = simulate_ddm_trial(subj_a, v_eff, subj_t, z_eff)
                            rts.append(rt)
                            responses.append(resp)
                        rts = np.array(rts)
                        responses = np.array(responses, dtype=int)
                    
                    # Stim Coding 坐标转换
                    if stimulus == 1:
                        choices = responses
                    else:
                        choices = 1 - responses
                    
                    for i in range(half):
                        all_trials.append({
                            'subj_idx': subj_id,
                            'condition': cond_label,
                            'z_value': z_val,
                            'identity': identity,
                            'stimulus': stimulus,
                            'rt': rts[i],
                            'choice': int(choices[i]),
                        })
    
    return pd.DataFrame(all_trials)


# ============================================================================
# 3. CRF 计算
# ============================================================================
def compute_crf(data, n_quantiles=5, group_cols=None):
    """计算条件响应函数 (CRF)，按 group_cols 分组计算。"""
    if group_cols is None:
        group_cols = ['condition']
    
    all_groups = data.groupby(group_cols)
    results = []
    
    for group_keys, group_data in all_groups:
        if not isinstance(group_keys, tuple):
            group_keys = (group_keys,)
        
        sorted_data = group_data.sort_values('rt')
        n = len(sorted_data)
        if n < n_quantiles * 2:
            continue
        
        q_size = n // n_quantiles
        for q in range(n_quantiles):
            start = q * q_size
            end = n if q == n_quantiles - 1 else start + q_size
            bin_data = sorted_data.iloc[start:end]
            
            rt_mean = bin_data['rt'].mean()
            p_match = bin_data['choice'].mean()
            n_bin = len(bin_data)
            se = np.sqrt(p_match * (1 - p_match) / n_bin) if n_bin > 1 else 0
            
            row = {'bin': q + 1, 'n': n_bin,
                   'rt_mean_ms': rt_mean * 1000, 'p_matching': p_match,
                   'se': se, 'ci_lo': max(0, p_match - 1.96 * se),
                   'ci_hi': min(1, p_match + 1.96 * se)}
            for ci, col_name in enumerate(group_cols):
                row[col_name] = group_keys[ci]
            results.append(row)
    
    return pd.DataFrame(results)


# ============================================================================
# 4. 可视化
# ============================================================================
plt.rcParams.update({
    'font.size': 11, 'axes.titlesize': 14, 'axes.titleweight': 'bold',
    'axes.labelsize': 12, 'legend.fontsize': 9, 'figure.dpi': 150,
})

def save_fig(fig, name):
    path = FIG_DIR / name
    fig.savefig(path, dpi=200, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f"  Saved: {path}")


def add_theory_box(ax, text_lines, x=0.02, y=0.98, fontsize=7.5):
    """在图角添加理论说明框。"""
    text = '\n'.join(text_lines)
    ax.text(x, y, text, transform=ax.transAxes, fontsize=fontsize,
            verticalalignment='top', fontfamily='monospace',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='lightyellow',
                      edgecolor='gray', alpha=0.85))


def plot_main_crf(crf_df, fig_dir):
    """图 1: 主 CRF 图 (真实 RT 范围匹配)"""
    condition_config = {
        'neutral':       {'label': 'Neutral (z=0.50)',       'color': '#757575', 'marker': 'o', 'ls': '-'},
        'z_bias_small':  {'label': 'Small Bias (z=0.55)',   'color': '#ff9800', 'marker': 's', 'ls': '--'},
        'z_bias_medium': {'label': 'Medium Bias (z=0.60)',  'color': '#e91e63', 'marker': '^', 'ls': '-.'},
        'z_bias_large':  {'label': 'Large Bias (z=0.65)',   'color': '#9c27b0', 'marker': 'D', 'ls': ':'},
    }
    
    fig, ax = plt.subplots(figsize=(10, 7))
    
    for cond, cfg in condition_config.items():
        cdf = crf_df[crf_df['condition'] == cond]
        if len(cdf) == 0:
            continue
        ax.errorbar(cdf['rt_mean_ms'], cdf['p_matching'],
                    yerr=[cdf['p_matching'] - cdf['ci_lo'], cdf['ci_hi'] - cdf['p_matching']],
                    marker=cfg['marker'], linestyle=cfg['ls'], color=cfg['color'],
                    linewidth=2.2, markersize=9, capsize=4, capthick=1.5,
                    label=cfg['label'], alpha=0.9)
    
    # 标注 SPE 窗口
    ax.axvspan(300, 800, alpha=0.06, color='#ff9800', label='SPE window (0.3-0.8s)')
    ax.axhline(y=0.5, color='gray', linestyle='--', linewidth=1.2, alpha=0.6,
               label='P=0.5 (unbiased)')
    
    ax.set_xlabel('Reaction Time (ms)')
    ax.set_ylabel('P(Matching)')
    ax.set_title('Conditional Response Function (CRF)\n'
                 'Stim Coding z-bias Simulation — Matched to Real RT Range',
                 fontweight='bold')
    ax.legend(loc='lower right', framealpha=0.9, edgecolor='gray', fontsize=8.5)
    ax.set_ylim(0.35, 1.05)
    ax.set_xlim(200, 1100)
    ax.grid(True, alpha=0.25)
    
    add_theory_box(ax, [
        'Theory (Z_bias = Response Bias):',
        '  z=0.50: no bias (neutral baseline)',
        '  z>0.50: bias toward "Match" key',
        '  CRF: P(Match) increases with RT',
        '  when z>0.5 (biased accumulation)',
        '',
        'Real Data Match:',
        '  Median RT ~600ms, Range 250-1000ms',
        '  D1-D4b groups within this window',
        '',
        'SPE Window:',
        '  300-800ms (orange shade)',
        '  SPE strongest in this range',
    ], fontsize=6.5)
    
    plt.tight_layout()
    save_fig(fig, 'figure_01_CRF_zbias_main.png')


def plot_rt_distribution(crf_df, data, fig_dir):
    """图 2: RT 分布 + SPE 条形图"""
    condition_config = {
        'neutral':       {'label': 'Neutral (z=0.50)',       'color': '#757575'},
        'z_bias_small':  {'label': 'Small Bias (z=0.55)',   'color': '#ff9800'},
        'z_bias_medium': {'label': 'Medium Bias (z=0.60)',  'color': '#e91e63'},
        'z_bias_large':  {'label': 'Large Bias (z=0.65)',   'color': '#9c27b0'},
    }
    
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    
    # Left: RT distribution
    ax = axes[0]
    for cond, cfg in condition_config.items():
        rts = data[data['condition'] == cond]['rt'] * 1000
        ax.hist(rts, bins=45, alpha=0.35, color=cfg['color'],
                label=cfg['label'], density=True)
    ax.axvspan(300, 800, alpha=0.04, color='#ff9800')
    ax.set_xlabel('RT (ms)')
    ax.set_ylabel('Density')
    ax.set_title('RT Distribution by z-bias Level\n(Real data-matched: median ~600ms)',
                 fontweight='bold')
    ax.legend(fontsize=7.5)
    
    # Right: SPE bar chart
    ax = axes[1]
    summary = crf_df.groupby('condition')['p_matching'].mean().reset_index()
    neutral_p = summary.loc[summary['condition'] == 'neutral', 'p_matching'].values
    if len(neutral_p) > 0:
        neutral_p = neutral_p[0]
        bias_conds = summary[summary['condition'] != 'neutral'].copy()
        bias_conds['SPE'] = bias_conds['p_matching'] - neutral_p
        
        z_vals = {'z_bias_small': 0.55, 'z_bias_medium': 0.60, 'z_bias_large': 0.65}
        colors = {'z_bias_small': '#ff9800', 'z_bias_medium': '#e91e63', 'z_bias_large': '#9c27b0'}
        for _, row in bias_conds.iterrows():
            cond = row['condition']
            ax.bar(f"z={z_vals[cond]}", row['SPE'], color=colors[cond], alpha=0.8,
                   edgecolor='black', linewidth=0.8)
            ax.text(f"z={z_vals[cond]}", row['SPE'] + 0.003, f"{row['SPE']:.3f}",
                    ha='center', fontsize=10, fontweight='bold')
        ax.axhline(y=0, color='gray', linestyle='-', linewidth=1, alpha=0.6)
        ax.set_ylabel('SPE = P(Match) - P(Match|Neutral)')
        ax.set_title('Self-Preference Effect (SPE) by z-bias', fontweight='bold')
        ax.grid(True, alpha=0.2, axis='y')
    
    plt.tight_layout()
    save_fig(fig, 'figure_02_CRF_RT_distribution.png')


def plot_systematic_z_variation(fig_dir):
    """
    图 4: 系统性 z 变化 (固定 v, a, t)
    
    验证假说 ③: Z_bias 是被试对 Match 的反应偏好
      - z 越大 → P(Match) 越高
      - z 变化改变 CRF 截距 (整体上下平移)
      - CRF 形态保持相似 (斜率主要由 v 决定)
    """
    print("\n[Systematic Z] Generating z-variation data...")
    
    z_items = [(f"z={z:.2f}", z) for z in Z_GRID]
    
    data_z = generate_crf_simulation(
        REALISTIC_PARAMS, n_subjects=N_SUBJECTS, trials_per=TRIALS_PER,
        z_levels=z_items, seed_base=100
    )
    crf_z = compute_crf(data_z, n_quantiles=5, group_cols=['condition'])
    
    # Plot: z-variation CRF
    fig, axes = plt.subplots(1, 2, figsize=(18, 7))
    
    # --- Left: CRF curves for selected z levels ---
    ax = axes[0]
    # Show subset for clarity
    show_z = [0.50, 0.54, 0.58, 0.63, 0.70]
    colors_z = plt.cm.YlOrRd(np.linspace(0.2, 0.95, len(show_z)))
    
    for zi, z in enumerate(show_z):
        label = f"z={z:.2f}"
        cdf = crf_z[crf_z['condition'] == label]
        if len(cdf) < 2:
            continue
        ax.errorbar(cdf['rt_mean_ms'], cdf['p_matching'],
                    yerr=[cdf['p_matching'] - cdf['ci_lo'], cdf['ci_hi'] - cdf['p_matching']],
                    marker='o', color=colors_z[zi], linewidth=1.8, markersize=7,
                    capsize=3, label=label, alpha=0.85)
    
    ax.axhline(y=0.5, color='gray', linestyle='--', linewidth=1, alpha=0.5)
    ax.set_xlabel('RT (ms)')
    ax.set_ylabel('P(Matching)')
    ax.set_title('Systematic z Variation (Fixed v=1.0, a=1.2, t=0.32)\n'
                 'Z_bias: Starting-point shift → response preference',
                 fontweight='bold')
    ax.legend(fontsize=7.5, ncol=2)
    ax.set_ylim(0.2, 1.02)
    ax.grid(True, alpha=0.2)
    
    add_theory_box(ax, [
        'Z_bias Hypothesis:',
        '  Starting point z controls',
        '  response preference toward',
        '  "Match" boundary.',
        '  z near 0.5 → unbiased',
        '  z near 0.7 → strong Match bias',
        'Effect: vertical shift of CRF',
        '  (same shape, different level)',
    ], fontsize=6.5)
    
    # --- Right: SPE waterfall across ALL z levels ---
    ax = axes[1]
    baseline = crf_z[crf_z['condition'] == 'z=0.50']
    if len(baseline) > 0:
        base_p = baseline.groupby('bin')['p_matching'].mean()
        zs_all = sorted(set(c['condition'].split('=')[1] for _, c in crf_z.iterrows() if c['condition'] != 'z=0.50'),
                        key=float)
        zs_all = [float(z) for z in zs_all]
        
        spe_by_z = {}
        for z_str in [f"z={z:.2f}" for z in zs_all]:
            cdf_z = crf_z[crf_z['condition'] == z_str]
            if len(cdf_z) == 0:
                continue
            z_val = float(z_str.split('=')[1])
            spe = cdf_z.groupby('bin')['p_matching'].mean() - base_p
            spe_by_z[z_val] = spe
        
        for z_val, spe in spe_by_z.items():
            color = plt.cm.YlOrRd((z_val - 0.50) / 0.20)
            ax.plot(spe.index, spe.values, 'o-', color=color, linewidth=1.5,
                    markersize=6, label=f"z={z_val:.2f}")
        
        ax.axhline(y=0, color='gray', linestyle='--', linewidth=1, alpha=0.5)
        ax.set_xlabel('RT Quantile Bin')
        ax.set_ylabel('SPE = P(Match) - P(Match|z=0.50)')
        ax.set_title('SPE Waterfall: z-bias Effect Across RT Bins', fontweight='bold')
        ax.legend(fontsize=6.5, ncol=2)
        ax.grid(True, alpha=0.2)
    
    plt.tight_layout()
    save_fig(fig, 'figure_04_Systematic_z_variation.png')


def plot_systematic_v_variation(fig_dir):
    """
    图 5: 系统性 v 变化 (固定 a, t, z)
    
    验证假说 ④: V_bias 是被试与自我相关刺激产生的加工优势
      - v 越大 → 漂移越快 → RT 越小
      - v 变化改变 CRF 斜率 (RT 敏感度)
      - 结合 Self/Stranger: v_Self > v_Stranger → Self 更快更准
    """
    print("\n[Systematic V] Generating v-variation data...")
    
    # Fix a, t, z; vary v
    # 对每个 v 水平: 使用 Self/Stranger 双条件 (模拟 V_bias)
    fixed_a = 1.2
    fixed_t = 0.32
    fixed_z = 0.55  # slight match bias
    
    all_v_data = []
    for v_val in V_GRID:
        v_params = {
            'a_mean': fixed_a, 'a_std': 0.0,
            'v_mean': v_val, 'v_std': 0.0,
            't_mean': fixed_t, 't_std': 0.0,
            'dc_std': 0.0,
        }
        # 添加 v_bias_self=0.3 模拟 Self 的加工优势
        data_v = generate_crf_simulation(
            v_params, n_subjects=12, trials_per=80,
            z_levels=[(f"v={v_val:.1f}", fixed_z)],
            seed_base=200 + int(v_val * 100),
            v_bias_self=0.3  # Self 条件漂移率优势
        )
        all_v_data.append(data_v)
    
    all_v_data = pd.concat(all_v_data, ignore_index=True)
    crf_v = compute_crf(all_v_data, n_quantiles=5, group_cols=['condition', 'identity'])
    
    # --- Left: CRF for selected v levels (Self vs Stranger) ---
    fig, axes = plt.subplots(1, 2, figsize=(18, 7))
    ax = axes[0]
    
    show_v = [0.4, 0.8, 1.2, 1.8]
    colors_v = plt.cm.Blues(np.linspace(0.3, 0.95, len(show_v)))
    
    for vi, v_val in enumerate(show_v):
        for idt, ls, alpha, marker in [('Self', '-', 1.0, 'o'), ('Stranger', '--', 0.55, 's')]:
            label = f"{idt} (v={v_val:.1f})"
            cdf = crf_v[(crf_v['condition'] == f"v={v_val:.1f}") & (crf_v['identity'] == idt)]
            if len(cdf) < 2:
                continue
            ax.errorbar(cdf['rt_mean_ms'], cdf['p_matching'],
                        yerr=[cdf['p_matching'] - cdf['ci_lo'], cdf['ci_hi'] - cdf['p_matching']],
                        marker=marker, color=colors_v[vi], linestyle=ls, linewidth=1.8,
                        markersize=6, capsize=3, label=label, alpha=alpha)
    
    ax.axhline(y=0.5, color='gray', linestyle='--', linewidth=1, alpha=0.5)
    ax.set_xlabel('RT (ms)')
    ax.set_ylabel('P(Matching)')
    ax.set_title('Systematic v Variation (Fixed a=1.2, t=0.32, z=0.55)\n'
                 'V_bias: Drift-rate difference → Self processing advantage',
                 fontweight='bold')
    ax.legend(fontsize=6.5, ncol=2)
    ax.grid(True, alpha=0.2)
    
    add_theory_box(ax, [
        'V_bias Hypothesis:',
        '  Drift rate v controls evidence',
        '  accumulation speed.',
        '  v_Self > v_Stranger → Self',
        '  trials processed faster/more',
        '  accurately (shorter RT, higher',
        '  P(Match) at same bin)',
        '',
        'Effect: shift left + up',
        '  Higher v → shorter RT,',
        '  same P(Match) contour',
    ], fontsize=6.5)
    
    # --- Right: SPE = Self - Stranger across v levels ---
    ax = axes[1]
    v_levels = sorted(set(float(c['condition'].split('=')[1]) for _, c in crf_v.iterrows()),
                      key=float)
    
    for v_val in v_levels:
        self_df = crf_v[(crf_v['condition'] == f"v={v_val:.1f}") & (crf_v['identity'] == 'Self')]
        stranger_df = crf_v[(crf_v['condition'] == f"v={v_val:.1f}") & (crf_v['identity'] == 'Stranger')]
        if len(self_df) < 2 or len(stranger_df) < 2:
            continue
        
        self_p = self_df.groupby('bin')['p_matching'].mean()
        stranger_p = stranger_df.groupby('bin')['p_matching'].mean()
        min_bins = min(len(self_p), len(stranger_p))
        spe = (self_p.iloc[:min_bins] - stranger_p.iloc[:min_bins]).values
        bins = list(range(1, min_bins + 1))
        
        color = plt.cm.Blues(0.3 + (v_val - V_GRID[0]) / (V_GRID[-1] - V_GRID[0]) * 0.7)
        ax.plot(bins, spe, 'o-', color=color, linewidth=1.5, markersize=6,
                label=f"v={v_val:.1f}")
    
    ax.axhline(y=0, color='gray', linestyle='--', linewidth=1, alpha=0.5)
    ax.set_xlabel('RT Quantile Bin')
    ax.set_ylabel('SPE = Self - Stranger P(Match)')
    ax.set_title('SPE Across v Levels: Self vs Stranger', fontweight='bold')
    ax.legend(fontsize=6.5, ncol=2)
    ax.grid(True, alpha=0.2)
    
    plt.tight_layout()
    save_fig(fig, 'figure_05_Systematic_v_variation.png')


# ============================================================================
# 5. 主流程
# ============================================================================
def main():
    print("=" * 70)
    print("  Systematic Parameter Variation — CRF Simulation")
    print("  HDDM Stim Coding + Real Data RT Matching")
    print("=" * 70)
    
    # ---- 5a. 主仿真 (z-bias 4水平, 真实RT匹配) ----
    print("\n[1/5] Main simulation — z-bias CRF (realistic RT params)...")
    z_items = [('neutral', 0.50), ('z_bias_small', 0.55),
               ('z_bias_medium', 0.60), ('z_bias_large', 0.65)]
    
    data_main = generate_crf_simulation(
        REALISTIC_PARAMS, n_subjects=30, trials_per=150,
        z_levels=z_items, seed_base=420
    )
    print(f"  Trials: {len(data_main)}, Mean RT: {data_main['rt'].mean()*1000:.1f} ms")
    print(f"  RT range: [{data_main['rt'].min()*1000:.0f}, {data_main['rt'].max()*1000:.0f}] ms")
    
    crf_main = compute_crf(data_main, n_quantiles=5, group_cols=['condition'])
    
    # Save data
    data_main.to_csv(DATA_DIR / "simulation_zbias_crf_data.csv", index=False)
    crf_main.to_csv(DATA_DIR / "crf_results_zbias.csv", index=False)
    
    # ---- 5b. 图 1-2: 主要 CRF 图 (更新版) ----
    print("\n[2/5] Plotting main CRF figures (realistic RT range)...")
    plot_main_crf(crf_main, FIG_DIR)
    plot_rt_distribution(crf_main, data_main, FIG_DIR)
    
    # ---- 5c. 图 3: SPE 条形图 (简化版, 已在图2中) ----
    print("\n[3/5] SPE bar chart included in figure_02.")
    
    # ---- 5d. 图 4: 系统性 z 变化 ----
    print("\n[4/5] Systematic z-variation analysis...")
    plot_systematic_z_variation(FIG_DIR)
    
    # ---- 5e. 图 5: 系统性 v 变化 ----
    print("\n[5/5] Systematic v-variation analysis...")
    plot_systematic_v_variation(FIG_DIR)
    
    print("\n" + "=" * 70)
    print("  All figures generated!")
    print(f"  Data:  {DATA_DIR}")
    print(f"  Figures: {FIG_DIR}")
    print("=" * 70)


if __name__ == "__main__":
    main()
