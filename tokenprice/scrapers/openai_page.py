"""
First-party OpenAI list prices, provenance `page`.

OpenAI serves its pricing page as markdown by appending `.md` to the docs URL.
The page holds several tier blocks, each introduced by a heading of the form
`### <Tier> pricing data` (Standard, then a discounted tier at half price).
Only the Standard tier is a list price; the others are skipped so that
`feed.markup()` compares resellers against list, not against batch.

Two table shapes appear under each tier:

    | Model | Short context input | Short context output | Short context cached input | ...
      | Long context input | Long context output | Long context cached input | ... |
    | Model | Input | Output | Cached input |

Rows with a long-context column set yield a second record keyed `-long-context`,
so the short-context row is the model's list price. A parenthetical on the model
name ("(<272K context length)") is recorded in extra and stripped from the key.

Keys: "gpt-6.1-sol" -> gpt-6-1-sol, which matches OpenRouter's openai/gpt-6.1-sol
after normalize().
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from urllib.request import Request, urlopen

from tokenprice.schema import Record, normalize

URL = "https://developers.openai.com/api/docs/pricing.md"
_PRICE = re.compile(r"\$\s*([0-9]+(?:\.[0-9]+)?)")
_TIER = re.compile(r"^#+\s*(\w+)\s+pricing data", re.IGNORECASE)
LIST_TIER = "standard"


def fetch(timeout: int = 30) -> str:
    req = Request(URL, headers={"User-Agent": "tokenprice/0.1", "Accept": "text/markdown, text/plain, */*"})
    with urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _price(cells: list[str], i: int | None) -> float | None:
    if i is None or i >= len(cells):
        return None
    m = _PRICE.search(cells[i])
    return float(m.group(1)) if m else None


def _columns(low: list[str]) -> dict[str, int]:
    """Map logical columns to indices. Short-context columns are the list price."""
    idx: dict[str, int] = {}
    for i, c in enumerate(low):
        if c in ("input", "short context input"):
            idx["input"] = i
        elif c in ("output", "short context output"):
            idx["output"] = i
        elif c in ("cached input", "short context cached input"):
            idx["cached"] = i
        elif c == "long context input":
            idx["lc_input"] = i
        elif c == "long context output":
            idx["lc_output"] = i
        elif c == "long context cached input":
            idx["lc_cached"] = i
    idx["width"] = len(low)
    return idx


def parse(markdown: str, read_at: str | None = None) -> list[Record]:
    read_at = read_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out: list[Record] = []
    tier: str | None = None
    idx: dict[str, int] | None = None
    for line in markdown.splitlines():
        if line.lstrip().startswith("#"):
            tm = _TIER.match(line.strip())
            tier = tm.group(1).lower() if tm else None  # unknown heading: never inherit a tier
            idx = None
            continue
        if not line.lstrip().startswith("|"):
            idx = None
            continue
        cells = _cells(line)
        low = [c.lower() for c in cells]
        if cells and low[0] == "model":
            idx = _columns(low) if ("input" in idx_keys(low) and "output" in idx_keys(low)) else None
            continue
        if idx is None or tier != LIST_TIER or set(cells[0]) <= {"-", ":"} or len(cells) != idx["width"]:
            continue
        name = cells[0]
        note = None
        pm = re.search(r"\(([^)]*)\)", name)
        if pm:
            note = pm.group(1).strip()
            name = name[: pm.start()].strip()
        if not name or " " in name:
            continue  # not a model id
        inp, outp = _price(cells, idx.get("input")), _price(cells, idx.get("output"))
        if inp is None or outp is None:
            continue
        base_raw = "openai/" + name
        variants = [(base_raw, inp, outp, _price(cells, idx.get("cached")), None)]
        lc_in, lc_out = _price(cells, idx.get("lc_input")), _price(cells, idx.get("lc_output"))
        if lc_in is not None and lc_out is not None:
            lc_c = _price(cells, idx.get("lc_cached"))
            variants.append((base_raw + "-long-context", lc_in, lc_out, lc_c, "long-context"))
        for raw, i_, o_, c_, t_ in variants:
            try:
                out.append(
                    Record(
                        provider="openai",
                        model=normalize(raw),
                        model_raw=raw,
                        input_per_m=i_,
                        output_per_m=o_,
                        cached_input_per_m=c_,
                        source=URL,
                        read_at=read_at,
                        provenance="page",
                        extra={"display_name": name, "tier": t_ or "base", "tier_note": note,
                               "price_tier": tier},
                    )
                )
            except ValueError:
                continue
    return out


def idx_keys(low: list[str]) -> set[str]:
    return set(_columns(low))


def scrape() -> list[Record]:
    return parse(fetch())
