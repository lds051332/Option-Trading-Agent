# 开发进度

按时间倒序。这里写「做了什么、为什么这么做」；产品说明仍看仓库根目录 README。

---

## 2026-11-19 · v0.5b 决策质量：趋势与历史击穿率

### 背景

v0.5a 回答了「这约贵不贵、离预期波动多远、大盘什么状态」。还缺两件事：**这只股票自己在往哪走**，以及**它过去真实的波动，比期权价格隐含的大还是小**。Delta 是风险中性下的到期 ITM 概率；如果这只票过去同样长度的持有期里越过同等距离的频率明显更高，说明期权卖便宜了。

刻意不做：

- 不新增网络请求：复用 IV/HV 已经拉的 8 个月日收盘
- 不落库，不做回测框架
- 趋势和击穿率都只是 **reduce**（偏向保守档），单独不会 SKIP；Enforcer 不因此改写
- 不改选档主规则

### 公式与规则

**个股趋势（每个标的一次）**

| 条件 | 标签 |
| --- | --- |
| spot > SMA20 > SMA50 | `up` |
| spot < SMA20 < SMA50 | `down` |
| 其余 | `flat` |
| 收盘不足 50 日 | `unknown` |

另带近 5 日涨跌和 20 日收盘区间（最低/最高收盘，不是盘中高低）。卖 Put 遇 `down`、卖 Call 遇 `up` → reduce。

**历史击穿率（每个档位）**

```text
horizon = round(DTE × 5/7) 个交易日
cushion = |strike − spot| / spot
breach_rate = 过去所有长度为 horizon 的重叠窗口里，收盘到收盘跌幅 ≥ cushion（Put）或涨幅 ≥ cushion（Call）的占比
```

样本少于 40 个窗口则为空。标准档 `breach_rate ≥ 1.5 × delta` → reduce。

**评分**新增 `history` 片，权重 10：`breach/delta` 为 0 → 100、1 → 50、2 → 0。没有收盘数据时这一片为空并按剩余权重归一，所以旧快照的总分不变。

**20 日区间**：Put 行权价低于 20 日最低收盘、Call 行权价高于 20 日最高收盘 → `beyond_recent_range`。只做展示和提示词上下文，不参与 reduce（标准档在区间内很常见）。

### 接到哪

- `TickerSnapshot.trend_context`；`ContractScore.history / hist_breach_rate / hist_breach_samples / hist_horizon_days / beyond_recent_range`
- LLM 系统提示（Put / Call 各自的方向）和 snapshot 正文带上 trend、hist_breach、beyond_20d_range
- 启发式 `_quality_reduce` 加趋势和击穿率；理由里写明是哪条信号
- Web：质量面板加「个股趋势」网格；档位表评分列下加历史击穿率（≥1.5×Δ 标红）和「在 20 日区间外」
- CLI / markdown 报告 / Finch 回复同步
- 中英：`option_desk/i18n.py` 与 `web/src/i18n.ts`

### 文件

| 路径 | 作用 |
| --- | --- |
| `option_desk/chain/quality.py` | 趋势、击穿率、history 评分片 |
| `option_desk/chain/screener.py` | 一次拉收盘，IV/趋势/评分共用 |
| `option_desk/agents/desk.py` | 提示词 + 启发式 reduce + 理由 |
| `option_desk/report.py` | `trend_summary` / `history_summary`，Finch 共用 |
| `web/src/QualityPanel.tsx` | 趋势网格 |
| `web/src/Desk.tsx` | 档位表击穿率 |
| `tests/test_quality.py`、`tests/test_desk.py` | 公式、阈值、reduce 方向、提示词 |

### 已知边界

- 击穿率只看到期收盘，不看盘中触及；重叠窗口之间不独立，样本数不等于独立观测数
- 8 个月窗口里若含一次财报跳空，会抬高击穿率——这正是想提醒的，但持有期内的财报本来就硬 SKIP
- `--as-of` 不回放历史收盘，仍用当前快照

---

## 2026-09-13 · 可选持仓管理 V1

### 背景

开仓决策台已经能给出 OPEN/SKIP。缺的是「已经开了仓，现在该怎么办」。持仓必须是可选的：不录仓也能继续用 `/put` 和 `/call`。OPEN 不能自动变成持仓，因为建议不是成交。

### 做了什么

- 新增 `/positions`。仓位只存在浏览器 `option-desk:positions:v1`，不落库、不接券商
- Home 第三张 Optional 卡；Desk OPEN 且结构为 CSP / Covered Call 时可预填「加入我的持仓」
- `POST /api/positions/evaluate` 按到期日精确查用户那张合约（不走开仓 3–9 DTE 筛链），确定性规则给出 HOLD / CLOSE / ROLL
- Profit Capture、止盈 75%、临期 2DTE/50%、指派风险滚仓；CLOSE 优先于 ROLL
- `POST /api/positions/roll-candidates` 复用现有 3–9 DTE 筛链；用户确认实际成交后旧仓 ROLLED、新仓 OPEN
- Bull Put Spread 仍只在 Entry Desk；`/api/runs` 语义未改

刻意不做：数据库、登录、自动下单、多腿持仓、LLM 决定动作。

