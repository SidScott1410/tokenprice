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

    prev_records = load_latest(root)
    prev = {_key(r): _price_tuple(r) for r in prev_records}
    changed = [r for r in records if prev.get(_key(r)) != _price_tuple(r)]
    removed = [r for r in prev_records if _key(r) not in {_key(x) for x in records}]
    # a listing that vanished is a change too (provider dropped the model)
    set_changed = bool(changed or removed or not (root / "latest.json").exists())

    day = read_at[:10]
    if set_changed:
        # only rewrite the big files when something moved: hourly rewrites of an
        # unchanged 25k-line file would put a new blob in git every hour forever
        latest = {"read_at": read_at, "count": len(records), "records": [r.to_dict() for r in records]}
        (root / "latest.json").write_text(json.dumps(latest, indent=1, sort_keys=True))
        write_csv(records, root / "latest.csv")
        write_litellm(records, root / "litellm.json", read_at)
        with (root / "history" / f"{day}.jsonl").open("a") as f:
            for r in changed:
                f.write(json.dumps(r.to_dict(), sort_keys=True) + "\n")
            for r in removed:
                d = r.to_dict()
                d["removed"] = True
                d["read_at"] = read_at
                f.write(json.dumps(d, sort_keys=True) + "\n")

    sp = spread(records)
    if set_changed:
        (root / "spread.json").write_text(json.dumps({"read_at": read_at, "models": sp}, indent=1, sort_keys=True))
    write_moves(root, read_at)

    # tiny file for badges; shields.io times out on the full feed
    top = max(sp.items(), key=lambda kv: kv[1]["ratio"] or 0) if sp else None
    top_r = max(sp.items(), key=lambda kv: kv[1]["ratio_p90"] or 0) if sp else None
    last_change = read_at if set_changed else (json.loads((root / "summary.json").read_text()).get("read_at")
                                                if (root / "summary.json").exists() else read_at)
    summary = {
        "read_at": last_change,     # when the price set last changed
        "checked_at": read_at,      # when the scrapers last ran
        "records": len(records),
        "providers": len({r.provider for r in records}),
        "models": len({r.model for r in records}),
        "models_with_spread": len(sp),
        "top_spread_model": top[0] if top else None,
        "top_spread_ratio": top[1]["ratio"] if top else None,
        "top_spread_p90_model": top_r[0] if top_r else None,
        "top_spread_p90_ratio": top_r[1]["ratio_p90"] if top_r else None,
    }
    (root / "summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True))
    return {"records": len(records), "changed": len(changed), "removed": len(removed),
            "models_with_spread": len(sp), "day": day}


def write_csv(records: list[Record], path: Path) -> None:
    """Flat file for spreadsheets and pandas. One row per listing."""
    import csv

    cols = ["provider", "model", "model_raw", "input_per_m", "output_per_m", "cached_input_per_m",
            "blended_per_m", "quantization", "context", "provenance", "source", "read_at"]
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in sorted(records, key=lambda r: (r.model, blended(r))):
            ex = r.extra or {}
            w.writerow([r.provider, r.model, r.model_raw, r.input_per_m, r.output_per_m,
                        "" if r.cached_input_per_m is None else r.cached_input_per_m,
                        round(blended(r), 6), ex.get("quantization") or "", r.context or "",
                        r.provenance, r.source, r.read_at])


def write_litellm(records: list[Record], path: Path, read_at: str) -> None:
    """LiteLLM `model_prices_and_context_window.json` shape, keyed `openrouter/<id>`.

    Uses the router's own listing (what a LiteLLM user pays through OpenRouter),
    per-token USD. Drop-in for `litellm.register_model(json.load(open(path)))`.
    """
    out: dict[str, dict] = {"_meta": {"source": "tokenprice", "read_at": read_at,
                                      "url": "https://github.com/SidScott1410/tokenprice"}}
    for r in records:
        if r.provider != "openrouter":
            continue
        entry = {
            "input_cost_per_token": round(r.input_per_m / 1e6, 12),
            "output_cost_per_token": round(r.output_per_m / 1e6, 12),
            "litellm_provider": "openrouter",
            "mode": "chat",
        }
        if r.cached_input_per_m is not None:
            entry["cache_read_input_token_cost"] = round(r.cached_input_per_m / 1e6, 12)
        if r.context:
            entry["max_input_tokens"] = r.context
        out[f"openrouter/{r.model_raw}"] = entry
    path.write_text(json.dumps(out, indent=1, sort_keys=True))


def moves(root: Path, days: int = 7, now: str | None = None) -> dict:
    """Price moves in the last `days`: per listing, first and last recorded price in the window."""
    from datetime import datetime, timedelta

    now_dt = datetime.strptime(now or now_iso(), "%Y-%m-%dT%H:%M:%SZ")
    since = (now_dt - timedelta(days=days)).strftime("%Y-%m-%d")
    first: dict[tuple, dict] = {}
    last: dict[tuple, dict] = {}
    removed: list[dict] = []
    for row in changes_since(since, root):
        k = (row["provider"], row["model_raw"], (row.get("extra") or {}).get("quantization"), row.get("context"))
        if row.get("removed"):
            removed.append(row)
            continue
        first.setdefault(k, row)
        last[k] = row
    cuts, rises, new = [], [], []
    for k, a in first.items():
        b = last[k]
        if a is b:
            new.append(b)  # first seen inside the window, never changed since
            continue
        pa = a["input_per_m"] + 3 * a["output_per_m"]
        pb = b["input_per_m"] + 3 * b["output_per_m"]
        if pb == pa or pa == 0:
            continue
        item = {"provider": b["provider"], "model_raw": b["model_raw"], "from": round(pa, 4), "to": round(pb, 4),
                "pct": round((pb - pa) / pa * 100, 1), "at": b["read_at"]}
        (cuts if pb < pa else rises).append(item)
    cuts.sort(key=lambda x: x["pct"])
    rises.sort(key=lambda x: -x["pct"])
    return {"since": since, "cuts": cuts, "rises": rises, "new": new, "removed": removed}


def write_moves(root: Path, read_at: str, days: int = 7) -> None:
    """MOVES.md: a human-readable digest of the last week, regenerated every run."""
    m = moves(root, days, read_at)
    sp = json.loads((root / "spread.json").read_text())["models"] if (root / "spread.json").exists() else {}
    top = sorted(sp.items(), key=lambda kv: -(kv[1].get("ratio_p90_p10") or 0))[:10]
    L = [f"# Price moves, last {days} days", "", f"Generated {read_at}. Blended = input + 3 x output, USD per M tokens.",
         f"Window starts {m['since']}. Source: [history/](history/).", ""]
    L += ["## Biggest cuts", "", "| provider | model | from | to | change |", "|---|---|---|---|---|"]
    L += [f"| {x['provider']} | {x['model_raw']} | {x['from']} | {x['to']} | {x['pct']}% |" for x in m["cuts"][:15]] or ["| (none) | | | | |"]
    L += ["", "## Biggest rises", "", "| provider | model | from | to | change |", "|---|---|---|---|---|"]
    L += [f"| {x['provider']} | {x['model_raw']} | {x['from']} | {x['to']} | +{x['pct']}% |" for x in m["rises"][:15]] or ["| (none) | | | | |"]
    L += ["", f"## New listings ({len(m['new'])})", ""]
    L += [f"- {x['provider']}: {x['model_raw']} at {round(x['input_per_m'] + 3 * x['output_per_m'], 4)}" for x in m["new"][:30]] or ["(none)"]
    L += ["", f"## Removed listings ({len(m['removed'])})", ""]
    L += [f"- {x['provider']}: {x['model_raw']}" for x in m["removed"][:30]] or ["(none)"]
    L += ["", "## Widest pack spread right now (p90 / p10 across providers)", "",
          "| model | providers | p10 | median | p90 | p90/p10 |", "|---|---|---|---|---|---|"]
    L += [f"| {k} | {v['n']} | {v['p10_blended_per_m']} | {v['median_blended_per_m']} | {v['p90_blended_per_m']} | {v['ratio_p90_p10']}x |"
          for k, v in top]
    (root / "MOVES.md").write_text("\n".join(L) + "\n")



def changes_since(day: str, root: Path = ROOT) -> list[dict]:
    """Every history line on or after YYYY-MM-DD, oldest first."""
    out: list[dict] = []
    for d in history_days(root):
        if d < day:
            continue
        with (root / "history" / f"{d}.jsonl").open() as f:
            out.extend(json.loads(line) for line in f if line.strip())
    return out


def _key(r: Record) -> tuple:
    # a provider can list one model several times (quantization, context tier);
    # keying on provider+model alone made those pairs flip every run and bloat history
    ex = r.extra or {}
    return (r.provider, r.model_raw, ex.get("quantization"), r.context)


def _price_tuple(r: Record) -> tuple:
    return (r.input_per_m, r.output_per_m, r.cached_input_per_m)


def load_latest(root: Path = ROOT) -> list[Record]:
    p = root / "latest.json"
    if not p.exists():
        return []
    return [Record.from_dict(d) for d in json.loads(p.read_text())["records"]]


def blended(r: Record) -> float:
    """input + 3 * output per M. A fixed ranking convention, stated wherever quoted."""
    return r.input_per_m + 3 * r.output_per_m


def spread(records: list[Record]) -> dict:
    """For each model served by 2+ distinct providers, the price dispersion across providers.

    Each provider is collapsed to its cheapest listing first, so a provider's own
    tiers (OpenAI priority/flex, say) do not register as a cross-provider spread.
    The router's own listing (provider "openrouter") is excluded, since it is a
    price for the same endpoints.

    ratio      = max / min across providers. Sensitive to one premium outlier.
    ratio_p90  = 90th percentile / min. Robust to a premium outlier, not to a cheap one.
    ratio_p90_p10 = p90 / p10. Trims one outlier at each end; the pack spread.
    median_x   = median / min. What a typical provider charges over the floor.
    """
    by: dict[str, dict[str, tuple[float, Record]]] = defaultdict(dict)
    for r in records:
        if r.provider == "openrouter":
            continue
        b = blended(r)
        cur = by[r.model].get(r.provider)
        if cur is None or b < cur[0]:
            by[r.model][r.provider] = (b, r)
    out = {}
    for model, per_provider in by.items():
        if len(per_provider) < 2:
            continue
        rows = sorted(per_provider.values(), key=lambda t: t[0])
        prices = [b for b, _ in rows]
        lo, hi = rows[0], rows[-1]
        n = len(prices)
        med = prices[n // 2] if n % 2 else (prices[n // 2 - 1] + prices[n // 2]) / 2
        p90 = prices[min(n - 1, int(round(0.9 * (n - 1))))]
        p10 = prices[max(0, int(round(0.1 * (n - 1))))]
        out[model] = {
            "n": n,
            "min_blended_per_m": round(lo[0], 4),
            "p10_blended_per_m": round(p10, 4),
            "median_blended_per_m": round(med, 4),
            "p90_blended_per_m": round(p90, 4),
            "max_blended_per_m": round(hi[0], 4),
            "ratio": round(hi[0] / lo[0], 2) if lo[0] > 0 else None,
            "ratio_p90": round(p90 / lo[0], 2) if lo[0] > 0 else None,
            "ratio_p90_p10": round(p90 / p10, 2) if p10 > 0 else None,  # trims one outlier at each end
            "median_x": round(med / lo[0], 2) if lo[0] > 0 else None,
            "cheapest": lo[1].provider,
            "dearest": hi[1].provider,
        }
    return out


def history_days(root: Path = ROOT) -> list[str]:
    h = root / "history"
    return sorted(p.stem for p in h.glob("*.jsonl")) if h.exists() else []


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
