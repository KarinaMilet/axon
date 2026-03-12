# ArXiv Research Bot — Design Document

**Version:** 1.0  
**Status:** Draft  
**Target Audience:** Coding agents / developers implementing this system

---

## 1. Overview

A scheduled bot that daily fetches, filters, analyzes, and summarizes arXiv papers in the AI Agent domain. It produces a structured digest with topic-based categorization, paper summaries, and reading recommendations.

### Goals

- Automated daily arXiv ingestion focused on AI Agent research
- Quality filtering to retain only high-credibility papers
- LLM-powered summarization and categorization (via Gemini)
- Topic-organized output digest with reading recommendations
- Extensible topic/keyword configuration

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Scheduler (cron)                     │
│                     Runs daily at 08:00 UTC                 │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   1. Fetcher Module                         │
│   arXiv API → raw paper list (title, abstract, authors,    │
│   date, categories, comments, journal_ref)                  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   2. Filter Module                          │
│   Venue scoring → discard low-credibility papers            │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   3. Analyzer Module                        │
│   Gemini API → per-paper summary, topic tags, score        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   4. Digest Builder                         │
│   Group by topic → daily summary → recommendations         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   5. Output / Delivery                      │
│   Markdown file + (optional) email / Slack / Notion push   │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Directory Structure

```
arxiv-bot/
├── main.py                  # Entry point; orchestrates pipeline
├── config.toml              # All user-tunable settings
├── requirements.txt
│
├── modules/
│   ├── fetcher.py           # arXiv API client
│   ├── filter.py            # Venue & quality filtering
│   ├── analyzer.py          # Gemini API integration
│   ├── digest.py            # Grouping, summary, recommendation
│   └── delivery.py          # Output writing / notification
│
├── prompts/
│   ├── paper_analysis.txt   # Gemini prompt: per-paper analysis
│   └── daily_summary.txt    # Gemini prompt: digest-level summary
│
├── data/
│   ├── venue_list.toml      # Curated conference/journal list
│   └── seen_ids.txt         # Dedup: already-processed paper IDs
│
└── outputs/                 # Generated daily digests
    └── YYYY-MM-DD.md
```

---

## 4. Configuration (`config.toml`)

```toml
# ── Topic Configuration (extend freely) ──────────────────────
[[topics]]
name = "Agent Planning"
keywords = ["agent planning", "task decomposition", "chain-of-thought", "reasoning agent", "tool use"]

[[topics]]
name = "Memory System"
keywords = ["memory system", "episodic memory", "retrieval-augmented", "long-term memory", "working memory agent"]

[[topics]]
name = "Multi-Agent Orchestration"
keywords = ["multi-agent", "agent collaboration", "agent communication", "multi-agent system", "agent orchestration"]

# ── arXiv Search ──────────────────────────────────────────────
[arxiv]
categories = ["cs.AI", "cs.LG", "cs.CL", "cs.MA"]  # arXiv category codes to search
max_results_per_query = 100
lookback_days = 1  # Fetch papers submitted in last N days

# ── Quality Filter ────────────────────────────────────────────
[filter]
min_venue_score = 2     # 0=unvetted, 1=workshop, 2=top-venue, 3=oral/best-paper
require_venue_signal = false  # If true, drop papers with no venue signal at all

# ── LLM (Gemini) ──────────────────────────────────────────────
[llm]
provider = "gemini"
model = "gemini-1.5-pro"
api_key_env = "GEMINI_API_KEY"
max_tokens = 1024
temperature = 0.2
batch_size = 5  # Papers per Gemini batch call

# ── Recommendations ───────────────────────────────────────────
[recommendations]
top_n = 5               # Number of must-read picks per digest
min_score_threshold = 7 # Out of 10; papers below this won't be recommended

# ── Delivery ──────────────────────────────────────────────────
[delivery]
output_dir = "./outputs"
formats = ["markdown"]  # Options: markdown, json
# [delivery.email]
# to = "you@example.com"
# smtp_host = "smtp.gmail.com"
# slack_webhook_url = ""
# notion_api_key_env = ""
```

---

## 5. Module Specifications

### 5.1 Fetcher (`modules/fetcher.py`)

**Responsibility:** Query the arXiv API and return a normalized list of paper objects.

**Implementation:**
- Use the `arxiv` Python library (`pip install arxiv`)
- Build one query per topic using keyword OR logic, filtered by `config.arxiv.categories`
- Deduplicate results across topics (by `arxiv_id`)
- Check `data/seen_ids.txt` and skip already-processed papers
- Return list of `Paper` dataclass objects

**Paper dataclass:**
```python
@dataclass
class Paper:
    arxiv_id: str
    title: str
    abstract: str
    authors: list[str]
    submitted_date: str       # ISO 8601
    categories: list[str]
    comments: str             # e.g. "Accepted at NeurIPS 2024"
    journal_ref: str          # e.g. "ICML 2024"
    pdf_url: str
    matched_topics: list[str] # Topics matched during fetch
```

**Key function signature:**
```python
def fetch_papers(config: dict) -> list[Paper]:
    ...
```

