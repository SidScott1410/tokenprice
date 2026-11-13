"""
First-party Anthropic list prices, provenance `page`.

Anthropic publishes its pricing page as markdown at a .md URL. The model table
has six pipe-separated columns:

    | Model | Base Input Tokens | 5m Cache Writes | 1h Cache Writes | Cache Hits & Refreshes | Output Tokens |

Rows look like `| Claude Sonnet 4.5 | $3 / MTok | $3.75 / MTok | $6 / MTok | $0.30 / MTok | $15 / MTok |`.
Deprecated rows carry a markdown link in the name; it is stripped and recorded in extra.

Keys: "Claude Sonnet 4.5" -> claude-sonnet-4-5, which matches OpenRouter's
anthropic/claude-sonnet-4.5 after normalize(). Pre-4 names ("Claude 3.7 Sonnet"
on OpenRouter vs "Claude Sonnet 3.7" here) do not line up; recorded as-is.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from urllib.request import Request, urlopen

from tokenprice.schema import Record, normalize

URL = "https://platform.claude.com/docs/en/about-claude/pricing.md"
_ROW = re.compile(r"^\|\s*(Claude[^|]+?)\s*\|((?:[^|]*\|){5})\s*$", re.M)
_PRICE = re.compile(r"\$\s*([0-9]+(?:\.[0-9]+)?)\s*/\s*MTok")
_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")


def fetch(timeout: int = 30) -> str:
    req = Request(URL, headers={"User-Agent": "tokenprice/0.1", "Accept": "text/markdown, text/plain, */*"})
    with urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def parse(markdown: str, read_at: str | None = None) -> list[Record]:
    read_at = read_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out: list[Record] = []
    for m in _ROW.finditer(markdown):
        raw_name, cells = m.group(1), m.group(2)
        cols = [c.strip() for c in cells.strip("|").split("|")]
        if len(cols) < 5:
            continue
        prices = []
        for c in cols[:5]:
            pm = _PRICE.search(c)
            prices.append(float(pm.group(1)) if pm else None)
        inp, cw5, cw1h, cached, outp = prices
        if inp is None or outp is None:
            continue
        name = _LINK.sub(r"\1", raw_name)
        flag = None
        pm = re.search(r"\(([^)]*)\)", name)
        if pm:
            flag = pm.group(1).strip()
            name = name[: pm.start()].strip()
        model_raw = "anthropic/" + name.lower().replace("claude ", "claude-").replace(" ", "-")
        try:
            out.append(
                Record(
                    provider="anthropic",
                    model=normalize(model_raw),
                    model_raw=model_raw,
                    input_per_m=inp,
                    output_per_m=outp,
                    cached_input_per_m=cached,
                    source=URL,
                    read_at=read_at,
                    provenance="page",
                    extra={"display_name": name, "cache_write_5m_per_m": cw5, "cache_write_1h_per_m": cw1h,
                           "status": flag},
                )
            )
        except ValueError:
            continue
    return out


def scrape() -> list[Record]:
    return parse(fetch())
