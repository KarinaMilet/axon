from __future__ import annotations

import logging
from pathlib import Path

from jinja2 import Template

from axon.models import Digest

logger = logging.getLogger(__name__)

MARKDOWN_TEMPLATE = """\
# 📚 ArXiv AI Agent Digest — {{ digest.date }}

> Fetched: {{ digest.total_fetched }} papers | After filter: {{ digest.total_after_filter }} papers | Topics: {{ digest.topics | length }}

## 🌐 Today's Overview

{{ digest.overview }}

**Trends:** {{ digest.trends | join(' · ') }}

---

## ⭐ Must-Read Recommendations
{% for entry in digest.recommendations %}

### {{ loop.index }}. {{ entry.paper.title }}
- **Authors:** {{ entry.paper.authors | join(', ') }}
- **Venue Score:** {{ entry.paper.venue_score }}
- **Summary:** {{ entry.analysis.one_line_summary }}
- **Why read:** {{ entry.analysis.recommendation_reason }}
- 🔗 [arXiv]({{ entry.paper.pdf_url }})
{% endfor %}
{% if not digest.recommendations %}
No papers met the recommendation threshold today.
{% endif %}

---

## 🗂 Papers by Topic
{% for topic_name, entries in digest.topics.items() %}

### {{ topic_name }} ({{ entries | length }} papers)
{% for entry in entries %}

#### {{ entry.paper.title }}
- **Score:** Novelty {{ entry.analysis.novelty_score }}/10 · Relevance {{ entry.analysis.relevance_score }}/10
- **Summary:** {{ entry.analysis.one_line_summary }}
- **Contribution:** {{ entry.analysis.contribution }}
- 🔗 [arXiv]({{ entry.paper.pdf_url }})
{% endfor %}
{% endfor %}
"""


def _render_markdown(digest: Digest) -> str:
    template = Template(MARKDOWN_TEMPLATE)
    return template.render(digest=digest)


def deliver(digest: Digest, config: dict) -> Path:
    delivery_cfg = config.get("delivery", {})
    output_dir = Path(delivery_cfg.get("output_dir", "./outputs"))
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"{digest.date}.md"
    content = _render_markdown(digest)
    output_path.write_text(content, encoding="utf-8")

    logger.info("Digest written to %s", output_path)
    return output_path
