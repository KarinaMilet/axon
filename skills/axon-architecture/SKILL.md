---
name: axon-architecture
description: Guide for extending the Axon research assistant. Use when adding new delivery backends (telegram, gmail), new analysis task types, new CLI commands, or any new module to the Orchestrator. Contains the architectural patterns, data flow contracts, and extension recipes for this codebase.
---

# Axon Architecture Guide

## Architecture Overview

Axon uses a three-layer pipeline coordinated by a central `Orchestrator`:

```
CLI → Orchestrator → crawler/ → analysis/ → delivery/
                          ↓           ↓           ↓
                    list[Paper]    Digest     str (path/status)
```

Each layer is a standalone Python package with a clean contract. The Orchestrator wires them together — layers do not import each other directly.

## Layer Contracts

| Layer | Package | Input | Output | Entry point |
|-------|---------|-------|--------|-------------|
| Crawl | `axon.crawler` | `config` | `(list[Paper], int)` | `fetch(config)` |
| Analyse | `axon.analysis` | `list[Paper], config, int` | `Digest` | `run_analysis(papers, config, total)` |
| Deliver | `axon.delivery` | `Digest, config` | `list[str]` | `deliver_all(digest, config)` |

`int` in crawler output is `total_fetched` (before filter), passed through to `Digest` for reporting.

## Adding a New Delivery Backend

The `delivery/` layer mirrors the `llm/` pluggable backend pattern.

**1. Create `src/axon/delivery/your_backend.py`:**

```python
from axon.delivery.base import DeliveryBackend
from axon.models import Digest

class YourBackend(DeliveryBackend):
    def __init__(self, config: dict):
        # read your section from config, e.g. config["your_backend"]
        ...

    def deliver(self, digest: Digest) -> str:
        # send/write the digest, return a status string
        ...
```

**2. Register in `src/axon/delivery/__init__.py`:**

```python
elif fmt == "your_backend":
    from axon.delivery.your_backend import YourBackend
    backends.append(YourBackend(config))
```

**3. Enable in `config.toml`:**

```toml
[delivery]
formats = ["markdown", "your_backend"]

[your_backend]
# backend-specific config
```

Multiple backends run in parallel — `deliver_all()` calls each one in sequence.

## Adding a New Orchestrator Task

Tasks are registered in `Orchestrator._registry`. To add a new task (e.g. topic-focused analysis):

**1. Add a method to `src/axon/orchestrator.py`:**

```python
def _topic_analyze(self, **kwargs) -> None:
    from axon.crawler import fetch
    from axon.analysis.topic import run_topic_analysis   # your new module
    from axon.delivery import deliver_all

    papers, total = fetch(self.config)
    digest = run_topic_analysis(papers, self.config, total, **kwargs)
    deliver_all(digest, self.config)
```

**2. Register it in `_registry`:**

```python
@property
def _registry(self) -> dict[str, Callable]:
    return {
        "daily": self._daily,
        "fetch": self._fetch,
        "topic_analyze": self._topic_analyze,   # add here
    }
```

**3. Expose via CLI in `src/axon/cli.py`:**

```python
@app.command()
def topic(config: str = ..., verbose: bool = ...):
    """Analyse papers by topic."""
    orch = Orchestrator(_load_config(config))
    orch.run("topic_analyze")
```

Key point: new tasks should reuse `crawler.fetch()` rather than reimplementing data acquisition.

## CLI Design Rules

- All commands go through `Orchestrator` — never import crawler/analysis/delivery directly in `cli.py`
- Aliases: define a real command, then have the alias call it (`crawler` calls `daily`)
- Lazy imports inside command handlers keep startup time fast

## Data Model Reference

Core models live in `src/axon/models.py` (never modified by analysis or delivery layers):

- `Paper` — raw arxiv result + `venue_score`, `matched_topics`
- `PaperAnalysis` — LLM output per paper (scores, summary, topics)
- `PaperEntry` — `Paper` + `PaperAnalysis` combined, exposes `avg_score`
- `Digest` — final output: date, overview, trends, topic-grouped entries, recommendations

## Key Config Sections

```toml
[[topics]]               # add topics freely, crawler uses keywords + arxiv categories
name = "..."
keywords = [...]

[filter]
min_venue_score = 2      # 0=unvetted 1=workshop 2=top-venue 3=oral; set 0 to pass all

[delivery]
formats = ["markdown"]   # list of enabled backends

[llm]
provider = "gemini"      # "gemini" | "ollama"
batch_size = 5           # papers per LLM batch
```

## seen_ids.txt

`data/seen_ids.txt` records all fetched arxiv IDs to avoid duplicates across runs.
Clear it to re-fetch previously seen papers (useful for testing or backfills):

```bash
echo -n "" > data/seen_ids.txt
```
