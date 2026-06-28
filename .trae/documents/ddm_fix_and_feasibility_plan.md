# DDM 可视化修复 + 逆向推断可行性分析 — 综合计划

## 探索发现摘要

使用相同参数 (v=1.0, a=1.2, t=0.3, z=0.5)，`visualization_app.html` 的 DDM 标签页与 `plot_CRF_zbias.ipynb` 产生不同结果，根因有三：

### 根因 1: z 参数语义不一致（最严重 Bug）
| 代码 | z 解释 | z=0.5, a=1.2 时实际起点 |
|------|--------|-------------------------|
| Notebook 系列 (`plot_CRF_zbias.ipynb` 等) | **比例** `x = z * a` | `0.5 × 1.2 = 0.6` |
| `app_server.py` / `ddm_engine.py` | **绝对值** `x = float(z)` | `0.5` |

两者产生完全不同的起始位置，导致 CRF 曲线、RT 分布、ACC 全部不同。

### 根因 2: 参数默认值差异
| 参数 | app_server.py 默认 | notebook 默认 |
|------|:---:|:---:|
| `t0` (非决策时间) | **0.20 s** | **0.30 s** (0.32 in systematic) |
| `v` (漂移率) | 1.5 | 1.0 |
| `a` (决策边界) | 1.5 | 1.2 |
| 被试间噪声 | 无 | a_std=0.2, v_std=0.3, t_std=0.05 |

### 根因 3: 仿真方法差异（次要）
- Notebook 使用 `hddm.generate.gen_rand_data()` (Wald 解析解，精确) 或 Euler-Maruyama (dt=0.001)
- `app_server.py` 使用 Euler-Maruyama (dt=0.001，存在离散化偏差约 +14ms RT)

### z 参数取值范围说明
根据 `RoadMap.md` 和 DDM 文献：
- **z 的绝对值**（HDDM 后验输出）范围: `0 ~ a`，典型值为 a/2 附近（无偏）或略偏上下
- **zr = z/a（相对起点）**: `0 ~ 1`，0.5 为无偏，>0.5 偏向上界，<0.5 偏向下界
- Notebook 中 z 作为比例（0~1），`x = z * a` 计算绝对起点
- `app_server.py` 中 z 作为绝对值，范围应为 `0 ~ a`，当前滑块 `0.1~3.0` 基本合理（a 最大 4.0）
- **z 可以 >1** 因为 a 可以 >1（如 a=2.01 时 z=0.75 是正常的绝对起点值）

---

## 计划

### Part A: 修复 app_server.py DDM 仿真（使与 notebook 一致）

**文件**: `1_Code/Python_for_Check/Visualization/app_server.py`

#### A1. 修复 z 参数语义 — 改为比例（与 notebook 对齐）
将 `simulate_ddm_euler()` 中的 `x = float(z)` 改为 `x = z * a`，使 z 表示比例 (0~1)。

```python
# 修改前
def simulate_ddm_euler(v, a, z, t0, dt=0.001, max_time_s=3.0):
    x = float(z)

# 修改后
def simulate_ddm_euler(v, a, z, t0, dt=0.001, max_time_s=3.0):
    x = z * a   # z 现在是 0~1 的比例
```

#### A2. 同步参数默认值为 notebook 标准值
```python
# do_POST /api/ddm/generate 中的默认值
v:  1.5  → 1.0      # 对齐 notebook v_mean
a:  1.5  → 1.2      # 对齐 notebook a_mean  
z:  0.75 → 0.5      # 对齐 notebook 中性比例
t0: 0.2  → 0.3      # 对齐 notebook t_mean
```

#### A3. 增加 max_time_s 从 3.0 到 10.0
防止慢条件（高 a、低 v）仿真被截断。

### Part B: 修复 visualization_app.html 前端参数默认值

**文件**: `1_Code/Python_for_Check/Visualization/visualization_app.html`

#### B1. 更新滑块默认值（与 notebook 对齐）
```javascript
// renderDDMTab() 中的默认值
ddm-v-self:  value="2.0" → value="1.0"
ddm-a-self:  value="1.5" → value="1.2"
ddm-z-self:  value="0.75" → value="0.5"
ddm-t-self:  value="0.2"  → value="0.30"
```

#### B2. 更新 z 滑块范围（改为比例 0~1）
```javascript
ddm-z-self: min="0.1" max="3" → min="0.05" max="0.95" step="0.05"
ddm-z-stranger: 同上
```

#### B3. 更新 z 标签说明
```html
<!-- 修改前 --> 起点 (starting point)
<!-- 修改后 --> 起点比例 z/a (0~1, 0.5=无偏)
```

#### B4. 更新 v/a/t 滑块范围以匹配文献
```javascript
ddm-v-self: min="0.1" max="5" → min="0.1" max="4" 
ddm-a-self: min="0.5" max="4" → min="0.3" max="3"
```

#### B5. 更新参数扫描默认范围
```javascript
ddm-sweep-min: 0.5 → 依扫描维度变化
ddm-sweep-max: 3.0 → 依扫描维度变化
```

### Part C: 创建可行性分析文档

**文件**: `1_Code/Python_for_Check/Visualization/DDM_Parameter_Explore/DDM_CRF_逆向推断可行性分析.md`

分析内容：
1. 问题定义（正向 vs 逆向）
2. 理论可行性（参数可辨识性分析）
3. 三种可行方法对比：
   - 方法 A: EZ-Diffusion（闭合解，3参数）
   - 方法 B: HDDM MCMC（金标准，4参数）
   - 方法 C: CRF 匹配优化（用户创新方法）
4. 方法 C 推荐实现路径
5. 潜在风险与局限
6. 参考文献（Wagenmakers 2007, Wiecki 2013, Ratcliff 2008, Turner & Sederberg 2014 等）
7. 结论与建议

---

## 文件修改清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `app_server.py` | 修改 | 修复 z 语义 + 默认值 + max_time |
| `visualization_app.html` | 修改 | 修复前端默认值和滑块范围 |
| `DDM_Parameter_Explore/DDM_CRF_逆向推断可行性分析.md` | 新建 | 完整可行性分析文档 |

---

## 验证步骤

1. 重启 `app_server.py`
2. 打开 DDM 参数模式标签页
3. 设置 v=1.0, a=1.2, t=0.30, z=0.5 → 点击生成
4. 观察 CRF 曲线应与 notebook `plot_CRF_zbias_Wiener.ipynb` 的 neutral 条件接近
5. 查阅可行性分析文档确认分析完整
