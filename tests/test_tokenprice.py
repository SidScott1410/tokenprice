import json

import pytest

import tokenprice
from tokenprice import feed
from tokenprice.schema import Record, normalize
from tokenprice.scrapers import openrouter, openrouter_endpoints

FIXTURE = {
    "data": [
        {"id": "meta-llama/llama-3-8b-instruct", "name": "Meta: Llama 3 8B Instruct", "context_length": 8192,
         "pricing": {"prompt": "0.00000005", "completion": "0.00000008"}},
        {"id": "meta-llama/llama-3-8b-instruct:free", "name": "free", "context_length": 8192,
         "pricing": {"prompt": "0", "completion": "0"}},
        {"id": "meta-llama/llama-3-8b-instruct:extended", "name": "ext", "context_length": 16384,
         "pricing": {"prompt": "0.0000002", "completion": "0.0000004"}},
        {"id": "anthropic/claude-sonnet-4.5", "name": "Claude", "context_length": 200000,
         "pricing": {"prompt": "0.000003", "completion": "0.000015", "input_cache_read": "0.0000003"}},
        {"id": "broken/model", "pricing": {"prompt": "n/a", "completion": "x"}},
    ]
}


ENDPOINTS = {
    "data": {
        "id": "meta-llama/llama-3-8b-instruct",
        "endpoints": [
            {"provider_name": "DeepInfra", "context_length": 8192, "quantization": "bf16",
             "pricing": {"prompt": "0.00000003", "completion": "0.00000006"}},
            {"provider_name": "Together", "context_length": 8192, "quantization": "fp8",
             "pricing": {"prompt": "0.00000018", "completion": "0.00000018"}},
            {"provider_name": "Broken", "pricing": {"prompt": "x", "completion": "y"}},
            {"name": "Free Tier", "pricing": {"prompt": "0", "completion": "0"}},
        ],
    }
}


def test_normalize():
    assert normalize("meta-llama/llama-3-8b-instruct:free") == "llama-3-8b-instruct"
    assert normalize("anthropic/claude-sonnet-4-5-20250929") == "claude-sonnet-4-5"
    assert normalize("anthropic/claude-sonnet-4.5") == "claude-sonnet-4-5"
    assert normalize("GPT_4o") == "gpt-4o"


def test_parse_endpoints():
    rs = openrouter_endpoints.parse(ENDPOINTS, "meta-llama/llama-3-8b-instruct", read_at="2026-11-10T22:00:00Z")
    assert [r.provider for r in rs] == ["deepinfra", "together"]
    assert rs[0].input_per_m == 0.03 and rs[0].source.endswith("/endpoints")
    assert rs[0].extra["quantization"] == "bf16"


def test_parse_openrouter():
    rs = openrouter.parse(FIXTURE, read_at="2026-11-10T22:00:00Z")
    assert len(rs) == 3                      # free tier and broken entry dropped
    a = rs[0]
    assert a.model == "llama-3-8b-instruct" and a.input_per_m == 0.05 and a.output_per_m == 0.08
    assert a.provenance == "api" and a.source.startswith("https://")
    c = [r for r in rs if r.model == "claude-sonnet-4-5"][0]
    assert c.cached_input_per_m == 0.3


def test_schema_refuses_bad_records():
    with pytest.raises(ValueError):
        Record("p", "m", "m", 1, 1, "https://x", "2026-01-01T00:00:00Z", "guess")
    with pytest.raises(ValueError):
        Record("p", "m", "m", 1, 1, "not-a-url", "2026-01-01T00:00:00Z", "manual")
    with pytest.raises(ValueError):
        Record("p", "m", "m", -1, 1, "https://x", "2026-01-01T00:00:00Z", "api")


def test_write_and_read_feed(tmp_path, monkeypatch):
    rs = openrouter.parse(FIXTURE, read_at="2026-11-10T22:00:00Z")
    rs += openrouter_endpoints.parse(ENDPOINTS, "meta-llama/llama-3-8b-instruct", read_at="2026-11-10T22:00:00Z")
    info = feed.write_run(rs, root=tmp_path)
    assert info["records"] == 5 and info["changed"] == 5 and info["day"] == "2026-11-10"
    assert (tmp_path / "history" / "2026-11-10.jsonl").read_text().count("\n") == 5
    sp = json.loads((tmp_path / "spread.json").read_text())["models"]
    # router listings (base and :extended) do not make a spread; two real providers do
    assert list(sp) == ["llama-3-8b-instruct"]
    s = sp["llama-3-8b-instruct"]
    # deepinfra 0.03+3*0.06=0.21 ; together 0.18+3*0.18=0.72 ; ratio 3.43
    assert s["n"] == 2 and s["ratio"] == 3.43 and s["cheapest"] == "deepinfra" and s["dearest"] == "together"

    # unchanged prices: latest rewritten, history untouched
    info = feed.write_run(rs, root=tmp_path, read_at="2026-11-10T23:00:00Z")
    assert info["changed"] == 0
    assert (tmp_path / "history" / "2026-11-10.jsonl").read_text().count("\n") == 5
    # one price moves: one history line
    rs[0].input_per_m = 0.06
    info = feed.write_run(rs, root=tmp_path, read_at="2026-11-11T00:00:00Z")
    assert info["changed"] == 1 and feed.history_days(tmp_path) == ["2026-11-10", "2026-11-11"]
    assert len(feed.changes_since("2026-11-11", tmp_path)) == 1
    assert len(feed.changes_since("2026-11-10", tmp_path)) == 6
    summ = json.loads((tmp_path / "summary.json").read_text())
    assert summ["top_spread_model"] == "llama-3-8b-instruct" and summ["providers"] == 3

    with pytest.raises(ValueError):
        feed.write_run([], root=tmp_path)

    # package API reads it
    monkeypatch.setattr(tokenprice, "_cache", None)
    monkeypatch.setattr(tokenprice, "ROOT", tmp_path)
    monkeypatch.setattr(feed, "ROOT", tmp_path)
    tokenprice._cache = feed.load_latest(tmp_path)
    assert tokenprice.get("llama-3-8b-instruct").provider == "deepinfra"
    assert tokenprice.get("llama-3-8b-instruct", provider="together").input_per_m == 0.18
    assert len(tokenprice.cheapest("llama-3-8b-instruct", n=10)) == 4
    assert tokenprice.spread("llama-3-8b-instruct")["ratio"] == 3.43
    assert tokenprice.get("nope") is None
    assert "claude-sonnet-4-5" in tokenprice.models()


def test_cli(tmp_path, monkeypatch, capsys):
    from tokenprice.cli import main
    rs = openrouter.parse(FIXTURE, read_at="2026-11-10T22:00:00Z")
    feed.write_run(rs, root=tmp_path)
    monkeypatch.setattr(tokenprice, "_cache", feed.load_latest(tmp_path))
    assert main(["llama-3-8b-instruct"]) == 0
    assert "0.050" in capsys.readouterr().out
    assert main(["llama-3-8b-instruct", "--spread"]) == 1  # router-only records: no provider spread
    rs += openrouter_endpoints.parse(ENDPOINTS, "meta-llama/llama-3-8b-instruct", read_at="2026-11-10T22:00:00Z")
    monkeypatch.setattr(tokenprice, "_cache", rs)
    assert main(["llama-3-8b-instruct", "--spread"]) == 0
    assert "3.43x" in capsys.readouterr().out
    assert main(["claude-sonnet-4-5", "--spread"]) == 1
    assert main(["nope"]) == 1
    assert main(["--models"]) == 0
