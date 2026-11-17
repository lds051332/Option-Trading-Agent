from __future__ import annotations

from option_desk.finch.parse import DeskRequest
from option_desk.finch.text import ft
from option_desk.i18n import localize_hard_reason, normalize_lang, t
from option_desk.schemas import (
    BucketCandidate,
    DeltaBucket,
    DeskAction,
    DeskMode,
    DeskRun,
    TickerDecision,
    TickerSnapshot,
)

MAX_EVENTS = 8


def _kv(lang: str, label: str, value: str) -> str:
    return f"{label}：{value}" if lang == "zh" else f"{label}: {value}"


def _pct(value: float | None) -> str:
    return "—" if value is None else f"{value:.0%}"


def _money(value: float) -> str:
    return f"{value:,.0f}"


def render_capabilities(lang: str, max_tickers: int) -> str:
    return ft(lang, "capability", n=max_tickers)


def render_guide(request: DeskRequest, topics: list[str], max_tickers: int) -> str:
    """Answer for a request with no ticker: strategy notes for the topics asked about, then how to run the desk."""
    lang = normalize_lang(request.language)
    if not topics:
        return render_capabilities(lang, max_tickers)
    cash = _money(request.cash) if request.cash else ("50000" if lang == "en" else "5万")
    parts = [ft(lang, f"guide_{topic}") for topic in topics]
    parts.append(ft(lang, "guide_run", n=max_tickers, put_example=ft(lang, "guide_put_example", cash=cash)))
    return "\n\n".join(parts) + "\n"


def _inputs(request: DeskRequest, lang: str) -> str:
    tickers = ", ".join(request.tickers)
    if request.mode == "call":
        cost = ft(lang, "not_given") if request.cost_basis is None else f"${request.cost_basis:,.2f}"
        return ft(
            lang,
            "inputs_call",
            tickers=tickers,
            shares=_money(request.shares or 0),
            cost=cost,
            delta=f"{request.delta:.2f}",
        )
    cash = ft(lang, "not_given") if request.cash is None else f"${_money(request.cash)}"
    return ft(lang, "inputs_put", tickers=tickers, cash=cash, delta=f"{request.delta:.2f}")


def _payoff(decision: TickerDecision, lang: str) -> str | None:
    payoff = decision.payoff
    if payoff is None:
        return None
    loss_note = ft(lang, "loss_capped" if payoff.loss_limited else "loss_zero")
    if lang == "zh":
        body = (
            f"{t(lang, 'md_max_profit')} ${_money(payoff.max_profit)}；"
            f"{t(lang, 'md_breakeven')} {payoff.breakeven:g}；"
            f"{t(lang, 'md_max_loss')} ${_money(payoff.max_loss)}（{loss_note}）"
        )
    else:
        body = (
            f"{t(lang, 'md_max_profit')} ${_money(payoff.max_profit)}; "
            f"{t(lang, 'md_breakeven')} {payoff.breakeven:g}; "
            f"{t(lang, 'md_max_loss')} ${_money(payoff.max_loss)} ({loss_note})"
        )
    return _kv(lang, t(lang, "md_payoff"), body)


def _decision_lines(decision: TickerDecision, lang: str, *, cost_known: bool = True) -> list[str]:
    head = f"**{decision.ticker} — {decision.action.value}**"
    bits = [
        decision.structure.value if decision.structure else None,
        decision.delta_bucket.value if decision.delta_bucket else None,
        f"`{decision.contract_id}`" if decision.contract_id else None,
    ]
    shown = [bit for bit in bits if bit]
    if shown:
        head = f"{head} · {' · '.join(shown)}"
    lines = [head, decision.why]
    if decision.action == DeskAction.OPEN:
        if decision.premium_tradeoff:
            lines.append(f"- {_kv(lang, t(lang, 'md_tradeoff'), decision.premium_tradeoff)}")
        if cost_known:
            payoff = _payoff(decision, lang)
            if payoff:
                lines.append(f"- {payoff}")
            lines.append(f"- {ft(lang, 'assign_ok' if decision.assignment_ok else 'assign_not_ok')}")
    lines.append("")
    return lines


def _bucket_line(bucket: DeltaBucket, cand: BucketCandidate | None, snap: TickerSnapshot, lang: str) -> str:
    if cand is None:
        return f"- {bucket.value}: {t(lang, 'no_contract')}"
    quote = cand.csp
    parts = [
        f"{t(lang, 'strike')} {quote.strike:g}",
        f"Δ {quote.delta:.3f}",
        f"{t(lang, 'dte')} {quote.dte}",
        f"{t(lang, 'bid_ask')} {quote.bid:.2f}/{quote.ask:.2f}",
        f"{t(lang, 'premium')} ${cand.premium_per_contract:.0f}{ft(lang, 'per_ct')}",
    ]
    if snap.mode is DeskMode.CALL:
        parts.append(ft(lang, "qty_call", n=cand.csp_contracts))
    else:
        parts.append(ft(lang, "qty_put", n=cand.csp_contracts, cash=_money(cand.assignment_cash)))
        if cand.spread:
            parts.append(
                ft(
                    lang,
                    "spread",
                    strike=f"{cand.spread.long.strike:g}",
                    loss=f"{cand.spread.max_loss_per_contract:.0f}",
                    n=cand.spread.contracts,
                )
            )
    if cand.score:
        where = t(lang, "md_inside_em" if cand.score.inside_expected_move else "md_outside_em")
        parts.append(f"{t(lang, 'md_score')} {cand.score.total} ({where})")
    last = ft(lang, "last_print") if quote.quote_source.value == "last" else ""
    return f"- {bucket.value} `{quote.contract_id}` · {' · '.join(parts)}{last}"


