from __future__ import annotations

from axon.crawler.fetcher import fetch_papers
from axon.crawler.filter import filter_papers
from axon.models import Paper


def fetch(config: dict) -> tuple[list[Paper], int]:
    """Fetch and filter papers. Reusable by any downstream consumer.

    Returns (filtered_papers, total_fetched_count).
    """
    all_papers = fetch_papers(config)
    papers = filter_papers(all_papers, config)
    return papers, len(all_papers)
