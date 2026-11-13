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
_PRICE = re.compile(r"\$\s*([0-9]+(?:\.[0-9]+)?)\s*/\s*MTok")
_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")


def fetch(timeout: int = 30) -> str:
    req = Request(URL, headers={"User-Agent": "tokenprice/0.1", "Accept": "text/markdown, text/plain, */*"})
    with urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def parse(markdown: str, read_at: str | None = None) -> list[Record]:
    """Header-aware: columns are located by name, rows must match the header's width.

    Only tables whose header has a "Base Input" column are model-price tables; the
    batch table (Batch input / Batch output) and the tool-use token table are skipped.
    Tiered rows ("for prompts over 100,000 tokens") get a `-long-context` key so the
    base tier is the model's list price.
    """
    read_at = read_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out: list[Record] = []
    idx: dict[str, int] | None = None
    for line in markdown.splitlines():
        if not line.lstrip().startswith("|"):
            idx = None
            continue
        cells = _cells(line)
        low = [c.lower() for c in cells]
        if cells and low[0] == "model":
            idx = None
            if any("base input" in c for c in low):
                idx = {}
                for i, c in enumerate(low):
                    if "base input" in c:
                        idx["input"] = i
                    elif c.startswith("output"):
                        idx["output"] = i
                    elif "cache hit" in c:
                        idx["cached"] = i
                    elif "5m cache write" in c:
                        idx["cw5"] = i
                    elif "1h cache write" in c:
                        idx["cw1h"] = i
                idx["width"] = len(cells)
            continue
        if idx is None or set(cells[0]) <= {"-", ":"} or len(cells) != idx["width"]:
            continue
        if not cells[0].startswith("Claude"):
            continue

        def price(key: str, _idx: dict = idx, _cells: list = cells) -> float | None:
            i = _idx.get(key)
            if i is None:
                return None
            m = _PRICE.search(_cells[i])
            return float(m.group(1)) if m else None

        inp, outp = price("input"), price("output")
        if inp is None or outp is None:
            continue
        name = _LINK.sub(r"\1", cells[0])
        flag = None
        pm = re.search(r"\(([^)]*)\)", name)
        if pm:
            flag = pm.group(1).strip()
            name = name[: pm.start()].strip()
        model_raw = "anthropic/" + name.lower().replace("claude ", "claude-").replace(" ", "-")
        tier = None
        if flag and "prompts over" in flag.lower():
            tier = "long-context"
            model_raw += "-long-context"
        elif flag and "prompts up to" in flag.lower():
            tier = "base"
        try:
            out.append(
                Record(
                    provider="anthropic",
                    model=normalize(model_raw),
                    model_raw=model_raw,
                    input_per_m=inp,
                    output_per_m=outp,
                    cached_input_per_m=price("cached"),
                    source=URL,
                    read_at=read_at,
                    provenance="page",
                    extra={"display_name": name, "cache_write_5m_per_m": price("cw5"),
                           "cache_write_1h_per_m": price("cw1h"),
                           "status": None if tier else flag, "tier": tier,
                           "tier_note": flag if tier else None},
                )
            )
        except ValueError:
            continue
    return out


def scrape() -> list[Record]:
    return parse(fetch())
