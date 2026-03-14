from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from axon.llm.base import LLMProvider
from axon.models import Digest, Paper, PaperAnalysis, PaperEntry

logger = logging.getLogger(__name__)

DAILY_SUMMARY_PROMPT_PATH = Path("prompts/daily_summary.txt")
DAILY_SUMMARY_SCHEMA = {
    "name": "daily_summary",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "overview": {"type": "string"},
            "trends": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
        "required": ["overview", "trends"],
    },
}


def _group_by_topic(
    papers: list[Paper],
    analyses: list[PaperAnalysis],
) -> dict[str, list[PaperEntry]]:
    analysis_map = {a.arxiv_id: a for a in analyses}
    topic_groups: dict[str, list[PaperEntry]] = {}

    for paper in papers:
        analysis = analysis_map.get(paper.arxiv_id)
        if analysis is None:
            continue

        entry = PaperEntry(paper=paper, analysis=analysis)

        all_topics = set(paper.matched_topics) | set(analysis.topics)
        for topic in all_topics:
            topic_groups.setdefault(topic, []).append(entry)

    for entries in topic_groups.values():
        entries.sort(key=lambda e: e.avg_score, reverse=True)

    return topic_groups


def _select_recommendations(
    papers: list[Paper],
    analyses: list[PaperAnalysis],
    config: dict,
) -> list[PaperEntry]:
    rec_cfg = config.get("recommendations", {})
    top_n = rec_cfg.get("top_n", 5)
    min_score = rec_cfg.get("min_score_threshold", 7)

    analysis_map = {a.arxiv_id: a for a in analyses}
    candidates: list[PaperEntry] = []

    for paper in papers:
        analysis = analysis_map.get(paper.arxiv_id)
        if analysis is None:
            continue
        entry = PaperEntry(paper=paper, analysis=analysis)
        if entry.avg_score >= min_score and analysis.recommendation_reason:
            candidates.append(entry)

    candidates.sort(key=lambda e: e.avg_score, reverse=True)
    return candidates[:top_n]


def _generate_daily_summary(
    analyses: list[PaperAnalysis],
    llm: LLMProvider,
) -> tuple[str, list[str]]:
    template = DAILY_SUMMARY_PROMPT_PATH.read_text()

    summaries = "\n".join(
        f"- {a.one_line_summary}" for a in analyses if a.one_line_summary
    )
    prompt = template.replace("{SUMMARIES_LIST}", summaries)

    try:
        data = llm.generate_json(prompt, schema=DAILY_SUMMARY_SCHEMA)
        overview = data.get("overview", "")
        trends = data.get("trends", [])
        return overview, trends
    except Exception:
        logger.exception("Failed to generate daily summary")
        return "Daily summary generation failed.", []


def build_digest(
    papers: list[Paper],
    analyses: list[PaperAnalysis],
    config: dict,
    llm: LLMProvider,
    total_fetched: int = 0,
) -> Digest:
    topic_groups = _group_by_topic(papers, analyses)
    recommendations = _select_recommendations(papers, analyses, config)
    overview, trends = _generate_daily_summary(analyses, llm)

    return Digest(
        date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        total_fetched=total_fetched or len(papers),
        total_after_filter=len(papers),
        overview=overview,
        trends=trends,
        topics=topic_groups,
        recommendations=recommendations,
    )
