from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Paper:
    arxiv_id: str
    title: str
    abstract: str
    authors: list[str]
    submitted_date: str
    categories: list[str]
    comments: str
    journal_ref: str
    pdf_url: str
    matched_topics: list[str] = field(default_factory=list)
    venue_score: int = 0


@dataclass
class PaperAnalysis:
    arxiv_id: str
    one_line_summary: str
    contribution: str
    novelty_score: int
    relevance_score: int
    topics: list[str]
    recommendation_reason: str


@dataclass
class PaperEntry:
    """A paper combined with its analysis, used in the final digest."""

    paper: Paper
    analysis: PaperAnalysis

    @property
    def avg_score(self) -> float:
        return (self.analysis.novelty_score + self.analysis.relevance_score) / 2


@dataclass
class Digest:
    date: str
    total_fetched: int
    total_after_filter: int
    overview: str
    trends: list[str]
    topics: dict[str, list[PaperEntry]]
    recommendations: list[PaperEntry]
