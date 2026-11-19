import pytest


@pytest.fixture(autouse=True)
def _no_shared_scout_cache(monkeypatch):
    """Tests must never read or write the real ~/.option_desk scout cache."""
    monkeypatch.setenv("OPTION_DESK_SCOUT_CACHE", "off")
