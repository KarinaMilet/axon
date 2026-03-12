from __future__ import annotations

import logging
import re
import tomllib
from pathlib import Path

from axon.models import Paper

logger = logging.getLogger(__name__)

VENUE_LIST_PATH = Path("data/venue_list.toml")


def _load_venue_list() -> dict:
    with open(VENUE_LIST_PATH, "rb") as f:
        return tomllib.load(f)


def _score_paper(paper: Paper, venue_data: dict) -> int:
    text = f"{paper.comments} {paper.journal_ref}".strip()
    if not text:
        return 0

    text_lower = text.lower()

    oral_patterns = venue_data.get("oral_patterns", [])
    has_oral = any(p.lower() in text_lower for p in oral_patterns)

    for venue in venue_data.get("tier1", []):
        for pattern in venue["patterns"]:
            if re.search(re.escape(pattern), text, re.IGNORECASE):
                return 3 if has_oral else 2

    for venue in venue_data.get("tier2", []):
        for pattern in venue["patterns"]:
            if re.search(re.escape(pattern), text, re.IGNORECASE):
                return 2 if has_oral else 1

    if "workshop" in text_lower:
        return 1

    return 0


def filter_papers(papers: list[Paper], config: dict) -> list[Paper]:
    filter_cfg = config.get("filter", {})
    min_score = filter_cfg.get("min_venue_score", 2)
    require_signal = filter_cfg.get("require_venue_signal", False)

    venue_data = _load_venue_list()
    result: list[Paper] = []

    for paper in papers:
        score = _score_paper(paper, venue_data)
        paper.venue_score = score

        if require_signal and score == 0:
            continue
        if score >= min_score:
            result.append(paper)

    logger.info(
        "Filter: %d/%d papers passed (min_score=%d)",
        len(result),
        len(papers),
        min_score,
    )
    return result