def _snapshot_lines(snap: TickerSnapshot, lang: str) -> list[str]:
    lines = [f"**{snap.ticker} @ {snap.spot:.2f}**"]
    for bucket in (DeltaBucket.CONSERVATIVE, DeltaBucket.STANDARD):
        lines.append(_bucket_line(bucket, snap.buckets.get(bucket), snap, lang))
    ctx = snap.iv_context
    if ctx is not None:
        iv = f"ATM {_pct(ctx.atm_iv)} · HV20 {_pct(ctx.hv_20)} · HV60 {_pct(ctx.hv_60)} · {ctx.regime.value}"
        if ctx.expected_move_pct is not None:
            dollars = f"${ctx.expected_move:.2f}" if ctx.expected_move is not None else "—"
            iv = f"{iv}; {t(lang, 'md_em')} ±{ctx.expected_move_pct:.1%} ({dollars}, {ctx.expected_move_dte or '?'} DTE)"
        lines.append(f"- {_kv(lang, t(lang, 'md_iv'), iv)}")
    cal = snap.calendar
    calendar = ft(lang, "calendar", start=cal.holding_start.isoformat(), end=cal.holding_end.isoformat())
    if cal.hard_skip:
        reasons = "; ".join(localize_hard_reason(reason, lang) for reason in cal.hard_reasons) or "—"
        calendar = f"{calendar} · {ft(lang, 'hard', reasons=reasons)}"
    if cal.soft_macros:
        tags = ", ".join(f"{m.kind} {m.event_date.isoformat()}" for m in cal.soft_macros)
        calendar = f"{calendar} · {_kv(lang, t(lang, 'md_soft'), tags)}"
    lines.append(f"- {calendar}")
    lines.extend(f"- {note}" for note in snap.notes)
    lines.append("")
    return lines


def render_run(run: DeskRun, request: DeskRequest) -> str:
    lang = normalize_lang(run.language)
    title = ft(lang, "title_call" if run.mode is DeskMode.CALL else "title_put")
    lines = [f"### {title} · {run.as_of.isoformat()}", _inputs(request, lang), ""]
    if request.dropped:
        lines += [
            "> "
            + ft(
                lang,
                "note_dropped",
                n=len(request.tickers),
                kept=", ".join(request.tickers),
                dropped=", ".join(request.dropped),
            ),
            "",
        ]
    lines += [f"> {ft(lang, f'assumed_{name}')}" for name in request.assumed]
    if request.assumed:
        lines.append("")

    cost_known = not (request.mode == "call" and request.cost_basis is None)
    lines.append(f"#### {ft(lang, 'sec_decision')}")
    for decision in run.desk.decisions:
        lines.extend(_decision_lines(decision, lang, cost_known=cost_known))
    decided = {decision.ticker for decision in run.desk.decisions}
    for ticker in request.tickers:
        if ticker not in decided:
            lines += [f"**{ticker} — {DeskAction.SKIP.value}**", ft(lang, "skip_no_data"), ""]
    if run.desk.portfolio_note:
        lines += [f"_{run.desk.portfolio_note}_", ""]

    if run.snapshots:
        lines.append(f"#### {ft(lang, 'sec_candidates')}")
        for snap in run.snapshots:
            lines.extend(_snapshot_lines(snap, lang))

    if run.market:
        lines.append(f"#### {t(lang, 'md_market')}")
        vix = f" · VIX {run.market.vix:.1f}" if run.market.vix is not None else ""
        lines.append(f"- **{run.market.label.value}**{vix}")
        if run.market.why:
            lines.append(f"- {run.market.why}")
        lines.append("")

    lines.append(f"#### {t(lang, 'md_events')}")
    if not run.events:
        lines.append(f"- {t(lang, 'md_none')}")
    for event in run.events[:MAX_EVENTS]:
        when = f" ({event.expected_time})" if event.expected_time else ""
        lines.append(f"- [{event.action.value} / {event.mechanism.value}] {event.title}{when}")
    if len(run.events) > MAX_EVENTS:
        lines.append(f"- {ft(lang, 'more_events', n=len(run.events) - MAX_EVENTS)}")
    lines.append("")

    if run.warnings:
        lines.append(f"#### {t(lang, 'md_warnings')}")
        lines.extend(f"- {warning}" for warning in run.warnings)
        lines.append("")

    footer = [t(lang, "md_chain"), ft(lang, "fetched", ts=run.fetched_at.strftime("%Y-%m-%d %H:%M"))]
    if cost_known and any(decision.payoff for decision in run.desk.decisions):
        footer.append(t(lang, "md_payoff_note"))
    lines += ["---", f"_{' '.join(footer)}_", "", f"**{t(lang, 'md_disclaimer')}**"]
    return "\n".join(lines).strip() + "\n"
