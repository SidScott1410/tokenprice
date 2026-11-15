"""
First-party Google (Gemini API) list prices, provenance `page`.

The Gemini pricing page ships its Markdoc source inside the HTML, HTML-escaped.
After unescaping, each model is a section:

    ## Gemini 2.5 Pro  {% id="gemini-2.5-pro" %}
    ...
    {% tabs %}
      {% tab title="Standard" %}
      {% table %}
      * Feature
      * Free Tier
      * Paid Tier, per 1M tokens in USD
      ---
      * Input price
      * Free of charge
      * $1.25, prompts <= 200k tokens
      $2.50, prompts > 200k tokens
      ---
      * Output price (including thinking tokens)
      ...
      {% /table %}
      {% /tab %}
      {% tab title="Batch" %} ...

Only the Standard tab is a list price (Batch and Flex are documented 0.5x tiers).
Paid-tier cells come in four shapes, all handled here:

  plain      `$1.50`
  promo      `$2.00 through November 30, 2026.` / `$4.00 starting December 1, 2026.`
             -> the price in force at read_at; the other is kept in extra
  modality   `$0.30 (text / image / video)` / `$1.00 (audio)` -> the text price
  tiered     `$1.25, prompts <= 200k tokens` / `$2.50, prompts > 200k tokens`
             -> base record plus a `-long-context` record

Models whose text input or output price does not parse as $/1M tokens (TTS,
transcription, image output, embeddings, music, decision) are skipped.

Keys: "google/gemini-2.5-pro" -> gemini-2-5-pro, matching OpenRouter's id after normalize().
"""
from __future__ import annotations

import html
import re
from datetime import date, datetime, timezone
from urllib.request import Request, urlopen

from tokenprice.schema import Record, normalize

URL = "https://ai.google.dev/gemini-api/docs/pricing"
_HEAD = re.compile(r'^## (.+?)\s+\{% id="([^"]+)" %\}', re.M)
_STD_TAB = re.compile(r'\{% tab title="Standard" %\}(.*?)\{% /tab %\}', re.S)
_TABLE = re.compile(r"\{% table %\}(.*?)\{% /table %\}", re.S)
_PRICE = re.compile(r"\$\s*([0-9]+(?:\.[0-9]+)?)")
_DATE = re.compile(r"(January|February|March|April|May|June|July|August|September|October|November|December)"
                   r"\s+(\d{1,2}),\s+(\d{4})")
_MONTHS = {m: i for i, m in enumerate(["January", "February", "March", "April", "May", "June", "July", "August",
                                        "September", "October", "November", "December"], 1)}
_SKIP = ("tts", "transcribe", "image", "embedding", "lyria", "decision", "banana", "live")


def fetch(timeout: int = 30) -> str:
    req = Request(URL, headers={"User-Agent": "Mozilla/5.0 tokenprice/0.1"})
    with urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def _to_date(m: re.Match) -> date:
    return date(int(m.group(3)), _MONTHS[m.group(1)], int(m.group(2)))


def _segments(cell: str) -> list[str]:
    """Split a Paid-tier cell into its price segments (one per line, continuation-joined)."""
    cell = re.sub(r"\{%.*?%\}", "", cell)  # drop markdoc tags (sup, etc.)
    cell = cell.replace("\\", " ")  # markdoc hard-break continuations
    return [s.strip() for s in cell.splitlines() if "$" in s]


def _pick_text(segs: list[str]) -> list[str]:
    """Prefer segments that say (text ...) when modality parentheticals are present."""
    if not segs:
        return []
    tagged = [s for s in segs if re.search(r"\((text|input)", s, re.I)]
    if tagged:
        return tagged
    if any(re.search(r"\((audio|video|image)", s, re.I) for s in segs):
        return []  # only non-text modalities priced
    return segs


def _in_force(segs: list[str], today: date) -> tuple[float | None, dict]:
    """Resolve promo (through/starting) segments to the price in force on `today`."""
    extra: dict = {}
    current, future = None, None
    for s in segs:
        if "/min" in s or "per image" in s.lower() or "per 1k" in s.lower():
            continue
        pm = _PRICE.search(s)
        if not pm:
            continue
        price = float(pm.group(1))
        dm = _DATE.search(s)
        low = s.lower()
        if dm and "through" in low:
            if today <= _to_date(dm):
                current = price
                extra["promo_until"] = _to_date(dm).isoformat()
            continue
        if dm and "starting" in low:
            if today >= _to_date(dm):
                current = current if current is not None else price
            else:
                future = price
                extra["price_after_promo"] = price
                extra["price_after_from"] = _to_date(dm).isoformat()
            continue
        if current is None:
            current = price
    if current is None and future is not None:
        current = future
    return current, extra


def _split_tiers(segs: list[str]) -> tuple[list[str], list[str]]:
    base = [s for s in segs if not re.search(r">\s*200k|prompts\s*>", s, re.I)]
    long = [s for s in segs if re.search(r">\s*200k|prompts\s*>", s, re.I)]
    return base, long


def _row(table: str, label: str) -> str | None:
    for row in table.split("---"):
        cells = [c.strip() for c in re.split(r"^\s*\* ", row, flags=re.M) if c.strip()]
        if cells and cells[0].lower().startswith(label):
            return cells[-1]
    return None


def parse(page: str, read_at: str | None = None) -> list[Record]:
    read_at = read_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    today = date.fromisoformat(read_at[:10])
    src = html.unescape(page)
    out: list[Record] = []
    heads = list(_HEAD.finditer(src))
    for i, h in enumerate(heads):
        name, slug = h.group(1).strip(), h.group(2).strip()
        if any(k in slug for k in _SKIP):
            continue
        body = src[h.end(): heads[i + 1].start() if i + 1 < len(heads) else len(src)]
        tab = _STD_TAB.search(body)
        scope = tab.group(1) if tab else body
        tm = _TABLE.search(scope)
        if not tm:
            continue
        table = tm.group(1)
        inp_cell, out_cell = _row(table, "input price"), _row(table, "output price")
        if not inp_cell or not out_cell:
            continue
        inp_segs, out_segs = _pick_text(_segments(inp_cell)), _pick_text(_segments(out_cell))
        inp_base, inp_long = _split_tiers(inp_segs)
        out_base, out_long = _split_tiers(out_segs)
        inp, x1 = _in_force(inp_base, today)
        outp, x2 = _in_force(out_base, today)
        if inp is None or outp is None:
            continue
        cache_cell = _row(table, "context caching price")
        cached, _ = _in_force(_split_tiers(_pick_text(_segments(cache_cell)))[0], today) if cache_cell else (None, {})
        display = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", name)
        variants = [("google/" + slug, inp, outp, cached, "base", {**x1, **x2})]
        if inp_long and out_long:
            li, lx = _in_force(inp_long, today)
            lo, _ = _in_force(out_long, today)
            if li is not None and lo is not None:
                variants.append(("google/" + slug + "-long-context", li, lo, None, "long-context", lx))
        for raw, i_, o_, c_, tier, px in variants:
            try:
                out.append(Record(provider="google", model=normalize(raw), model_raw=raw, input_per_m=i_,
                                  output_per_m=o_, cached_input_per_m=c_, source=URL, read_at=read_at,
                                  provenance="page", extra={"display_name": display, "tier": tier,
                                                           "price_tier": "standard", **px}))
            except ValueError:
                continue
    return out


def scrape() -> list[Record]:
    return parse(fetch())
