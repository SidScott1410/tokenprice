"""
SVG dot plot of seller prices per model, written by the feed each run.

No dependencies: the file is assembled as text. One row per model (the
models with the most distinct sellers), one dot per seller on a log price
axis, with the median marked. Dark-mode safe via currentColor and a muted
palette; GitHub renders it inline from README.
"""
from __future__ import annotations

import math
from collections import defaultdict
from pathlib import Path

from tokenprice.feed import blended
from tokenprice.schema import Record

W, ROW, PAD_L, PAD_R, PAD_T = 920, 26, 260, 48, 56


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def dot_plot(records: list[Record], rows: int = 15, read_at: str = "") -> str:
    per: dict[str, dict[str, float]] = defaultdict(dict)
    for r in records:
        if r.provider == "openrouter":
            continue
        b = blended(r)
        if b <= 0:
            continue
        cur = per[r.model].get(r.provider)
        if cur is None or b < cur:
            per[r.model][r.provider] = b
    models = sorted((m for m in per if len(per[m]) >= 3), key=lambda m: -len(per[m]))[:rows]
    if not models:
        return _empty(read_at)
    allp = [p for m in models for p in per[m].values()]
    lo, hi = min(allp), max(allp)
    lo10, hi10 = math.floor(math.log10(lo)), math.ceil(math.log10(hi))
    if hi10 == lo10:
        hi10 += 1
    plot_w = W - PAD_L - PAD_R
    X = lambda p: PAD_L + (math.log10(p) - lo10) / (hi10 - lo10) * plot_w  # noqa: E731
    H = PAD_T + ROW * len(models) + 34

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
           f'font-family="system-ui,sans-serif" font-size="12" fill="currentColor" color="#333">',
           '<style>@media(prefers-color-scheme:dark){svg{color:#ddd}}</style>',
           f'<text x="{PAD_L}" y="20" font-size="15" font-weight="600">Same model, different sellers</text>',
           f'<text x="{PAD_L}" y="38" opacity=".65">Blended USD per M tokens (input + 3 × output), log scale. '
           f'Dot = seller at its cheapest tier, bar = median, right = dearest / cheapest.</text>',
           f'<text x="{W - PAD_R}" y="20" text-anchor="end" opacity=".5">{_esc(read_at)}</text>',
           '<text x="14" y="38" opacity=".5">sellers</text>']
    for e in range(lo10, hi10 + 1):
        x = X(10 ** e)
        out.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{PAD_T - 6}" y2="{H - 26}" stroke="currentColor" stroke-opacity=".12"/>')
        out.append(f'<text x="{x:.1f}" y="{H - 10}" text-anchor="middle" opacity=".65">${10 ** e:g}</text>')
    for i, m in enumerate(models):
        y = PAD_T + ROW * i + ROW / 2
        prices = sorted(per[m].values())
        n = len(prices)
        med = prices[n // 2] if n % 2 else (prices[n // 2 - 1] + prices[n // 2]) / 2
        out.append(f'<line x1="{PAD_L}" x2="{W - PAD_R}" y1="{y:.1f}" y2="{y:.1f}" stroke="currentColor" stroke-opacity=".06"/>')
        out.append(f'<text x="{PAD_L - 10}" y="{y + 4:.1f}" text-anchor="end">{_esc(m)}</text>')
        out.append(f'<text x="30" y="{y + 4:.1f}" text-anchor="end" opacity=".5">{n}</text>')
        for p in prices:
            out.append(f'<circle cx="{X(p):.1f}" cy="{y:.1f}" r="4" fill="#3b6fd6" fill-opacity=".55"/>')
        out.append(f'<line x1="{X(med):.1f}" x2="{X(med):.1f}" y1="{y - 8:.1f}" y2="{y + 8:.1f}" stroke="#d6453b" stroke-width="2.5"/>')
        out.append(f'<text x="{X(prices[-1]) + 8:.1f}" y="{y + 4:.1f}" opacity=".65">{prices[-1] / prices[0]:.1f}x</text>')
    out.append("</svg>")
    return "\n".join(out)


def _empty(read_at: str) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="60" font-family="system-ui" font-size="13">'
            f'<text x="10" y="35">No model has 3+ sellers yet. {_esc(read_at)}</text></svg>')


def write_chart(records: list[Record], path: Path, read_at: str) -> None:
    path.write_text(dot_plot(records, read_at=read_at))
