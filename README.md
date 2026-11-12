# tokenprice

Live token prices across providers, with provenance. A git-backed feed updated hourly by GitHub Actions, plus a one-call Python API and CLI.

![feed](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2FSidScott1410%2Ftokenprice%2Fmain%2Fprices%2Fsummary.json&query=%24.records&label=listings&color=blue)
![updated](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2FSidScott1410%2Ftokenprice%2Fmain%2Fprices%2Fsummary.json&query=%24.read_at&label=as%20of&color=green)

## Why

Every price in the feed carries three fields you cannot omit: the URL it was read from, when it was read, and how (`api`, `page`, or `manual`). A number without those is not a price, it is a rumor. Records that fail validation are refused at construction time, so the feed cannot contain an invented price.

The feed also answers a question no single provider page does: for the same open-weight model, how far apart are the cheapest and dearest listings right now? That ratio (`spread.json`) is the arbitrage that an inference buyer or a dispatcher should be capturing.

## Install

```
pip install git+https://github.com/SidScott1410/tokenprice
```

No runtime dependencies. Python 3.10+.

## Use

```python
import tokenprice

tokenprice.refresh()                       # pull latest.json from GitHub (optional; ships with a snapshot)
r = tokenprice.get("llama-3-8b-instruct")  # cheapest listing, a Record
r.input_per_m, r.output_per_m, r.source, r.read_at, r.provenance

tokenprice.cheapest("llama-3-8b-instruct", n=3)
tokenprice.spread("llama-3-8b-instruct")   # {"n", "min_blended_per_m", "max_blended_per_m", "ratio", "cheapest", "dearest"}
tokenprice.models()
```

```
tokenprice llama-3-8b-instruct            # table, cheapest first
tokenprice llama-3-8b-instruct --spread   # min, max, ratio across providers
tokenprice --models
tokenprice --refresh claude-sonnet-4-5 --json
tokenprice --since 2026-11-01             # every recorded price change since that day
```

Model names are normalized: provider prefix, date suffix, and OpenRouter variant tags (`:free`, `:extended`) are stripped, underscores become dashes. `anthropic/claude-sonnet-4-5-20250929` and `claude-sonnet-4-5` resolve to the same key. The raw listing id is kept in `model_raw`.

## Conventions

- Prices are USD per million tokens.
- Blended price (used for ranking and spread) is `input + 3 * output` per M, a 1:3 input:output mix. It is a ranking convention, not your bill.
- Free tiers (price 0) are dropped. They are not prices.
- `spread` requires at least two distinct upstream providers for a model.
- A full update is ~1 request per model plus one for the list, paced at 150 ms, so the hourly job takes a few minutes.

## Feed layout

```
prices/latest.json             most recent scrape, all records
prices/history/YYYY-MM-DD.jsonl  records whose price changed that day (unchanged runs write nothing)
prices/spread.json             per-model min/max/ratio
prices/summary.json            counts and the top spread, for badges
```

The feed is populated by the Action on first run. There is no hand-entered seed data.

## Sources

| scraper | provenance | what it covers |
|---|---|---|
| `tokenprice/scrapers/openrouter.py` | `api` | one router price per model from `/api/v1/models` (provider `openrouter`) |
| `tokenprice/scrapers/openrouter_endpoints.py` | `api` | per-provider prices from `/api/v1/models/{id}/endpoints`; this is where the spread comes from |

The router listing is kept so every model has at least one price; it is excluded from spread, which is computed over distinct upstream providers only.

Adding a scraper: write `scrape() -> list[Record]` in `tokenprice/scrapers/<name>.py`, call it from `cli._update`. First-party pages (OpenAI, Anthropic, Google) are client-rendered or change layout often; a `page` scraper for them is welcome but must set `provenance="page"` and keep the exact URL.

## Related

- [agent-cost](https://github.com/SidScott1410/agent-cost): prices an agent run step by step and uses this feed when installed.
- [reckon](https://github.com/reckonresearch/reckon): measured served-token cost on real silicon, the other half of the price question.

## License

Apache-2.0
