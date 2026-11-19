from __future__ import annotations

from datetime import date

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from option_desk.agents.structured import ModelCall, invoke_structured_traced
from option_desk.config import Settings, missing_llm_key_hint
from option_desk.events import cache
from option_desk.events.search import SearchHit, search_web
from option_desk.i18n import normalize_lang, t
from option_desk.schemas import EventAction, EventMechanism, ScoutedEvent


QUERY_TEMPLATES = (
    "{names} export control OR BIS OR TSMC OR NVIDIA China restriction",
    "{names} Azure OR hyperscaler AI capex cut OR cloud spending",
    "{names} antitrust OR DOJ OR lawsuit OR guidance cut",
    "this week FOMC OR CPI OR NFP OR PCE market impact {as_of}",
    "{names} earnings OR unexpected news this week",
)

GEOPOLITIC_HINTS = (
    "war",
    "invasion",
    "missile",
    "strait",
    "geopolit",
    "conflict",
    "military",
)

SYSTEM = """You extract tradable event risk for a 3-9 DTE cash-secured put desk on US mega-cap stocks.

Rules:
- Only keep events that could cause a gap or a sharp reprice during the holding window.
- Persistent narratives (AI boom, "war risk" with no dated catalyst) are noise → action=ignore, mechanism=noise.
- If expected_time is unknown AND mechanism is not a clearly dated catalyst, action must be ignore.
- Export controls, hyperscaler capex cuts, unexpected lawsuits, supply shocks: skip or reduce depending on whether they land this week.
- Do not invent dates. If a source does not give a date, expected_time is null.
- tickers must be a subset of the universe provided.
- action is exactly one of ignore, reduce, spread_only, skip.
- mechanism is exactly one of gap, repricing, noise.
- Write title and detail in English. Also fill title_zh and detail_zh with the same content in Simplified Chinese.
  Keep tickers, numbers, and enum values unchanged in both.
"""


class BilingualEvent(ScoutedEvent):
    title_zh: str = ""
    detail_zh: str = ""


class BilingualEventList(BaseModel):
    """One classification serves every output language, so zh and en runs see the same actions."""

    events: list[BilingualEvent] = Field(default_factory=list)


def _localize(event: BilingualEvent, lang: str) -> ScoutedEvent:
    data = event.model_dump(exclude={"title_zh", "detail_zh"})
    if normalize_lang(lang) == "zh":
        data["title"] = event.title_zh.strip() or event.title
        data["detail"] = event.detail_zh.strip() or event.detail
    return ScoutedEvent.model_validate(data)


def _queries(tickers: list[str], as_of: date) -> list[str]:
    names = " OR ".join(tickers)
    return [template.format(names=names, as_of=as_of.isoformat()) for template in QUERY_TEMPLATES]


def _normalize(event: ScoutedEvent, universe: list[str]) -> ScoutedEvent:
    tickers = [t.upper() for t in event.tickers if t.upper() in universe]
    if not tickers:
        tickers = list(universe)
    action = event.action
    mechanism = event.mechanism
    expected = (event.expected_time or "").strip() or None
    title_l = event.title.lower()
    geo = any(h in title_l or h in event.detail.lower() for h in GEOPOLITIC_HINTS)
    if not expected:
        if mechanism == EventMechanism.NOISE or geo:
            action = EventAction.IGNORE
            mechanism = EventMechanism.NOISE
        elif action != EventAction.IGNORE and mechanism != EventMechanism.GAP:
            action = EventAction.IGNORE
            mechanism = EventMechanism.NOISE
    return event.model_copy(
        update={
            "tickers": tickers,
            "action": action,
            "mechanism": mechanism,
            "expected_time": expected,
        }
    )


def scout_queries(tickers: list[str], as_of: date) -> list[str]:
    return _queries(tickers, as_of)


def classify_scout_hits(
    tickers: list[str],
    as_of: date,
    settings: Settings,
    llm,
    hits: list[SearchHit],
) -> tuple[list[ScoutedEvent], list[str], ModelCall | None]:
    warnings: list[str] = []
    if not hits:
        warnings.append(t(settings.output_language, "search_empty"))
        return [], warnings, None
    if llm is None:
        warnings.append(missing_llm_key_hint() + t(settings.output_language, "skipped_classify"))
        return [], warnings, ModelCall(method="heuristic", elapsed_ms=0)

    lang = settings.output_language
    digest = "\n".join(
        f"- [{h.query}] {h.title} | {h.snippet} | {h.url}" for h in hits[:24]
    )
    key = cache.cache_key("classify", sorted(tickers), as_of.isoformat(), settings.min_dte, settings.max_dte, digest)
    cached = cache.get(key)
    if cached is not None:
        parsed = BilingualEventList.model_validate(cached)
        events = [_normalize(_localize(event, lang), tickers) for event in parsed.events]
        return events, warnings, ModelCall(method="cached", elapsed_ms=0)
    prompt = (
        f"Universe: {', '.join(tickers)}\n"
        f"As-of date: {as_of.isoformat()}\n"
        f"Holding window: about {settings.min_dte}-{settings.max_dte} calendar days.\n\n"
        f"Search hits:\n{digest}"
    )
    try:
        parsed, call = invoke_structured_traced(
            llm,
            BilingualEventList,
            [
                SystemMessage(content=SYSTEM),
                HumanMessage(content=prompt),
            ],
            provider=settings.llm_endpoint().provider,
        )
    except Exception as exc:
        warnings.append(t(lang, "scout_failed").format(exc=exc))
        failed = getattr(exc, "call", None)
        call = failed if isinstance(failed, ModelCall) else ModelCall(method="failed", elapsed_ms=0, error=str(exc))
        return [], warnings, call
    cache.put(key, parsed.model_dump(mode="json"))
    events = [_normalize(_localize(event, lang), tickers) for event in parsed.events]
    return events, warnings, call


def scout_events(
    tickers: list[str],
    as_of: date,
    settings: Settings,
    llm,
) -> tuple[list[ScoutedEvent], list[SearchHit], list[str]]:
    hits: list[SearchHit] = []
    for query in scout_queries(tickers, as_of):
        hits.extend(search_web(query, settings.tavily_api_key, limit=4))
    events, warnings, _call = classify_scout_hits(tickers, as_of, settings, llm, hits)
    return events, hits, warnings
