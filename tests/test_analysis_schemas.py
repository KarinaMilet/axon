from __future__ import annotations

from axon.analysis.analyzer import PAPER_ANALYSIS_SCHEMA, analyze_papers
from axon.analysis.digest import DAILY_SUMMARY_SCHEMA, build_digest
from axon.models import Paper, PaperAnalysis


class RecordingLLM:
    def __init__(self, responses: list[dict] | None = None, error: Exception | None = None):
        self.responses = list(responses or [])
        self.error = error
        self.calls: list[dict] = []

    def generate(self, prompt: str) -> str:
        raise NotImplementedError

    def generate_json(self, prompt: str, schema: dict | None = None) -> dict:
        self.calls.append({"prompt": prompt, "schema": schema})
        if self.error is not None:
            raise self.error
        return self.responses.pop(0)


def _paper() -> Paper:
    return Paper(
        arxiv_id="1234.5678",
        title="Agentic Planning",
        abstract="A paper about planning.",
        authors=["Ada"],
        submitted_date="2026-03-14",
        categories=["cs.AI"],
        comments="",
        journal_ref="",
        pdf_url="https://example.com/paper.pdf",
        matched_topics=["Agent Planning"],
        venue_score=3,
    )


def test_analyze_papers_passes_schema(monkeypatch) -> None:
    monkeypatch.setattr("axon.analysis.analyzer.time.sleep", lambda _: None)
    llm = RecordingLLM(
        responses=[
            {
                "one_line_summary": "A summary",
                "contribution": "A contribution",
                "novelty_score": 8,
                "relevance_score": 9,
                "topics": ["Agent Planning"],
                "recommendation_reason": "Worth reading",
            }
        ]
    )

    analyses = analyze_papers([_paper()], {"topics": [{"name": "Agent Planning"}], "llm": {}}, llm)

    assert analyses[0].one_line_summary == "A summary"
    assert llm.calls[0]["schema"] == PAPER_ANALYSIS_SCHEMA


def test_analyze_papers_keeps_failure_fallback(monkeypatch) -> None:
    monkeypatch.setattr("axon.analysis.analyzer.time.sleep", lambda _: None)
    llm = RecordingLLM(error=RuntimeError("boom"))

    analyses = analyze_papers([_paper()], {"topics": [{"name": "Agent Planning"}], "llm": {}}, llm)

    assert analyses[0].one_line_summary == "[Analysis failed]"
    assert analyses[0].topics == ["Agent Planning"]


def test_build_digest_passes_schema() -> None:
    llm = RecordingLLM(responses=[{"overview": "A good day", "trends": ["Planning"]}])
    paper = _paper()
    analysis = PaperAnalysis(
        arxiv_id=paper.arxiv_id,
        one_line_summary="A summary",
        contribution="A contribution",
        novelty_score=8,
        relevance_score=9,
        topics=["Agent Planning"],
        recommendation_reason="Worth reading",
    )

    digest = build_digest([paper], [analysis], {"recommendations": {}}, llm, total_fetched=3)

    assert digest.overview == "A good day"
    assert digest.total_fetched == 3
    assert llm.calls[0]["schema"] == DAILY_SUMMARY_SCHEMA


def test_build_digest_keeps_failure_fallback() -> None:
    llm = RecordingLLM(error=RuntimeError("boom"))
    paper = _paper()
    analysis = PaperAnalysis(
        arxiv_id=paper.arxiv_id,
        one_line_summary="A summary",
        contribution="A contribution",
        novelty_score=8,
        relevance_score=9,
        topics=["Agent Planning"],
        recommendation_reason="Worth reading",
    )

    digest = build_digest([paper], [analysis], {"recommendations": {}}, llm)

    assert digest.overview == "Daily summary generation failed."
    assert digest.trends == []
