# Feed files

Written by `tokenprice --update` (the hourly GitHub Action). Nothing here is hand-entered.

- `latest.json`, `latest.csv`: the current price set, one record per provider listing. Rewritten only when a price changes or a listing appears or vanishes.
- `history/YYYY-MM-DD.jsonl`: one line per listing whose price changed that day, plus `removed: true` lines for listings that vanished. A changelog, not a log.
- `spread.json`: per model, dispersion across distinct providers (min, p10, median, p90, max and ratios).
- `litellm.json`: the router listings in LiteLLM's `model_prices_and_context_window.json` shape, per-token USD.
- `summary.json`: counts, `read_at` (last change) and `checked_at` (last run). Badges read this.
- `MOVES.md`: last 7 days of cuts, rises, new and removed listings, regenerated every run.

Blended price = input $/M + 3 x output $/M (a 1:3 input:output token mix). It is a ranking convention, not a cost estimate for your workload.

Data license: CC BY 4.0. Attribute "tokenprice (Sidney Scott)" with the snapshot `read_at`.
