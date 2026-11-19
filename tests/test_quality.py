from datetime import date

from option_desk.chain.quality import (
    breach_exceeds_delta,
    build_iv_context,
    build_trend_context,
    classify_iv_regime,
    classify_market_regime,
    classify_trend,
    expected_move_pct,
    historical_breach_rate,
    realized_vol,
    score_contract,
    sma,
    trading_days,
)
from option_desk.chain.market import build_market_regime
from option_desk.schemas import (
    ContractQuote,
    DeskMode,
    IvRegime,
    MarketLabel,
    QuoteSource,
    TrendLabel,
)


def _quote(**overrides) -> ContractQuote:
    base = dict(
        contract_id="NVDA-2026-09-18-P-170",
        ticker="NVDA",
        expiry=date(2026, 9, 18),
        dte=7,
        strike=170.0,
        bid=1.8,
        ask=1.9,
        mid=1.85,
        iv=0.46,
        delta=0.20,
        open_interest=800,
        volume=200,
        spread_pct=0.054,
    )
    base.update(overrides)
    return ContractQuote(**base)


def _closes(start: float, n: int, step: float = 0.0) -> list[float]:
    return [start + i * step for i in range(n)]


def test_expected_move_one_sigma():
    pct = expected_move_pct(0.40, 7)
    assert abs(pct - 0.40 * (7 / 365) ** 0.5) < 1e-9
    assert expected_move_pct(0, 7) == 0.0
    assert expected_move_pct(0.4, 0) == 0.0


def test_realized_vol_needs_enough_obs():
    assert realized_vol(_closes(100, 5), 20) is None
    series = []
    price = 100.0
    for i in range(40):
        price *= 1.01 if i % 2 == 0 else 0.99
        series.append(price)
    hv = realized_vol(series, 20)
    assert hv is not None
    assert 0.05 < hv < 2.0


def test_sma_window():
    assert sma([1, 2, 3, 4], 3) == 3.0
    assert sma([1, 2], 3) is None


def test_iv_regime_thresholds():
    assert classify_iv_regime(0.20, 0.30) is IvRegime.LOW
    assert classify_iv_regime(0.30, 0.30) is IvRegime.NORMAL
    assert classify_iv_regime(0.40, 0.30) is IvRegime.HIGH
    assert classify_iv_regime(0.50, 0.30) is IvRegime.RICH
    assert classify_iv_regime(None, 0.30) is IvRegime.UNKNOWN


def test_market_regime_rules():
    assert classify_market_regime(32, 500, 510, 520) is MarketLabel.RISK_OFF
    assert classify_market_regime(26, 500, 510, 520) is MarketLabel.RISK_OFF
    assert classify_market_regime(23, 530, 520, 510) is MarketLabel.CAUTION
    assert classify_market_regime(12, 530, 520, 510) is MarketLabel.RISK_ON
    assert classify_market_regime(16, 530, 520, 510) is MarketLabel.NEUTRAL
    # Backwardation bumps caution → risk_off
    assert classify_market_regime(23, 530, 520, 510, vix_term=0.90) is MarketLabel.RISK_OFF


def test_score_penalizes_last_print_and_inside_em():
    live = score_contract(
        _quote(strike=160, delta=0.12),
        spot=180,
        target_delta=0.11,
        band=0.05,
        mode=DeskMode.PUT,
        iv_hv_ratio=1.3,
    )
    inside = score_contract(
        _quote(strike=175, delta=0.20, mid=2.5),
        spot=180,
        target_delta=0.20,
        band=0.06,
        mode=DeskMode.PUT,
        iv_hv_ratio=1.3,
    )
    stale = score_contract(
        _quote(quote_source=QuoteSource.LAST, bid=0, ask=0, spread_pct=1.0, strike=160, delta=0.12),
        spot=180,
        target_delta=0.11,
        band=0.05,
        mode=DeskMode.PUT,
        iv_hv_ratio=1.3,
    )
    assert live.inside_expected_move is False
    assert inside.inside_expected_move is True
    assert live.expected_move > inside.expected_move
    assert stale.spread == 0
    assert stale.total < live.total
    assert 0 <= live.total <= 100


