from __future__ import annotations

from dataclasses import dataclass

from option_desk.events import cache


@dataclass
class SearchHit:
    title: str
    url: str
    snippet: str
    query: str

    def as_dict(self) -> dict[str, str]:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "query": self.query,
        }


def _tavily_search(query: str, api_key: str, limit: int) -> list[SearchHit]:
    from tavily import TavilyClient

    client = TavilyClient(api_key=api_key)
    payload = client.search(query, max_results=limit)
    hits: list[SearchHit] = []
    for item in payload.get("results", []):
        hits.append(
            SearchHit(
                title=item.get("title") or "",
                url=item.get("url") or "",
                snippet=(item.get("content") or "")[:500],
                query=query,
            )
        )
    return hits


def _ddgs_search(query: str, limit: int) -> list[SearchHit]:
    from ddgs import DDGS

    hits: list[SearchHit] = []
    with DDGS() as ddgs:
        for item in ddgs.text(query, max_results=limit):
            hits.append(
                SearchHit(
                    title=item.get("title") or "",
                    url=item.get("href") or item.get("url") or "",
                    snippet=(item.get("body") or item.get("snippet") or "")[:500],
                    query=query,
                )
            )
    return hits


def _search_live(query: str, tavily_api_key: str | None, limit: int) -> list[SearchHit]:
    if tavily_api_key:
        try:
            return _tavily_search(query, tavily_api_key, limit)
        except Exception:
            pass
    try:
        return _ddgs_search(query, limit)
    except Exception:
        return []


def search_web(query: str, tavily_api_key: str | None, limit: int = 5) -> list[SearchHit]:
    """Same query on the same market day returns the cached hits. Empty results are not cached."""
    key = cache.cache_key("search", query, limit, cache.market_day())
    cached = cache.get(key)
    if cached is not None:
        return [SearchHit(**item) for item in cached]
    hits = _search_live(query, tavily_api_key, limit)
    if hits:
        cache.put(key, [hit.as_dict() for hit in hits])
    return hits
