from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

import arxiv

from axon.models import Paper

logger = logging.getLogger(__name__)

SEEN_IDS_PATH = Path("data/seen_ids.txt")


def _load_seen_ids() -> set[str]:
    if not SEEN_IDS_PATH.exists():
        return set()
    return set(SEEN_IDS_PATH.read_text().splitlines())


def _save_seen_ids(seen: set[str]) -> None:
    SEEN_IDS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SEEN_IDS_PATH.write_text("\n".join(sorted(seen)) + "\n")


def _build_query(keywords: list[str], categories: list[str]) -> str:
    kw_clause = " OR ".join(f'abs:"{kw}"' for kw in keywords)
    cat_clause = " OR ".join(f"cat:{cat}" for cat in categories)
    return f"({kw_clause}) AND ({cat_clause})"


def _result_to_paper(result: arxiv.Result, matched_topics: list[str]) -> Paper:
    return Paper(
        arxiv_id=result.entry_id.split("/abs/")[-1],
        title=result.title.replace("\n", " ").strip(),
        abstract=result.summary.replace("\n", " ").strip(),
        authors=[a.name for a in result.authors],
        submitted_date=result.published.isoformat(),
        categories=[c for c in result.categories],
        comments=result.comment or "",
        journal_ref=result.journal_ref or "",
        pdf_url=result.pdf_url or "",
        matched_topics=matched_topics,
    )


def fetch_papers(config: dict) -> list[Paper]:
    arxiv_cfg = config["arxiv"]
    categories = arxiv_cfg["categories"]
    max_results = arxiv_cfg.get("max_results_per_query", 100)
    lookback_days = arxiv_cfg.get("lookback_days", 1)

    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    seen_ids = _load_seen_ids()
    papers_by_id: dict[str, Paper] = {}

    topics = config.get("topics", [])
    client = arxiv.Client()

    for topic in topics:
        query = _build_query(topic["keywords"], categories)
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending,
        )

        for result in client.results(search):
            if result.published.replace(tzinfo=timezone.utc) < cutoff:
                break

            paper = _result_to_paper(result, [topic["name"]])

            if paper.arxiv_id in seen_ids:
                continue

            if paper.arxiv_id in papers_by_id:
                existing = papers_by_id[paper.arxiv_id]
                if topic["name"] not in existing.matched_topics:
                    existing.matched_topics.append(topic["name"])
            else:
                papers_by_id[paper.arxiv_id] = paper

    new_papers = list(papers_by_id.values())

    new_ids = seen_ids | {p.arxiv_id for p in new_papers}
    _save_seen_ids(new_ids)

    logger.info("Fetched %d new papers (skipped %d seen)", len(new_papers), len(seen_ids))
    return new_papers
