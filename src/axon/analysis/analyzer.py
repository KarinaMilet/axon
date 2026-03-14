from __future__ import annotations

import logging
import time
from pathlib import Path

from axon.llm.base import LLMProvider
from axon.models import Paper, PaperAnalysis

logger = logging.getLogger(__name__)

PAPER_PROMPT_PATH = Path("prompts/paper_analysis.txt")
PAPER_ANALYSIS_SCHEMA = {
    "name": "paper_analysis",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "one_line_summary": {"type": "string"},
            "contribution": {"type": "string"},
            "novelty_score": {"type": "integer"},
            "relevance_score": {"type": "integer"},
            "topics": {
                "type": "array",
                "items": {"type": "string"},
            },
            "recommendation_reason": {"type": "string"},
        },
        "required": [
            "one_line_summary",
            "contribution",
            "novelty_score",
            "relevance_score",
            "topics",
            "recommendation_reason",
        ],
    },
}


def _load_prompt_template() -> str:
    return PAPER_PROMPT_PATH.read_text()


def _build_prompt(template: str, paper: Paper, topic_list: list[str]) -> str:
    return (
        template.replace("{TOPIC_LIST}", ", ".join(topic_list))
        .replace("{TITLE}", paper.title)
        .replace("{ABSTRACT}", paper.abstract)
    )


def _parse_analysis(arxiv_id: str, data: dict) -> PaperAnalysis:
    return PaperAnalysis(
        arxiv_id=arxiv_id,
        one_line_summary=data.get("one_line_summary", ""),
        contribution=data.get("contribution", ""),
        novelty_score=int(data.get("novelty_score", 5)),
        relevance_score=int(data.get("relevance_score", 5)),
        topics=data.get("topics", []),
        recommendation_reason=data.get("recommendation_reason", ""),
    )


def analyze_papers(
    papers: list[Paper],
    config: dict,
    llm: LLMProvider,
) -> list[PaperAnalysis]:
    template = _load_prompt_template()
    topic_names = [t["name"] for t in config.get("topics", [])]
    batch_size = config.get("llm", {}).get("batch_size", 5)

    analyses: list[PaperAnalysis] = []

    for i in range(0, len(papers), batch_size):
        batch = papers[i : i + batch_size]
        logger.info(
            "Analyzing batch %d/%d (%d papers)",
            i // batch_size + 1,
            (len(papers) + batch_size - 1) // batch_size,
            len(batch),
        )

        for j, paper in enumerate(batch):
            prompt = _build_prompt(template, paper, topic_names)
            try:
                data = llm.generate_json(prompt, schema=PAPER_ANALYSIS_SCHEMA)
                analysis = _parse_analysis(paper.arxiv_id, data)
                analyses.append(analysis)
                logger.info("  ✓ %s", paper.title[:60])
            except Exception:
                logger.exception("Failed to analyze paper %s, skipping", paper.arxiv_id)
                analyses.append(
                    PaperAnalysis(
                        arxiv_id=paper.arxiv_id,
                        one_line_summary="[Analysis failed]",
                        contribution="",
                        novelty_score=5,
                        relevance_score=5,
                        topics=paper.matched_topics,
                        recommendation_reason="",
                    )
                )

            if j < len(batch) - 1:
                time.sleep(13)

    logger.info("Analyzed %d papers total", len(analyses))
    return analyses
