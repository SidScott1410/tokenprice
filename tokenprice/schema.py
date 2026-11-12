"""
One price record per (provider, model) per read.

    {
      "provider": "openrouter/together",   # venue, then the upstream provider if the venue reports it
      "model": "llama-3-8b-instruct",      # normalized id, see normalize()
      "model_raw": "meta-llama/llama-3-8b-instruct",
      "input_per_m": 0.05,                 # USD per 1M input tokens
      "output_per_m": 0.08,
      "cached_input_per_m": null,
      "context": 8192,
      "source": "https://openrouter.ai/api/v1/models",
      "read_at": "2026-11-10T22:00:00Z",
      "provenance": "api"                  # api | page | manual
    }

Provenance is a required field. `api` means a machine-readable endpoint,
`page` means scraped HTML (fragile, flagged), `manual` means a human typed it
from a price page and recorded the date. Nothing is written without one.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

PROVENANCE = ("api", "page", "manual")

_DATE_SUFFIX = re.compile(r"[-_:]?\d{8}$|[-_:]?\d{4}-\d{2}-\d{2}$|:free$|:extended$|:nitro$")


def normalize(model: str) -> str:
    m = model.strip().lower()
    if "/" in m:
        m = m.rsplit("/", 1)[1]
    m = _DATE_SUFFIX.sub("", m)
    # 'claude-sonnet-4.5' (OpenRouter) and 'claude-sonnet-4-5' (Anthropic) are one model
    return m.replace("_", "-").replace(".", "-")


@dataclass
class Record:
    provider: str
    model: str
    model_raw: str
    input_per_m: float
    output_per_m: float
    source: str
    read_at: str
    provenance: str
    cached_input_per_m: float | None = None
    context: int | None = None
    extra: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.provenance not in PROVENANCE:
            raise ValueError(f"provenance must be one of {PROVENANCE}, got {self.provenance!r}")
        if self.input_per_m < 0 or self.output_per_m < 0:
            raise ValueError("negative price")
        if not self.source.startswith("http"):
            raise ValueError("source must be a URL")

    def to_dict(self) -> dict:
        d = asdict(self)
        if not d["extra"]:
            d.pop("extra")
        return d

    @classmethod
    def from_dict(cls, d: dict) -> Record:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})
