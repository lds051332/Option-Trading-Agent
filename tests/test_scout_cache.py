from datetime import date

from option_desk.agents.structured import ModelCall
from option_desk.config import Settings
from option_desk.events import cache, scout, search
from option_desk.events.scout import BilingualEvent, BilingualEventList, classify_scout_hits
from option_desk.events.search import SearchHit, search_web
from option_desk.schemas import EventAction, EventMechanism


def _use_tmp_cache(monkeypatch, tmp_path):
    monkeypatch.setenv("OPTION_DESK_SCOUT_CACHE", str(tmp_path / "scout.sqlite3"))


def test_search_hits_are_reused_within_a_market_day(monkeypatch, tmp_path):
    _use_tmp_cache(monkeypatch, tmp_path)
    calls = []

    def live(query, key, limit):
        calls.append(query)
        return [SearchHit(title="BIS rule", url="https://x", snippet="s", query=query)]

    monkeypatch.setattr(search, "_search_live", live)
    first = search_web("NVDA export control", None, limit=4)
    second = search_web("NVDA export control", None, limit=4)
    assert calls == ["NVDA export control"]
    assert second == first


def test_empty_search_is_not_cached(monkeypatch, tmp_path):
    _use_tmp_cache(monkeypatch, tmp_path)
    calls = []

    def live(query, key, limit):
        calls.append(query)
        return []

    monkeypatch.setattr(search, "_search_live", live)
    search_web("q", None)
    search_web("q", None)
    assert len(calls) == 2


def test_cache_off_always_searches(monkeypatch):
    calls = []
    monkeypatch.setattr(search, "_search_live", lambda q, k, n: calls.append(q) or [])
    search_web("q", None)
    search_web("q", None)
    assert cache.get(cache.cache_key("search", "q")) is None
    assert len(calls) == 2


def _hits():
    return [SearchHit(title="BIS curbs remote access", url="https://x", snippet="dated 2026-11-18", query="q")]


def test_classification_shared_across_languages(monkeypatch, tmp_path):
    _use_tmp_cache(monkeypatch, tmp_path)
    calls = []

    def fake_invoke(llm, schema, messages, provider):
        calls.append(schema)
        parsed = BilingualEventList(
            events=[
                BilingualEvent(
                    title="BIS curbs remote access",
                    title_zh="BIS 限制远程访问",
                    expected_time="2026-11-18",
                    tickers=["NVDA"],
                    mechanism=EventMechanism.REPRICING,
                    action=EventAction.REDUCE,
                )
            ]
        )
        return parsed, ModelCall(method="json_schema", elapsed_ms=5)

    monkeypatch.setattr(scout, "invoke_structured_traced", fake_invoke)
    as_of = date(2026, 11, 19)
    en, _, en_call = classify_scout_hits(["NVDA"], as_of, Settings(output_language="en"), object(), _hits())
    zh, _, zh_call = classify_scout_hits(["NVDA"], as_of, Settings(output_language="zh"), object(), _hits())
    assert calls == [BilingualEventList]
    assert en_call.method == "json_schema"
    assert zh_call.method == "cached"
    assert en[0].title == "BIS curbs remote access"
    assert zh[0].title == "BIS 限制远程访问"
    assert en[0].action == zh[0].action == EventAction.REDUCE