### 文件

| 路径 | 作用 |
| --- | --- |
| `web/src/positions/` | 本地仓位、导入导出、settings |
| `web/src/PositionsPage.tsx` | 持仓页（Windows 下不能叫 Positions.tsx，会和目录撞名） |
| `option_desk/positions/` | 估值、规则、滚仓候选 |
| `tests/test_position_*.py` | 公式、规则、API |

---

## 2026-09-12 · v0.5a 决策质量

### 背景

开仓流水线已经完整：Delta 分档、财报/FOMC 硬门控、宏观软标签、新闻侦察、LLM 终审、到期损益图。产品断层在持仓管理，但那一块需要状态对象。先补开仓决策本身缺的一层：**这约贵不贵、行权价离预期波动有多远、大盘现在什么状态**。

刻意不做：

- 不落库、不存每日 IV 序列，因此也没有 IV Percentile
- 不做全市场扫描器
- 不改选档主规则（仍是 Delta 带内最近 + NBBO 优先）
- 不加铁鹰 / Collar / 持仓管理

IV 体制用 **当前 ATM IV / 20 日已实现波动**。没有历史分位数之前，这是当天就能用、也不会假装「IVP=72」的做法。

### 公式与规则

**Expected Move（1σ）**

```text
EM% = IV × √(DTE / 365)
EM$ = spot × EM%
cushion% = |strike − spot| / spot   （Put 在现价下方，Call 在上方）
inside EM = cushion% < EM%
```

用该合约自己的 IV 和 DTE，不用历史期权库。ATM 合约的 EM 挂在 snapshot 上，给刻度尺用。

**已实现波动**

对数收益、样本标准差、×√252。窗口 20 / 60 / 120。样本不足 10 个交易日则该项为空。

**IV 体制（相对 HV20）**

| IV / HV20 | 标签 |
| ---: | --- |
| < 0.85 | `low` |
| < 1.15 | `normal` |
| < 1.50 | `high` |
| ≥ 1.50 | `rich` |

卖权利金时 `low` 表示期权相对近期股价波动偏便宜，启发式改走保守档；`high` / `rich` 不作为无视日历或事件的理由。

**市场体制（每轮一次，不是每只股票一次）**

输入：VIX、VIX3M/VIX 期限结构、SPY 相对 20/50 日均。

| 条件 | 标签 |
| --- | --- |
| VIX ≥ 30，或 VIX ≥ 25 且 SPY 低于 50 日均 | `risk_off` |
| VIX ≥ 22，或 SPY 低于 50 日均 | `caution` |
| VIX < 14 且 SPY 高于 20 与 50 日均 | `risk_on` |
| 其余 | `neutral` |

VIX 期限倒挂（VIX3M/VIX < 0.95）上调一档。`caution` / `risk_off` 只是 **reduce**（偏向保守档），单独不会 SKIP。Yahoo 拉失败则这一层缺席，流水线继续。

**合约评分 0–100**

给两档候选排序参考，不是下单指令。权重：Delta 贴合 25、IV 相对 HV 20、权利金/占用资金 20、价差 15、相对 EM 的安全垫 10、流动性 10。缺 IV 时去掉该片并按剩余权重归一。Last print 价差分为 0。选档函数 `select_bucket()` 不变，分数事后挂上。

启发式额外：标准档在 EM 内、保守档在 EM 外 → 改用保守档。

### 接到哪

- `TickerSnapshot.iv_context`、`BucketCandidate.score`、`DeskRun.market`
- 流水线在筛链前先发 `regime_started` / `regime_done`
- LLM 系统提示和 snapshot 正文带上 IV/EM/score/市场；启发式无 LLM 时走同一套 reduce
- Web：市场体制卡片、IV 网格、EM 刻度尺、评分列；移动端网格两列、刻度尺全宽、表继续横向滑
- CLI / markdown 报告同步这些字段
- 中英：`option_desk/i18n.py` 与 `web/src/i18n.ts`

### 文件

| 路径 | 作用 |
| --- | --- |
| `option_desk/chain/quality.py` | 纯计算：EM、HV、IV 体制、市场规则、评分 |
| `option_desk/chain/market.py` | yfinance 拉收盘价；失败则空 |
| `option_desk/chain/screener.py` | 筛完后挂 IV 上下文和分数 |
| `option_desk/pipeline.py` | 每轮一次市场体制 |
| `option_desk/agents/desk.py` | 提示词 + 启发式 reduce |
| `option_desk/schemas.py` | `IvContext` / `ContractScore` / `MarketRegime` |
| `web/src/QualityPanel.tsx` | IV 网格、EM 尺、市场卡片 |
| `tests/test_quality.py` | 公式与体制规则 |
| `tests/test_desk.py` | risk_off / 低 IV / 标准档在 EM 内 → 保守档 |

### 已知边界

- `--as-of` 仍然只改日历窗口；IV/HV/EM 用的是当前 yfinance 快照
- HV 每个标的多一次历史行情请求，市场体制每轮四次（VIX、VIX3M、SPY、QQQ）；失败不阻断分析
- 评分是排序辅助。终审仍只能从已有档位里挑 `contract_id`
