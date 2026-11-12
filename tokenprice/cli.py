"""
    tokenprice llama-3-8b-instruct          # prices across providers, cheapest first
    tokenprice llama-3-8b-instruct --spread # min, max, ratio
    tokenprice --models                     # every model in the feed
    tokenprice --refresh                    # pull the latest feed from GitHub first
    tokenprice --since 2026-11-01           # price changes recorded since a date
    tokenprice --update                     # run the scrapers and write prices/ (what the Action does)
"""
from __future__ import annotations

import argparse
import json
import sys

import tokenprice
from tokenprice import feed


def _update() -> int:
    from tokenprice.scrapers import openrouter  # local import: scrapers are not part of the wheel

    records = openrouter.scrape()
    info = feed.write_run(records)
    print(json.dumps(info))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="tokenprice", description="Live token prices across providers.")
    ap.add_argument("model", nargs="?")
    ap.add_argument("--provider", default=None)
    ap.add_argument("--spread", action="store_true")
    ap.add_argument("--models", action="store_true")
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--update", action="store_true", help="run scrapers and write the feed (maintainers)")
    ap.add_argument("--since", metavar="YYYY-MM-DD", help="list price changes recorded since this day")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    if a.update:
        return _update()
    if a.refresh:
        n = tokenprice.refresh()
        print(f"refreshed: {n} records", file=sys.stderr)
    if a.since:
        rows = feed.changes_since(a.since)
        if a.model:
            rows = [r for r in rows if r["model"] == tokenprice.normalize(a.model)]
        if a.json:
            print(json.dumps(rows, indent=2))
        else:
            for r in rows:
                head = f"{r['read_at']}  {r['provider']:<14} {r['model_raw']:<44}"
                print(f"{head} in {r['input_per_m']:.4f}  out {r['output_per_m']:.4f}")
        return 0
    if a.models:
        print("\n".join(tokenprice.models()))
        return 0
    if not a.model:
        ap.print_help()
        return 2

    if a.spread:
        s = tokenprice.spread(a.model)
        if s is None:
            print(f"{a.model}: fewer than two providers in the feed", file=sys.stderr)
            return 1
        if a.json:
            print(json.dumps(s, indent=2))
        else:
            lo, hi = s["min_blended_per_m"], s["max_blended_per_m"]
            print(f"{a.model}: {s['n']} listings, blended ${lo:.3f} to ${hi:.3f} per M, ratio {s['ratio']}x")
            print(f"  cheapest {s['cheapest']}\n  dearest  {s['dearest']}")
        return 0

    rs = tokenprice.all_for(a.model)
    if a.provider:
        rs = [r for r in rs if r.provider == a.provider or r.model_raw.startswith(a.provider)]
    if not rs:
        print(f"{a.model}: not in the feed (try --models)", file=sys.stderr)
        return 1
    if a.json:
        print(json.dumps([r.to_dict() for r in rs], indent=2))
        return 0
    print(f"{'model_raw':<48} {'in $/M':>8} {'out $/M':>8} {'cached':>8}  read_at")
    for r in rs:
        c = f"{r.cached_input_per_m:.3f}" if r.cached_input_per_m is not None else "-"
        print(f"{r.model_raw:<48} {r.input_per_m:>8.3f} {r.output_per_m:>8.3f} {c:>8}  {r.read_at}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