---

### 5.2 Filter (`modules/filter.py`)

**Responsibility:** Score each paper's venue credibility and discard low-quality ones.

**Venue scoring logic:**

| Score | Criteria |
|-------|----------|
| 3 | Oral / spotlight / best paper at top venue |
| 2 | Accepted at Tier-1 venue (NeurIPS, ICML, ICLR, ACL, EMNLP, NAACL, CVPR, ECCV, AAAI, IJCAI) |
| 1 | Workshop paper at top venue, or accepted at Tier-2 venue |
| 0 | No venue signal detected |

**Signal detection:** Scan `paper.comments` and `paper.journal_ref` fields using regex patterns against `data/venue_list.toml`.

**`data/venue_list.toml` structure:**
```toml
[[tier1]]
name = "NeurIPS"
patterns = ["NeurIPS", "Neural Information Processing"]

[[tier1]]
name = "ICML"
patterns = ["ICML", "International Conference on Machine Learning"]

[[tier1]]
name = "ICLR"
patterns = ["ICLR", "International Conference on Learning Representations"]

# ... add more tier1 venues here

[[tier2]]
name = "CoRL"
patterns = ["CoRL", "Conference on Robot Learning"]

# ... add more tier2 venues here

oral_patterns = ["oral", "spotlight", "best paper"]
```

**Key function signature:**
```python
def filter_papers(papers: list[Paper], config: dict) -> list[Paper]:
    # Returns only papers with venue_score >= config.filter.min_venue_score
    ...
```

---

### 5.3 Analyzer (`modules/analyzer.py`)

**Responsibility:** Send filtered papers to Gemini for structured analysis.

**Per-paper analysis prompt** (`prompts/paper_analysis.txt`):
```
You are a research analyst specializing in AI agents.
Analyze the following paper and return ONLY a valid JSON object with this exact schema:

{
  "one_line_summary": "<1 sentence, plain English>",
  "contribution": "<2-3 sentences: what problem, what method, what result>",
  "novelty_score": <integer 1-10>,
  "relevance_score": <integer 1-10, relevance to AI agents>,
  "topics": ["<topic1>", "<topic2>"],   // from the provided topic list
  "recommendation_reason": "<why a researcher should read this, or empty string if not recommended>"
}

Available topics: {TOPIC_LIST}

Paper title: {TITLE}
Paper abstract: {ABSTRACT}
```

**Batching:** Process `config.llm.batch_size` papers per API call to reduce latency and cost.

**Output:** Attach analysis fields directly to the `Paper` dataclass (or a parallel `PaperAnalysis` object keyed by `arxiv_id`).

**Key function signature:**
```python
def analyze_papers(papers: list[Paper], config: dict) -> list[PaperAnalysis]:
    ...
```

**`PaperAnalysis` dataclass:**
```python
@dataclass
class PaperAnalysis:
    arxiv_id: str
    one_line_summary: str
    contribution: str
    novelty_score: int          # 1–10
    relevance_score: int        # 1–10
    topics: list[str]
    recommendation_reason: str
```

---

### 5.4 Digest Builder (`modules/digest.py`)

**Responsibility:** Combine papers + analyses into a structured daily digest.

**Steps:**

1. **Group papers by topic** — a paper may appear under multiple topics if it matched multiple
2. **Sort within each topic** by `(novelty_score + relevance_score) / 2` descending
3. **Select recommendations** — top N papers globally where `recommendation_reason != ""` and avg score >= threshold
4. **Generate daily summary** — call Gemini once with the digest-level prompt (`prompts/daily_summary.txt`) passing all one-line summaries

**Daily summary prompt** (`prompts/daily_summary.txt`):
```
You are summarizing today's AI agent research for a senior researcher.
Given the following paper summaries (already filtered and categorized), write:
1. A 3-5 sentence overview of the day's research landscape
2. The 2-3 most important trends or themes you observe

Paper summaries:
{SUMMARIES_LIST}

Return ONLY a JSON object:
{
  "overview": "<3-5 sentence paragraph>",
  "trends": ["<trend 1>", "<trend 2>", "<trend 3>"]
}
```

**Key function signature:**
```python
def build_digest(papers: list[Paper], analyses: list[PaperAnalysis], config: dict) -> Digest:
    ...
```

**`Digest` dataclass:**
```python
@dataclass
class Digest:
    date: str
    total_fetched: int
    total_after_filter: int
    overview: str
    trends: list[str]
    topics: dict[str, list[PaperEntry]]   # topic_name -> sorted papers
    recommendations: list[PaperEntry]
```

---

### 5.5 Delivery (`modules/delivery.py`)

**Responsibility:** Render and deliver the digest.

**Markdown output format:**

