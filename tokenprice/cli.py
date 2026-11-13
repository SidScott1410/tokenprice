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
    from tokenprice.scrapers import anthropic_page, openrouter, openrouter_endpoints

    listed = openrouter.scrape()  # one router price per model
    ids = sorted({r.model_raw for r in listed})
    per_provider, failed = openrouter_endpoints.scrape_all(ids)  # the spread lives here
    first_party: list = []
    for name, mod in (("anthropic", anthropic_page),):
        try:  # first-party pages are best effort: a layout change must not take the feed down
            first_party += mod.scrape()
        except Exception as e:  # noqa: BLE001
            print(f"first-party scraper {name} failed: {e}", file=sys.stderr)
    info = feed.write_run(listed + per_provider + first_party)
    info["first_party_records"] = len(first_party)
    info["endpoint_models"] = len(ids)
    info["endpoint_records"] = len(per_provider)
    info["endpoint_models_failed"] = len(failed)
    if failed:
        print("endpoints failed for: " + ", ".join(failed[:10]) + (" ..." if len(failed) > 10 else ""), file=sys.stderr)
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
    ap.add_argument("--markup", action="store_true", help="router/reseller price over first-party list price")
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
    if a.markup:
        mk = feed.markup(tokenprice._records())
        if a.model:
            mk = {k: v for k, v in mk.items() if k == tokenprice.normalize(a.model)}
        if a.json:
            print(json.dumps(mk, indent=2))
            return 0
        for model, v in sorted(mk.items()):
            print(f"{model}: list ${v['list_blended_per_m']:.3f}/M ({v['list_provider']})")
            for s in v["sellers"]:
                print(f"  {s['provider']:<18} ${s['blended_per_m']:.3f}  {s['over_list']:.2f}x list")
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
            print(f"{a.model}: {s['n']} providers, blended ${lo:.3f} (min) ${s['median_blended_per_m']:.3f} (median) "
                  f"${s['p90_blended_per_m']:.3f} (p90) ${hi:.3f} (max) per M")
            print(f"  max/min {s['ratio']}x   p90/min {s['ratio_p90']}x   p90/p10 {s['ratio_p90_p10']}x   "
                  f"median/min {s['median_x']}x")
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
    hdr = f"{'provider':<18} {'quant':<6} {'ctx':>7} {'in $/M':>8} {'out $/M':>8} {'cached':>8} {'blended':>8}"
    print(f"{hdr}  model_raw")
    for r in rs:
        c = f"{r.cached_input_per_m:.3f}" if r.cached_input_per_m is not None else "-"
        q = (r.extra or {}).get("quantization") or "-"
        ctx = f"{r.context:,}" if r.context else "-"
        b = r.input_per_m + 3 * r.output_per_m
        row = f"{r.provider:<18} {q:<6} {ctx:>7} {r.input_per_m:>8.3f} {r.output_per_m:>8.3f} {c:>8} {b:>8.3f}"
        print(f"{row}  {r.model_raw}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
