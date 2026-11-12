"""
OpenRouter lists every model it routes with per-token prices in one public
endpoint. One call, hundreds of (provider, model) prices, no key needed.

    https://openrouter.ai/api/v1/models

Prices in the response are USD per token as strings; we convert to USD per
million. The upstream provider is not in this endpoint, so provider is
"openrouter" and the model id keeps its vendor prefix in model_raw.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from urllib.request import Request, urlopen

from tokenprice.schema import Record, normalize

URL = "https://openrouter.ai/api/v1/models"


def fetch(url: str = URL, timeout: int = 30) -> dict:
    req = Request(url, headers={"User-Agent": "tokenprice/0.1 (+https://github.com/reckonresearch/tokenprice)"})
    with urlopen(req, timeout=timeout) as r:
        return json.load(r)


def parse(payload: dict, read_at: str | None = None, url: str = URL) -> list[Record]:
    read_at = read_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out: list[Record] = []
    for m in payload.get("data", []):
        pricing = m.get("pricing") or {}
        try:
            inp = float(pricing.get("prompt", "0")) * 1e6
            outp = float(pricing.get("completion", "0")) * 1e6
        except (TypeError, ValueError):
            continue
        if inp == 0 and outp == 0:
            continue  # free tiers carry no price signal
        if inp < 0 or outp < 0:
            continue  # OpenRouter uses -1 for dynamic pricing (auto router); not a price
        cached = pricing.get("input_cache_read")
        try:
            rec = Record(
                provider="openrouter",
                model=normalize(m["id"]),
                model_raw=m["id"],
                input_per_m=round(inp, 6),
                output_per_m=round(outp, 6),
                cached_input_per_m=round(float(cached) * 1e6, 6) if cached not in (None, "", "0") else None,
                context=m.get("context_length"),
                source=url,
                read_at=read_at,
                provenance="api",
                extra={"name": m.get("name")},
            )
        except ValueError:
            continue  # validator refused it; the feed must not carry it
        out.append(rec)
    return out


def scrape() -> list[Record]:
    return parse(fetch())
