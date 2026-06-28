# DDM 参数生成模式可视化 — 新增标签页计划

## 概述

在 `visualization_app.html` 中新增第 7 个标签页 **"DDM参数模式"**，允许用户设置 DDM 参数（v/a/t/z），后端生成模拟数据，前端以交互式 CRF 曲线和参数扫描图展示不同参数下的行为生成模式。核心理念：**DDM参数 → 数据模拟 → CRF可视化呈现**。

---

## 当前状态分析

### 现有6个标签页
| 标签页 | 功能 | 数据来源 |
|--------|------|----------|
| tab-experiment | 实验按键逻辑模拟 | `/api/experiment/*` |
| tab-selfcheck | 数据自查 | `/api/data/self_check` |
| tab-data | 数据选择与浏览 | `/api/data/*` |
| tab-visualization | 交互式CRF可视化 | `/api/data/all` |
| tab-design | 设计空间分析 | `/api/data/all` |
| tab-spe | SPE数据库 | `/api/spe/*` |

### 现有后端 (app_server.py)
- 端口 8899，Python `http.server` 实现
- 仅有 `do_GET`，无 `do_POST`
- 无任何 DDM 参数相关 API
- 无 DDM 仿真能力

### 可复用的 DDM 仿真代码
- `automation/core/ddm_engine.py` 中 `simulate_ddm_euler()` — Euler-Maruyama DDM 仿真
- 函数签名：`simulate_ddm_euler(v, a, z, t0, dt=0.001, max_time_s=3.0) → (RT, response)`

### SPE_Visualizer 参考
- `SPE_Visualizer.html` 的 "参数探索" 标签页（第409-488行）提供：
  - X 轴维度选择（T/P/W）
  - Y 轴指标多选（spe_rt, spe_acc, v_self, v_stranger, a, t0, z）
  - 模型对比（模型1 vs 模型2）
  - 后端 `/api/sweep` 返回曲线数据

---

## 方案设计

### 数据流
```
用户设参(v,a,t,z) → 后端 DDM 仿真(Euler-Maruyama) → 生成 trial 数据(RT, response)
                                                              ↓
                                         前端渲染: CRF曲线 + RT分布 + 参数扫描图
```

### 架构图
```
┌─ Left Panel (控制面板) ─────────────────────┐
│  DDM 参数滑块: v, a, t (t0), z              │
│  模拟参数: 试次数, 被试数                      │
│  扫描维度选择: X轴(P/T/W), Y轴(指标)           │
│  [生成模拟数据] 按钮                          │
│  [生成参数曲线] 按钮                          │
└─────────────────────────────────────────────┘
┌─ Right Panel (可视化区域) ───────────────────┐
│  Chart 1: CRF 曲线 (Self/Stranger 按匹配键比例)│
│  Chart 2: RT 分布直方图 (Self vs Stranger)    │
│  Chart 3: 参数扫描折线图 (类似SPE_Visualizer)  │
└─────────────────────────────────────────────┘
```

---

## 实施步骤

### Step 1: 后端 — 新增 DDM 仿真与 API 端点

**文件**: `1_Code/Python_for_Check/Visualization/app_server.py`

#### 1.1 添加 `do_POST` 方法支持 POST 请求
在 `AppHandler` 类中新增 `do_POST` 方法，用于接收 JSON body 参数。

#### 1.2 添加 DDM 仿真函数（内嵌版）
将 `automation/core/ddm_engine.py` 中的 `simulate_ddm_euler` 函数复制到 `app_server.py` 中（避免跨模块依赖）：
```python
def ddm_simulate(v, a, z, t0, n_trials, dt=0.001, max_time=3.0):
    """生成 n_trials 条 DDM 仿真数据"""
    trials = []
    for _ in range(n_trials):
        rt, resp = simulate_ddm_euler(v, a, z, t0, dt, max_time)
        trials.append({'RT': rt, 'response': resp, 'omission': np.isnan(rt)})
    return trials
```

#### 1.3 新增 API 端点

##### `POST /api/ddm/generate`
- **输入**: `{"v": 1.5, "a": 1.5, "z": 0.75, "t0": 0.2, "n_trials": 500}`
- **输出**: `{"trials": [{"RT": 0.45, "response": 1, "omission": false}, ...], "summary": {"mean_rt": ..., "acc": ..., "n_valid": ...}}`
- **用途**: 根据用户设置的 v/a/t0/z 生成一批模拟 trial 数据，供 CRF 可视化使用

##### `POST /api/ddm/sweep`
- **输入**: `{"sweep_var": "v", "sweep_range": [0.5, 3.0, 20], "fixed": {"a": 1.5, "z": 0.75, "t0": 0.2}, "n_trials": 200}`
- **输出**: `{"x_values": [0.5, 0.625, ...], "curves": {"mean_rt": [...], "acc": [...], "spe_rt": [...]}}`
- **用途**: 扫描一个 DDM 参数维度，观察 RT/ACC 的变化曲线，类似 SPE_Visualizer 的 sweep 功能

### Step 2: 前端 — 新增 "DDM参数模式" 标签页

**文件**: `1_Code/Python_for_Check/Visualization/visualization_app.html`

