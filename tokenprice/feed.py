"""
The feed on disk.

    prices/latest.json          every (provider, model) from the most recent run
    prices/history/YYYY-MM-DD.jsonl   one line per record, appended only when a price changed
    prices/spread.json          per-model price spread across providers, latest

`write_run` is what the hourly Action calls. `load_latest` is what the package
reads. Both are plain files so the feed works from a raw GitHub URL with no
server behind it.
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from .schema import Record

ROOT = Path(__file__).resolve().parent.parent / "prices"


def write_run(records: list[Record], root: Path | None = None, read_at: str | None = None) -> dict:
    root = root or ROOT
    if not records:
        raise ValueError("refusing to write an empty run")
    read_at = read_at or records[0].read_at
    root.mkdir(parents=True, exist_ok=True)
    (root / "history").mkdir(exist_ok=True)

    prev = {_key(r): _price_tuple(r) for r in load_latest(root)}
    changed = [r for r in records if prev.get(_key(r)) != _price_tuple(r)]

    latest = {"read_at": read_at, "count": len(records), "records": [r.to_dict() for r in records]}
    (root / "latest.json").write_text(json.dumps(latest, indent=1, sort_keys=True))

    day = read_at[:10]
    if changed:
        with (root / "history" / f"{day}.jsonl").open("a") as f:
            for r in changed:
                f.write(json.dumps(r.to_dict(), sort_keys=True) + "\n")

    sp = spread(records)
    (root / "spread.json").write_text(json.dumps({"read_at": read_at, "models": sp}, indent=1, sort_keys=True))

    # tiny file for badges; shields.io times out on the full feed
    top = max(sp.items(), key=lambda kv: kv[1]["ratio"] or 0) if sp else None
    summary = {
        "read_at": read_at,
        "records": len(records),
        "providers": len({r.provider for r in records}),
        "models": len({r.model for r in records}),
        "models_with_spread": len(sp),
        "top_spread_model": top[0] if top else None,
        "top_spread_ratio": top[1]["ratio"] if top else None,
    }
    (root / "summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True))
    return {"records": len(records), "changed": len(changed), "models_with_spread": len(sp), "day": day}


def changes_since(day: str, root: Path = ROOT) -> list[dict]:
    """Every history line on or after YYYY-MM-DD, oldest first."""
    out: list[dict] = []
    for d in history_days(root):
        if d < day:
            continue
        with (root / "history" / f"{d}.jsonl").open() as f:
            out.extend(json.loads(line) for line in f if line.strip())
    return out


def _key(r: Record) -> tuple[str, str]:
    return (r.provider, r.model_raw)


def _price_tuple(r: Record) -> tuple:
    return (r.input_per_m, r.output_per_m, r.cached_input_per_m)


def load_latest(root: Path = ROOT) -> list[Record]:
    p = root / "latest.json"
    if not p.exists():
        return []
    return [Record.from_dict(d) for d in json.loads(p.read_text())["records"]]


def spread(records: list[Record]) -> dict:
    """For each model served by 2+ distinct providers: min, max, ratio on a blended price.

    Only per-provider records count. The router's own listing (provider
    "openrouter") is excluded, since it is a price for the same endpoints.

    Blended = input + 3 * output per M, a fixed convention that weights output
    tokens the way a chat workload does. State it when you quote the number.
    """
    by: dict[str, list[Record]] = defaultdict(list)
    for r in records:
        if r.provider != "openrouter":
            by[r.model].append(r)
    out = {}
    for model, rs in by.items():
        if len({r.provider for r in rs}) < 2:
            continue
        # key on price only: Record is not orderable, and ties are common in a real feed
        blended = sorted(((r.input_per_m + 3 * r.output_per_m, r) for r in rs), key=lambda t: t[0])
        lo, hi = blended[0], blended[-1]
        out[model] = {
            "n": len(rs),
            "min_blended_per_m": round(lo[0], 4),
            "max_blended_per_m": round(hi[0], 4),
            "ratio": round(hi[0] / lo[0], 2) if lo[0] > 0 else None,
            "cheapest": lo[1].provider,
            "dearest": hi[1].provider,
        }
    return out


def history_days(root: Path = ROOT) -> list[str]:
    h = root / "history"
    return sorted(p.stem for p in h.glob("*.jsonl")) if h.exists() else []


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
