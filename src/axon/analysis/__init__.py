from __future__ import annotations

from axon.analysis.analyzer import analyze_papers
from axon.analysis.digest import build_digest
from axon.llm import create_provider
from axon.models import Digest, Paper


def run_analysis(papers: list[Paper], config: dict, total_fetched: int) -> Digest:
    """Analyze papers and build digest. Returns a Digest object."""
    llm = create_provider(config)
    analyses = analyze_papers(papers, config, llm)
    return build_digest(papers, analyses, config, llm, total_fetched=total_fetched)