```markdown
# 📚 ArXiv AI Agent Digest — YYYY-MM-DD

> Fetched: 87 papers | After filter: 23 papers | Topics: 3

## 🌐 Today's Overview

{overview paragraph}

**Trends:** {trend 1} · {trend 2} · {trend 3}

---

## ⭐ Must-Read Recommendations

### 1. {Paper Title}
- **Authors:** ...  | **Venue:** ...
- **Summary:** {one_line_summary}
- **Why read:** {recommendation_reason}
- 🔗 [arXiv]({pdf_url})

---

## 🗂 Papers by Topic

### Agent Planning ({N} papers)

#### {Paper Title}
- **Score:** Novelty {X}/10 · Relevance {Y}/10
- **Summary:** {one_line_summary}
- **Contribution:** {contribution}
- 🔗 [arXiv]({pdf_url})

...

### Memory System ({N} papers)
...

### Multi-Agent Orchestration ({N} papers)
...
```

**Key function signature:**
```python
def deliver(digest: Digest, config: dict) -> None:
    # Writes markdown to outputs/YYYY-MM-DD.md
    # Optionally sends email/Slack notification
    ...
```

---

## 6. Scheduling

Use a cron job or GitHub Actions scheduled workflow.

**cron example** (runs daily at 8:00 AM UTC):
```
0 8 * * * cd /path/to/arxiv-bot && python main.py >> logs/bot.log 2>&1
```

**GitHub Actions example** (`.github/workflows/daily.yml`):
```yaml
name: Daily ArXiv Digest
on:
  schedule:
    - cron: "0 8 * * *"
  workflow_dispatch:

jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt
      - run: python main.py
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
      - uses: actions/upload-artifact@v4
        with:
          name: digest
          path: outputs/
```

---

## 7. Main Orchestrator (`main.py`)

```python
import tomllib
from modules.fetcher import fetch_papers
from modules.filter import filter_papers
from modules.analyzer import analyze_papers
from modules.digest import build_digest
from modules.delivery import deliver

def main():
    with open("config.toml", "rb") as f:
        config = tomllib.load(f)

    print("[1/5] Fetching papers...")
    papers = fetch_papers(config)
    print(f"  → {len(papers)} papers fetched")

    print("[2/5] Filtering papers...")
    papers = filter_papers(papers, config)
    print(f"  → {len(papers)} papers after filter")

    if not papers:
        print("  No papers passed filter today. Exiting.")
        return

    print("[3/5] Analyzing papers with Gemini...")
    analyses = analyze_papers(papers, config)

    print("[4/5] Building digest...")
    digest = build_digest(papers, analyses, config)

    print("[5/5] Delivering digest...")
    deliver(digest, config)
    print("  Done.")

if __name__ == "__main__":
    main()
```

---

## 8. Extensibility Guide

### Adding a new topic

In `config.toml`, append a new entry under `topics`:
```toml
[[topics]]
name = "Tool-Augmented Agents"
keywords = ["tool use", "function calling", "API agent", "code agent"]
```

No code changes required. The fetcher and analyzer automatically pick up new topics.

### Adding a new venue to the filter

In `data/venue_list.toml`, add the venue under the appropriate tier:
```toml
[[tier1]]
name = "COLM"
patterns = ["COLM", "Conference on Language Modeling"]
```

### Adding a new delivery channel

Implement a new function in `modules/delivery.py` and wire it to the `delivery` config key:
```python
def send_slack(digest: Digest, webhook_url: str) -> None:
    ...
```

### Swapping the LLM provider

The `analyzer.py` module should use a thin adapter pattern. To switch from Gemini to another provider (e.g., Claude, GPT-4), update `config.llm.provider` and implement the corresponding adapter in `modules/analyzer.py` behind the same `analyze_papers()` interface.

---

## 9. Dependencies (`requirements.txt`)

```
arxiv>=2.1.0
google-generativeai>=0.5.0
# tomllib is built-in for Python 3.11+; for older versions: pip install tomli
python-dateutil>=2.9.0
jinja2>=3.1.0        # Optional: for templated markdown rendering
requests>=2.31.0
```

---

## 10. Error Handling & Resilience

| Failure Point | Strategy |
|---------------|----------|
| arXiv API timeout | Retry 3× with exponential backoff |
| Gemini API rate limit | Respect 429 responses; sleep and retry |
| Gemini returns malformed JSON | Retry with `"Return ONLY valid JSON"` appended; log and skip paper on second failure |
| Zero papers after filter | Log warning and exit gracefully; do not send empty digest |
| Duplicate paper IDs across days | `seen_ids.txt` append-log prevents re-analysis |

---

## 11. Implementation Order (for coding agents)

Implement modules in this sequence to allow incremental testing:

1. **`modules/fetcher.py`** — verify raw arXiv API output
2. **`data/venue_list.toml`** + **`modules/filter.py`** — test filter scoring in isolation
3. **`prompts/paper_analysis.txt`** + **`modules/analyzer.py`** — test Gemini round-trip with 3 sample papers
4. **`prompts/daily_summary.txt`** + **`modules/digest.py`** — build digest from mock analysis data
5. **`modules/delivery.py`** — write and inspect markdown output
6. **`main.py`** — wire all modules together
7. **Scheduling** — configure cron or GitHub Actions

Each module should have a corresponding `test_<module>.py` using `pytest` with fixture data in `tests/fixtures/`.

---

*End of Design Document*