def test_iv_context_from_quotes_and_closes():
    quotes = [_quote(strike=180, iv=0.50), _quote(strike=160, iv=0.40)]
    series = []
    price = 100.0
    for i in range(80):
        price *= 1.004 if i % 3 else 0.997
        series.append(price)
    ctx = build_iv_context(quotes, 180.0, series)
    assert ctx is not None
    assert ctx.atm_iv == 0.50
    assert ctx.hv_20 is not None
    assert ctx.expected_move_pct is not None
    assert ctx.expected_move == 180.0 * ctx.expected_move_pct


def test_trend_labels():
    assert classify_trend(110, 105, 100) is TrendLabel.UP
    assert classify_trend(90, 95, 100) is TrendLabel.DOWN
    assert classify_trend(100, 95, 105) is TrendLabel.FLAT
    assert classify_trend(100, 95, None) is TrendLabel.UNKNOWN


def test_trend_context_from_falling_closes():
    closes = _closes(200, 60, step=-1.0)
    ctx = build_trend_context(closes[-1], closes)
    assert ctx is not None
    assert ctx.label is TrendLabel.DOWN
    assert ctx.low_20 == closes[-1]
    assert ctx.high_20 == closes[-20]
    assert ctx.return_5d is not None and ctx.return_5d < 0
    assert build_trend_context(100, _closes(100, 10)) is None


def test_trading_days_from_dte():
    assert trading_days(7) == 5
    assert trading_days(1) == 1
    assert trading_days(0) == 1


def test_breach_rate_counts_windows_past_cushion():
    # Alternating ±3% days: every 1-session window moves 3%, 2-session windows net out.
    closes = []
    price = 100.0
    for i in range(80):
        price *= 1.03 if i % 2 == 0 else 1 / 1.03
        closes.append(price)
    put_rate, n = historical_breach_rate(closes, 0.02, 1, DeskMode.PUT)
    assert n == 79
    assert put_rate is not None and 0.45 < put_rate < 0.55
    call_rate, _ = historical_breach_rate(closes, 0.02, 2, DeskMode.CALL)
    assert call_rate == 0.0
    short, n_short = historical_breach_rate(closes[:30], 0.02, 1, DeskMode.PUT)
    assert short is None and n_short == 29


def test_breach_exceeds_delta_threshold():
    assert breach_exceeds_delta(0.30, 0.20) is True
    assert breach_exceeds_delta(0.25, 0.20) is False
    assert breach_exceeds_delta(None, 0.20) is False
    assert breach_exceeds_delta(0.30, 0.0) is False


def test_score_uses_price_history_when_closes_given():
    quote = _quote(strike=170, delta=0.20)
    calm = _closes(180, 120, step=0.05)
    without = score_contract(quote, spot=180, target_delta=0.20, band=0.06, mode=DeskMode.PUT, iv_hv_ratio=1.2)
    calm_score = score_contract(
        quote, spot=180, target_delta=0.20, band=0.06, mode=DeskMode.PUT, iv_hv_ratio=1.2, closes=calm
    )
    assert without.history is None
    assert without.hist_breach_rate is None
    assert calm_score.hist_breach_rate == 0.0
    assert calm_score.history == 100
    assert calm_score.hist_horizon_days == 5
    assert calm_score.beyond_recent_range is True
    assert calm_score.total >= without.total


def test_build_market_regime_localizes_why():
    vix = [18.0] * 5 + [21.0]
    spy = [500 + i * 0.2 for i in range(60)]
    qqq = [400 + i * 0.1 for i in range(60)]
    vix3m = [22.0]
    regime = build_market_regime(vix, spy, qqq, vix3m, lang="zh")
    assert regime is not None
    assert regime.vix == 21.0
    assert "SPY" in regime.why
    assert "50 日均" in regime.why
