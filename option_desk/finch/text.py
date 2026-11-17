from __future__ import annotations

from option_desk.i18n import normalize_lang

# Buyer-facing copy for the Finch channel. Same shape as option_desk.i18n.UI:
# add every key to BOTH "en" and "zh".
COPY: dict[str, dict[str, str]] = {
    "en": {
        "capability": (
            "**Option Desk** reviews short-dated (3–9 DTE) US equity options for the wheel strategy "
            "and stamps each ticker **OPEN** or **SKIP**. It recommends; it never places orders.\n\n"
            "**Two books**\n"
            "- **Cash-secured puts**: send tickers and the cash you set aside (leave cash out and each "
            "ticker is sized at 1 contract). You get CSP or bull put spread, the conservative (~0.11Δ) or "
            "standard (~0.20Δ) bucket, the exact contract, the reasoning, and expiration P/L.\n"
            "- **Covered calls**: send the ticker, shares held (100 or more) and cost basis (defaults: 100 "
            "shares, no cost check). You get the covered-call bucket and contract, and whether assignment "
            "is acceptable against your cost.\n\n"
            "**What it checks**: live yfinance option chain with Black-Scholes Delta; ATM IV vs 20/60/120-day "
            "realized volatility; 1-sigma expected move; a 0–100 contract score; VIX + SPY/QQQ regime; "
            "earnings and FOMC inside the holding window (hard skip); CPI / NFP / PCE (soft); and a news "
            "scout for off-calendar gap risk. The final pick must be a contract already in the screened buckets.\n\n"
            "**Examples**\n"
            "- `Sell puts on NVDA and MSFT, cash 50000`\n"
            "- `Covered call on AAPL, 300 shares, cost 180`\n"
            "- `NVDA 卖put 现金5万` (write in Chinese to get a Chinese report)\n\n"
            "Up to {n} tickers per request. A run usually takes about a minute.\n\n"
            "_Not investment advice. Not automated trading. Options can lose the entire premium; confirm "
            "quotes, fills and assignment cash before any order._"
        ),
        "ask_intro": "To run the desk I still need:",
        "ask_tickers": "- Tickers, up to {n} (uppercase symbols such as NVDA, MSFT, or cashtags like $nvda)",
        "ask_mode": "Say “covered call” for the covered-call desk; otherwise I run the cash-secured put desk.",
        "ask_example": "Example: `NVDA MSFT sell puts, cash 50000` or `covered call AAPL, 300 shares, cost 180`",
        "problem_delta": "- Delta must be between {lo} and {hi} (default 0.20).",
        "problem_cash": "- Cash must be between $1,000 and $10,000,000.",
        "problem_shares": "- Shares must be between 100 and 1,000,000.",
        "problem_cost": "- Cost basis must be above $0 and at most $1,000,000.",
        "note_dropped": "One request analyses at most {n} tickers, so this run covers {kept} and skips {dropped}.",
        "stage_queued": "Queued",
        "stage_starting": "Starting",
        "stage_regime": "Reading the VIX / SPY / QQQ regime",
        "stage_screen": "Screening the {ticker} option chain",
        "stage_calendar": "Checking {ticker} earnings and FOMC dates",
        "stage_scout": "Searching the news for gap risk",
        "stage_classify": "Classifying events",
        "stage_desk": "Desk review",
        "stage_done": "Done",
        "err_analysis": "The analysis could not finish. Please try again later.",
        "err_input": (
            "Not enough information to run the desk. Please start a new request with tickers and cash, "
            "or ticker, shares and cost basis for a covered call."
        ),
        "err_unanswered": "No reply to the follow-up question arrived, so this request has ended.",
        "err_daily": "Today's free analysis quota is used up. Please try again tomorrow.",
        "err_data": "The market data source is rate-limiting right now. Please try again in a few minutes.",
        "skip_no_data": "No option chain came back for this ticker; see the warnings below.",
        "title_put": "Cash-secured put desk",
        "title_call": "Covered-call desk",
        "inputs_put": "Input: {tickers} · cash {cash} · standard Δ {delta}",
        "inputs_call": "Input: {tickers} · {shares} shares · cost {cost} · standard Δ {delta}",
        "not_given": "not given",
        "assumed_cash": "Cash was not given, so each ticker is sized at 1 contract; check the assignment cash before any order.",
        "assumed_shares": "Shares were not given, so this assumes 100 shares (1 covered call).",
        "assumed_cost_basis": "Cost basis was not given, so assignment is not checked against your cost.",
        "guide_wheel": (
            "**How the wheel works**: 1) on a stock you would happily own, sell a cash-secured put and keep the "
            "premium; 2) if it expires worthless, sell another; if assigned, you buy 100 shares at the strike; "
            "3) on those shares sell covered calls until they are called away, then start again. Only wheel "
            "names you want to hold, pick strikes you would buy at, and stay clear of earnings."
        ),
        "guide_income": (
            "**Collecting option premium**: with cash, sell cash-secured puts; with 100+ shares, sell covered "
            "calls, rolling weekly or every two weeks. 0.10–0.20Δ out-of-the-money contracts expire worthless "
            "more often but pay less; the closer to the money, the more premium and the higher the assignment odds."
        ),
        "guide_risk": (
            "**The risks**: a short put's real risk is a sharp drop and assignment; the loss can approach "
            "strike × 100 minus the premium. A covered call caps your upside if the stock rips, while the "
            "downside of the shares stays. Short-dated contracts must dodge gap events such as earnings and "
            "FOMC, which this desk checks automatically."
        ),
        "guide_beginner": (
            "**Where to start**: learn Delta (roughly the assignment odds), premium, strike and expiry first. "
            "Begin with cash-secured puts or covered calls on large, liquid names; no naked calls, no margin. "
            "Trade one or two contracts and run a few full cycles before sizing up."
        ),
        "guide_run": (
            "**Want concrete contracts?** Send tickers (up to {n}), for example:\n"
            "- `{put_example}`\n"
            "- `Covered call on AAPL, 300 shares, cost 180`\n\n"
            "Cash is optional; without it each ticker is sized at 1 contract.\n\n"
            "_Not investment advice. Not automated trading._"
        ),
        "guide_put_example": "Sell puts on NVDA and MSFT, cash {cash}",
        "sec_decision": "Decision",
        "sec_candidates": "Candidates",
        "assign_ok": "Assignment at this strike is acceptable.",
        "assign_not_ok": "Assignment at this strike is NOT acceptable versus your cost basis.",
        "per_ct": "/ct",
        "last_print": " (last print, confirm live quotes)",
        "qty_put": "CSP {n} ct, assignment ${cash}",
        "qty_call": "{n} ct covered",
        "spread": "spread: long {strike} (max loss ${loss}/ct, {n} ct)",
        "loss_capped": "capped",
        "loss_zero": "stock to $0",
        "calendar": "Holding window {start} → {end}",
        "hard": "hard skip: {reasons}",
        "fetched": "Chain fetched {ts} UTC.",
        "more_events": "…and {n} more.",
    },
    "zh": {
        "capability": (
            "**Option Desk（摩根大山期权决策台）** 针对美股 3–9 天到期的期权做 wheel 策略开仓评估，"
            "给每个标的盖 **OPEN** 或 **SKIP** 章。只给建议，从不下单。\n\n"
            "**两个决策台**\n"
            "- **卖 Put（现金担保）**：告诉我标的和可用现金（不写现金则每个标的按 1 张估算）。输出 CSP "
            "或牛市看跌价差、保守档（约 0.11Δ）或标准档（约 0.20Δ）、具体合约、理由和到期损益。\n"
            "- **备兑 Call**：告诉我标的、持股数（至少 100 股）和每股成本（默认 100 股、不检查成本）。"
            "输出备兑档位与合约，以及相对成本价被指派是否可以接受。\n\n"
            "**会检查什么**：yfinance 实时期权链 + Black-Scholes 估算 Delta；ATM IV 与 20/60/120 日已实现波动对比；"
            "1σ 预期波动；0–100 合约评分；VIX + SPY/QQQ 市场体制；持有期内的财报与 FOMC（硬性跳过）；"
            "CPI / NFP / PCE（软标签）；以及新闻侦察日历外的跳空风险。最终只能从筛出的档位里选合约。\n\n"
            "**示例**\n"
            "- `NVDA MSFT 卖put 现金5万`\n"
            "- `备兑 AAPL 300股 成本180`\n"
            "- `Sell puts on NVDA, cash 50000`（用英文提问会得到英文报告）\n\n"
            "每次最多 {n} 个标的，一次分析通常一分钟左右。\n\n"
            "_不构成投资建议，不自动交易。期权可能亏掉全部权利金；下单前请核对报价、成交价与被指派所需现金。_"
        ),
        "ask_intro": "开跑前还差这几项：",
        "ask_tickers": "- 标的代码，最多 {n} 个（如 NVDA、MSFT，也可以写英伟达、微软）",
        "ask_mode": "要做备兑 Call 请写“备兑”或“covered call”，否则默认走卖 Put。",
        "ask_example": "示例：`NVDA MSFT 卖put 现金5万` 或 `备兑 AAPL 300股 成本180`",
        "problem_delta": "- Delta 需在 {lo} 到 {hi} 之间（默认 0.20）。",
        "problem_cash": "- 现金需在 $1,000 到 $10,000,000 之间。",
        "problem_shares": "- 持股需在 100 到 1,000,000 股之间。",
        "problem_cost": "- 每股成本需大于 $0 且不超过 $1,000,000。",
        "note_dropped": "每次最多分析 {n} 个标的，本次分析 {kept}，未分析 {dropped}。",
        "stage_queued": "排队中",
        "stage_starting": "开始分析",
        "stage_regime": "读取 VIX / SPY / QQQ 市场体制",
        "stage_screen": "筛选 {ticker} 期权链",
        "stage_calendar": "检查 {ticker} 财报与 FOMC 日期",
        "stage_scout": "搜索新闻中的跳空风险",
        "stage_classify": "给事件分类",
        "stage_desk": "终审",
        "stage_done": "完成",
        "err_analysis": "分析没能完成，请稍后再试。",
        "err_input": "信息不足，无法开跑。请重新发起，写明标的和现金；备兑请写标的、持股数和成本。",
        "err_unanswered": "追问后一直没有收到补充信息，本次调用已结束。",
        "err_daily": "今天的免费分析次数已用完，请明天再试。",
        "err_data": "行情数据源暂时限流，请几分钟后再试。",
        "skip_no_data": "没拿到这只标的的期权链，见下方警告。",
        "title_put": "卖 Put 决策台",
        "title_call": "备兑 Call 决策台",
        "inputs_put": "输入：{tickers} · 现金 {cash} · 标准档 Δ {delta}",
        "inputs_call": "输入：{tickers} · 持股 {shares} 股 · 成本 {cost} · 标准档 Δ {delta}",
        "not_given": "未提供",
        "assumed_cash": "未提供可用现金，每个标的按 1 张合约估算，下单前请核对被指派所需现金。",
        "assumed_shares": "未提供持股数，按 100 股（1 张备兑）估算。",
        "assumed_cost_basis": "未提供持仓成本，不评估被指派后相对成本的盈亏。",
        "guide_wheel": (
            "**Wheel（轮动）怎么玩**：1）挑一只愿意长期持有的股票，用现金担保卖出 Put 收权利金；"
            "2）到期没被指派就继续卖，被指派就按行权价买入 100 股；3）持股后卖备兑 Call 继续收租，"
            "被行权卖出后回到第 1 步。只做愿意拿的股票，行权价选在愿意买入的位置，避开财报。"
        ),
        "guide_income": (
            "**怎么收期权租**：有现金就卖现金担保 Put，有 100 股以上持股就卖备兑 Call，"
            "每周或每两周滚动一次。0.10–0.20Δ 的虚值合约到期作废的概率高、权利金少；"
            "越接近平值，权利金越多，被指派的概率也越高。"
        ),
        "guide_risk": (
            "**风险在哪**：卖 Put 的主要风险是股价大跌被指派，亏损可以接近“行权价 × 100 − 权利金”；"
            "备兑 Call 会在股票大涨时封顶收益，而股票下跌的风险依然在。短期合约必须避开财报、"
            "FOMC 这类跳空事件，这正是本决策台会自动检查的。"
        ),
        "guide_beginner": (
            "**新手从哪开始**：先弄懂 Delta（约等于被指派概率）、权利金、行权价和到期日；"
            "从大盘股的现金担保卖 Put 或备兑 Call 开始，不裸卖、不加杠杆；每次一两张，"
            "先完整跑几个周期再加仓。"
        ),
        "guide_run": (
            "**想直接拿到具体合约？** 告诉我标的（最多 {n} 个），例如：\n"
            "- `{put_example}`\n"
            "- `备兑 AAPL 300股 成本180`\n\n"
            "现金可以不写，不写就每个标的按 1 张估算。\n\n"
            "_不构成投资建议，不自动交易。_"
        ),
        "guide_put_example": "NVDA MSFT 卖put 现金{cash}",
        "sec_decision": "结论",
        "sec_candidates": "候选合约",
        "assign_ok": "在这个行权价被指派可以接受。",
        "assign_not_ok": "相对持仓成本，在这个行权价被指派不可接受。",
        "per_ct": "/张",
        "last_print": "（成交价而非盘口，下单前请核实报价）",
        "qty_put": "CSP {n} 张，指派占用 ${cash}",
        "qty_call": "可卖 {n} 张",
        "spread": "价差：多头 {strike}（最大亏损 ${loss}/张，{n} 张）",
        "loss_capped": "有限",
        "loss_zero": "股价到 $0",
        "calendar": "持有窗口 {start} → {end}",
        "hard": "硬性跳过：{reasons}",
        "fetched": "期权链拉取时间 {ts} UTC。",
        "more_events": "……另有 {n} 条。",
    },
}


def ft(lang: str, key: str, **kwargs: object) -> str:
    pack = COPY.get(normalize_lang(lang), COPY["en"])
    text = pack.get(key, COPY["en"][key])
    return text.format(**kwargs) if kwargs else text
