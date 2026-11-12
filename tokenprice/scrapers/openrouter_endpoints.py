"""
Per-provider prices for a model. The /models endpoint carries one price per
model (the router's listed price); the provider spread lives here:

    https://openrouter.ai/api/v1/models/{author}/{slug}/endpoints

One request per model, so `scrape_all` paces itself. Failures on individual
models are returned, not raised; the feed should still be written from the
models that answered.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from tokenprice.schema import Record, normalize

BASE = "https://openrouter.ai/api/v1/models/{id}/endpoints"


def url_for(model_id: str) -> str:
    return BASE.format(id=model_id)


def fetch(model_id: str, timeout: int = 30) -> dict:
    req = Request(url_for(model_id), headers={"User-Agent": "tokenprice/0.1"})
    with urlopen(req, timeout=timeout) as r:
        return json.load(r)


def parse(payload: dict, model_id: str, read_at: str | None = None) -> list[Record]:
    read_at = read_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    data = payload.get("data") or {}
    out: list[Record] = []
    for ep in data.get("endpoints") or []:
        pricing = ep.get("pricing") or {}
        try:
            inp = float(pricing.get("prompt", "0")) * 1e6
            outp = float(pricing.get("completion", "0")) * 1e6
        except (TypeError, ValueError):
            continue
        if inp == 0 and outp == 0:
            continue
        provider = ep.get("provider_name") or ep.get("name")
        if not provider:
            continue
        cached = pricing.get("input_cache_read")
        out.append(
            Record(
                provider=str(provider).strip().lower().replace(" ", "-"),
                model=normalize(model_id),
                model_raw=model_id,
                input_per_m=round(inp, 6),
                output_per_m=round(outp, 6),
                cached_input_per_m=round(float(cached) * 1e6, 6) if cached not in (None, "", "0") else None,
                context=ep.get("context_length"),
                source=url_for(model_id),
                read_at=read_at,
                provenance="api",
                extra={"quantization": ep.get("quantization"), "uptime_30m": ep.get("uptime_last_30m")},
            )
        )
    return out


def scrape_all(model_ids: list[str], pause_s: float = 0.15) -> tuple[list[Record], list[str]]:
    """Returns (records, failed_model_ids)."""
    records: list[Record] = []
    failed: list[str] = []
    for mid in model_ids:
        try:
            records.extend(parse(fetch(mid), mid))
        except (HTTPError, URLError, TimeoutError, ValueError, KeyError):
            failed.append(mid)
        time.sleep(pause_s)
    return records, failed
