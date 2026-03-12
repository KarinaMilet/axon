# Axon

Your personal research assistant — fetches, filters, and summarizes daily papers using LLM-powered analysis, with a modular architecture designed for extensibility.

## Features

- **Automated ingestion** — Query arXiv by topic keywords
- **Venue-based filtering** — Score papers by conference/journal credibility
- **LLM summarization** — Per-paper analysis and daily digest via LLM
- **Topic-organized output** — Markdown digest with recommendations, trends, and grouped papers
- **Pluggable delivery** — Markdown output today, Telegram/Gmail/etc. tomorrow
- **CLI + scheduler** — Manual runs or cron-style daemon; all settings in TOML

## Quick Start

```bash
# Install (requires uv)
uv sync

# Set your Gemini API key
export API_KEY_GEMINI="your-api-key"

# Run full daily pipeline
uv run axon daily

# Or start the scheduler (runs daily at configured time)
uv run axon serve
```

## Commands

| Command | Description |
|---------|-------------|
| `axon daily` | Run full pipeline once (fetch -> filter -> analyze -> digest -> deliver) |
| `axon crawler` | Alias for `daily` |
| `axon fetch` | Fetch and filter only, no LLM calls (reusable data acquisition) |
| `axon serve` | Start cron daemon; schedule in `config.toml` |

## Configuration

Edit `config.toml` to adjust:

- **Topics** — Add keywords and topic names
- **arXiv** — Categories, lookback days, max results
- **Filter** — `min_venue_score` (0-3), venue list in `data/venue_list.toml`
- **LLM** — Provider (`gemini` / `ollama`), model, batch size
- **Delivery** — Output formats (e.g. `["markdown"]`), output directory
- **Scheduler** — Cron expression and timezone

## Project Structure

```
axon/
├── config.toml              # All settings
├── src/axon/
│   ├── cli.py               # Typer CLI
│   ├── orchestrator.py      # Central task dispatcher
│   ├── crawler/             # Data acquisition (fetcher + filter)
│   ├── analysis/            # LLM analysis (analyzer + digest)
│   ├── delivery/            # Pluggable output backends (markdown, ...)
│   └── llm/                 # Gemini + Ollama adapters
├── data/venue_list.toml     # Conference patterns
├── prompts/                 # LLM prompt templates
└── outputs/                 # Generated digests (YYYY-MM-DD.md)
```

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) for dependency management
- LLM API key

## License

MIT
