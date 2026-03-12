---
name: arxiv-bot-gemini
description: Build or extend the Axon arXiv research digest bot. Covers project architecture, Gemini API setup (new google-genai SDK, JSON mode, rate limiting), uv project management, CLI with Typer, APScheduler configuration, and venue filtering. Use when working on axon, adding new modules, debugging Gemini API issues, or extending the pipeline.
---

# Axon — ArXiv Research Digest Bot

## Project Layout

```
axon/
├── config.toml                # All user-tunable settings
├── src/axon/
│   ├── models.py              # Paper, PaperAnalysis, Digest dataclasses
│   ├── pipeline.py            # Orchestrates all 5 stages
│   ├── cli.py                 # Typer CLI: run / serve / fetch-only
│   ├── scheduler.py           # APScheduler blocking scheduler
│   ├── llm/
│   │   ├── base.py            # LLMProvider ABC
│   │   ├── gemini.py          # google-genai SDK adapter
│   │   └── ollama.py          # Local Ollama adapter
│   └── modules/
│       ├── fetcher.py         # arXiv API → Paper list
│       ├── filter.py          # Venue scoring + discard
│       ├── analyzer.py        # LLM per-paper analysis
│       ├── digest.py          # Group, rank, daily summary
│       └── delivery.py        # Jinja2 → Markdown output
├── data/
│   ├── venue_list.toml        # Tier1/Tier2 conference patterns
│   └── seen_ids.txt           # Dedup: already-processed IDs
├── prompts/
│   ├── paper_analysis.txt     # Per-paper LLM prompt template
│   └── daily_summary.txt      # Digest-level LLM prompt template
└── outputs/YYYY-MM-DD.md      # Generated digests
```

## CLI Commands

```bash
uv run axon run              # Full pipeline (manual trigger)
uv run axon fetch-only       # Fetch + filter only (no LLM, debug)
uv run axon serve            # Start cron scheduler daemon
uv run axon run --config path/to/other.toml   # Custom config
```

## Key config.toml Sections

```toml
[scheduler]
cron = "0 8 * * *"        # Standard cron expression
timezone = "Asia/Tokyo"

[llm]
provider = "gemini"        # "gemini" or "ollama"
model = "gemini-2.0-flash" # Use 2.0-flash for high free quota (1500 RPD)
api_key_env = "GEMINI_API_KEY"   # env var name, OR paste key directly
batch_size = 5

[filter]
min_venue_score = 0   # 0=all, 1=workshop, 2=tier1, 3=oral/best-paper
                      # Set to 0 for fresh/recent papers (no venue signal yet)
```

## Gemini API Critical Notes

### Use `google-genai`, NOT `google-generativeai`
The old SDK (`google-generativeai`) uses gRPC which fails in some regions (Japan etc.).
Always use the new REST-based SDK:
```bash
uv add google-genai
# NOT: uv add google-generativeai
```

### Force JSON output with response_mime_type
Avoids JSON parse failures and saves quota on retries:
```python
from google.genai import types

json_config = types.GenerateContentConfig(
    max_output_tokens=1024,
    temperature=0.2,
    response_mime_type="application/json",  # key: no markdown fences
)
response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents=prompt,
    config=json_config,
)
```

### Model Selection & Free Quota

| Model | Free RPD | Free RPM | Notes |
|-------|----------|----------|-------|
| `gemini-2.0-flash` | 1500 | 15 | Best choice for this bot |
| `gemini-2.5-flash-lite` | 1500 | 15 | Used if 2.0-flash unavailable |
| `gemini-3-flash-preview` | 20 | 5 | Too low for production use |
| `gemini-1.5-pro` | 50 | 2 | For higher quality if needed |

### Rate Limiting: add delays between calls
Free tier is 15 RPM. With ~10 papers/day, sleep ~13s between calls:
```python
# In analyzer.py between papers
if j < len(batch) - 1:
    time.sleep(13)
```

### api_key_env supports both env var name and literal key
The GeminiProvider constructor handles both:
```python
api_key = os.environ.get(api_key_env, "") or api_key_env
```
So `api_key_env = "GEMINI_API_KEY"` looks up an env var,
but `api_key_env = "AIzaSy..."` uses the literal key directly.

## LLM Provider Pattern

To add a new provider, implement `LLMProvider` and register it in `llm/__init__.py`:

```python
# llm/base.py
class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> str: ...
    @abstractmethod
    def generate_json(self, prompt: str) -> dict: ...

# llm/__init__.py — factory
def create_provider(config: dict) -> LLMProvider:
    name = config["llm"]["provider"]
    if name == "gemini": return GeminiProvider(config)
    if name == "ollama": return OllamaProvider(config)
    raise ValueError(f"Unknown provider: {name}")
```

## Venue Filter Scoring

| Score | Meaning | Example |
|-------|---------|---------|
| 3 | Oral / best paper at tier-1 | "oral at NeurIPS" |
| 2 | Accepted at tier-1 | "ICML 2025" |
| 1 | Workshop or tier-2 | "workshop at NeurIPS" |
| 0 | No venue signal | preprint only |

Patterns are matched against `paper.comments` and `paper.journal_ref`.
Add venues to `data/venue_list.toml` under `[[tier1]]` or `[[tier2]]`.

## Adding a New Topic

Only config change needed — no code changes:
```toml
[[topics]]
name = "Tool-Augmented Agents"
keywords = ["tool use", "function calling", "API agent", "code agent"]
```

## Common Debugging

**All papers filtered out?** — Recent arXiv papers have no venue signal yet.
Set `min_venue_score = 0` temporarily to test the full pipeline.

**Want to re-analyze today's papers?** — Clear `data/seen_ids.txt`:
```bash
: > data/seen_ids.txt
```

**Check what would be fetched without LLM calls:**
```bash
uv run axon fetch-only -v
```
