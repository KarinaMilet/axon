from __future__ import annotations

import logging

from axon.llm import create_provider
from axon.modules.analyzer import analyze_papers
from axon.modules.delivery import deliver
from axon.modules.digest import build_digest
from axon.modules.fetcher import fetch_papers
from axon.modules.filter import filter_papers

logger = logging.getLogger(__name__)


def run_pipeline(config: dict) -> None:
    print("[1/5] Fetching papers...")
    all_papers = fetch_papers(config)
    total_fetched = len(all_papers)
    print(f"  → {total_fetched} papers fetched")

    print("[2/5] Filtering papers...")
    papers = filter_papers(all_papers, config)
    print(f"  → {len(papers)} papers after filter")

    if not papers:
        print("  No papers passed filter today. Exiting.")
        return

    print("[3/5] Analyzing papers with LLM...")
    llm = create_provider(config)
    analyses = analyze_papers(papers, config, llm)

    print("[4/5] Building digest...")
    digest = build_digest(papers, analyses, config, llm, total_fetched=total_fetched)

    print("[5/5] Delivering digest...")
    output_path = deliver(digest, config)
    print(f"  Done. Output: {output_path}")


def fetch_only_pipeline(config: dict) -> None:
    """Run only the fetch + filter stages (no LLM calls)."""
    print("[1/2] Fetching papers...")
    all_papers = fetch_papers(config)
    print(f"  → {len(all_papers)} papers fetched")

    print("[2/2] Filtering papers...")
    papers = filter_papers(all_papers, config)
    print(f"  → {len(papers)} papers after filter")

    if papers:
        print("\nFiltered papers:")
        for p in papers:
            print(f"  [{p.venue_score}] {p.title}")
            print(f"      Topics: {', '.join(p.matched_topics)}")
            print(f"      {p.pdf_url}")
    else:
        print("  No papers passed filter today.")
