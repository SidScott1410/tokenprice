"""
tokenprice: live token prices across providers, one feed, one call.

    import tokenprice
    tokenprice.get("llama-3-8b-instruct")            # cheapest record for the model
    tokenprice.get("llama-3-8b-instruct", provider="openrouter")
    tokenprice.cheapest("llama-3-8b-instruct", n=5)
    tokenprice.spread("llama-3-8b-instruct")         # {"ratio": 8.6, ...}

Reads prices/latest.json from the installed package, or from the raw GitHub
feed when `refresh()` is called.
"""
from __future__ import annotations

import json
from urllib.request import Request, urlopen

from .feed import ROOT, load_latest
from .feed import spread as _spread
from .schema import Record, normalize

__version__ = "0.1.0"
FEED_URL = "https://raw.githubusercontent.com/SidScott1410/tokenprice/main/prices/latest.json"

_cache: list[Record] | None = None


def _records() -> list[Record]:
    global _cache
    if _cache is None:
        _cache = load_latest(ROOT)
    return _cache


def refresh(url: str = FEED_URL, timeout: int = 20) -> int:
    """Pull the latest feed from GitHub into memory. Returns record count."""
    global _cache
    req = Request(url, headers={"User-Agent": f"tokenprice/{__version__}"})
    with urlopen(req, timeout=timeout) as r:
        data = json.load(r)
    _cache = [Record.from_dict(d) for d in data["records"]]
    return len(_cache)


def all_for(model: str) -> list[Record]:
    key = normalize(model)
    return sorted((r for r in _records() if r.model == key), key=lambda r: r.input_per_m + 3 * r.output_per_m)


def get(model: str, provider: str | None = None) -> Record | None:
    rs = all_for(model)
    if provider:
        rs = [r for r in rs if r.provider == provider or r.model_raw.startswith(provider)]
    return rs[0] if rs else None


def cheapest(model: str, n: int = 3) -> list[Record]:
    return all_for(model)[:n]


def spread(model: str) -> dict | None:
    return _spread(_records()).get(normalize(model))


def models() -> list[str]:
    return sorted({r.model for r in _records()})


__all__ = ["get", "cheapest", "spread", "all_for", "models", "refresh", "Record", "normalize", "FEED_URL"]