#### 2.1 HTML 结构修改
- 在 `<div class="tab-nav">`（第200-207行）中新增标签按钮:
  ```html
  <button class="tab-btn" data-tab="tab-ddm">DDM参数模式</button>
  ```

#### 2.2 JavaScript 修改

##### 在 `renderTabContent()` (第347-358行) 新增 case:
```javascript
case 'tab-ddm': renderDDMTab(lp, rp); break;
```

##### 新增 `renderDDMTab(lp, rp)` 函数

**左侧面板 (lp)**:
- DDM 参数滑块组:
  - v (漂移率): 0.1 ~ 5.0, 默认 1.5, step 0.1
  - a (决策边界): 0.5 ~ 4.0, 默认 1.5, step 0.1
  - t (非决策时间 t0): 0.1 ~ 0.5 s, 默认 0.2, step 0.01
  - z (起点): 0.1 ~ a (跟随a变化), 默认 a/2, step 0.05
- 模拟参数:
  - 试次数: 100 ~ 2000, 默认 500
  - 随机种子
- Self/Stranger 双条件参数（可启用差异对比）:
  - Self: v_self, a_self, t_self, z_self
  - Stranger: v_stranger, a_stranger, t_stranger, z_stranger
- 按钮:
  - [生成模拟数据] — 调用 `/api/ddm/generate`，更新 CRF 图表
  - [生成参数曲线] — 调用 `/api/ddm/sweep`，更新参数扫描图表

**右侧面板 (rp)**:
- Chart 1: **CRF 曲线** — Self vs Stranger 的匹配键比例 × RT分位数
  - 使用 scatter + showLine（与现有 CRF 模块风格一致）
  - 纵轴：匹配键选择比例（0~1），横轴：RT
  - 包含 y=0.5 基线
- Chart 2: **RT 分布** — 直方图或密度曲线
  - Self (红色) vs Stranger (蓝色) 的 RT 分布
  - 标注均值线
- Chart 3: **参数扫描图** — 沿选定维度的变化曲线
  - X 轴选择: v / a / t / z（单选按钮）
  - Y 轴选择: RT / ACC / SPE_RT（多选芯片）
  - 交互式折线图，支持多曲线叠加

#### 2.3 辅助函数
- `runDDMGenerate()` — 调用后端生成数据
- `runDDMSweep()` — 调用后端扫描参数
- `renderDDMCRFChart(trials)` — 渲染 CRF 曲线
- `renderDDMRTDistChart(trials)` — 渲染 RT 分布
- `renderDDMSweepChart(data)` — 渲染参数扫描图

#### 2.4 CSS 样式
- 复用现有暗色/亮色主题变量
- DDM 参数滑块样式与 `SPE_Visualizer.html` 风格一致
- 新增 `.ddm-slider-row` 样式（带实时数值显示）

### Step 3: CRF 计算与可视化集成

#### CRF 分箱计算（前端）
复用现有 `visualization_app.html` 中 CRF 的计算逻辑（分位数分箱 + 匹配键比例），但数据源改为 DDM 仿真生成的 trial 数据：

```javascript
function computeDDMCRF(trials, identity, nQuantiles=5) {
  // identity: 'self' | 'stranger'
  const filtered = trials.filter(t => !t.omission && t.identity === identity);
  const sorted = [...filtered].sort((a, b) => a.RT - b.RT);
  // ... 分箱计算 ...
  return bins; // [{rtMean, upperProp}, ...]
}
```

#### DDM response 映射
- DDM 仿真返回 `response` ∈ {0, 1}（下界/上界）
- 映射到匹配/非匹配键:
  - 对于 Self 条件: response=1 → 匹配键（Self优势），response=0 → 不匹配
  - 对于 Stranger 条件: response=1 → 匹配键（Stranger优势），response=0 → 不匹配

---

## 文件修改清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `app_server.py` | 修改 | 添加 `do_POST`、DDM仿真函数、2个新API端点 |
| `visualization_app.html` | 修改 | 新增第7个标签页按钮 + `renderDDMTab()` + 3个图表 + 辅助函数 |

无需创建新文件。

---

## 假设与决策

1. **DDM 仿真使用 Euler-Maruyama 方法**，与项目现有 `automation/core/ddm_engine.py` 一致
2. **Self/Stranger 通过两套 DDM 参数区分**（v_self > v_stranger 体现 SPE）
3. **CRF 计算复用现有分位数分箱逻辑**（5分位，按RT排序后计算匹配键比例）
4. **使用 POST 请求**（JSON body），与现有 GET-only 不同但更适合复杂参数传递
5. **所有计算在前端完成后端只返回原始 trial 数据**，减轻服务器负载

---

## 验证步骤

1. 启动 `app_server.py` 在端口 8899
2. 打开 `http://localhost:8899`
3. 点击 "DDM参数模式" 标签页
4. 调整 v/a/t/z 滑块，点击「生成模拟数据」，观察 CRF 曲线和 RT 分布变化
5. 点击「生成参数曲线」，选择不同 X/Y 轴维度，观察参数扫描图
6. 启用 Self/Stranger 差异模式，对比两组参数下的 CRF
