# Feed files

Written by `tokenprice --update` (the hourly GitHub Action). Nothing here is hand-entered.

- `latest.json`: the most recent full scrape. One record per provider listing.
- `history/YYYY-MM-DD.jsonl`: one line per (provider, model) whose price changed that day. Unchanged runs write nothing, so the file is a changelog, not a log.
- `spread.json`: per model, min and max blended price across providers and the ratio.

Blended price = input $/M + 3 x output $/M (a 1:3 input:output token mix). It is a ranking convention, not a cost estimate for your workload.
