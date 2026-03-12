from __future__ import annotations

import logging
from typing import Callable

logger = logging.getLogger(__name__)


class Orchestrator:
    """Central dispatcher that coordinates crawler, analysis, and delivery."""

    def __init__(self, config: dict):
        self.config = config

    def run(self, task: str, **kwargs) -> None:
        handler = self._registry.get(task)
        if not handler:
            available = ", ".join(self._registry)
            raise ValueError(f"Unknown task: {task!r} (available: {available})")
        handler(**kwargs)

    @property
    def _registry(self) -> dict[str, Callable]:
        return {
            "daily": self._daily,
            "fetch": self._fetch,
        }

    def _fetch(self, **kwargs) -> None:
        from axon.crawler import fetch

        print("[1/2] Fetching papers...")
        papers, total = fetch(self.config)
        print(f"  -> {total} papers fetched")
        print(f"  -> {len(papers)} papers after filter")

        if papers:
            print("\nFiltered papers:")
            for p in papers:
                print(f"  [{p.venue_score}] {p.title}")
                print(f"      Topics: {', '.join(p.matched_topics)}")
                print(f"      {p.pdf_url}")
        else:
            print("  No papers passed filter today.")

    def _daily(self, **kwargs) -> None:
        from axon.analysis import run_analysis
        from axon.crawler import fetch
        from axon.delivery import deliver_all

        print("[1/3] Fetching papers...")
        papers, total_fetched = fetch(self.config)
        print(f"  -> {total_fetched} papers fetched, {len(papers)} after filter")

        if not papers:
            print("  No papers passed filter today. Exiting.")
            return

        print("[2/3] Analyzing papers with LLM...")
        digest = run_analysis(papers, self.config, total_fetched)

        print("[3/3] Delivering digest...")
        results = deliver_all(digest, self.config)
        for r in results:
            print(f"  Done. Output: {r}")
