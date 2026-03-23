"""Weekly digest builder for research field summaries.

Aggregates enriched and ranked papers into a newsletter-style digest
with must-reads, hidden gems, hot topics, and field statistics.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone

from arxiv_curator.fieldmap import STOPWORDS
from arxiv_curator.models import EnrichedPaper
from arxiv_curator.ranker import RankedPaper


@dataclass
class Digest:
    """A newsletter-style summary of papers for a time period."""

    query: str
    period_start: datetime
    period_end: datetime
    total_papers: int
    category_counts: dict[str, int]
    papers_with_code: int
    must_reads: list[RankedPaper]
    hidden_gems: list[RankedPaper]
    hot_topics: list[tuple[str, int]]
    venue_counts: dict[str, int]


def _extract_keywords(title: str) -> list[str]:
    """Extract significant lowercase words from a paper title."""
    words = re.findall(r"[a-zA-Z]{3,}", title)
    return [w.lower() for w in words if w.lower() not in STOPWORDS]


def _find_must_reads(ranked: list[RankedPaper], top_n: int = 3) -> list[RankedPaper]:
    """Select top papers by score (top N, preferring score > 50)."""
    if not ranked:
        return []
    # Already sorted by score descending from rank_papers
    return ranked[:top_n]


def _find_hidden_gems(
    ranked: list[RankedPaper],
    max_days: int = 30,
    max_citations: int = 10,
) -> list[RankedPaper]:
    """Find recent papers with code but low citations."""
    gems = []
    now = datetime.now(timezone.utc)
    for rp in ranked:
        paper = rp.paper
        published_utc = paper.published.replace(tzinfo=timezone.utc)
        days_old = (now - published_utc).days
        if days_old <= max_days and paper.code_url and paper.citation_count < max_citations:
            gems.append(rp)
    return gems


def _extract_hot_topics(
    papers: list[EnrichedPaper],
    top_n: int = 5,
) -> list[tuple[str, int]]:
    """Extract most frequent keywords from paper titles."""
    counter: Counter[str] = Counter()
    for paper in papers:
        keywords = set(_extract_keywords(paper.title))
        counter.update(keywords)
    return counter.most_common(top_n)


def _count_categories(papers: list[EnrichedPaper]) -> dict[str, int]:
    """Count papers per arXiv category."""
    counter: Counter[str] = Counter()
    for paper in papers:
        for cat in paper.categories:
            counter[cat] += 1
    # Sort by count descending
    return dict(counter.most_common())


def _count_venues(papers: list[EnrichedPaper]) -> dict[str, int]:
    """Count papers per venue."""
    counter: Counter[str] = Counter()
    for paper in papers:
        if paper.venue and paper.venue.strip():
            counter[paper.venue.strip()] += 1
    return dict(counter.most_common())


def build_digest(
    enriched_papers: list[EnrichedPaper],
    ranked_papers: list[RankedPaper],
    query: str,
    period_start: datetime,
    period_end: datetime,
) -> Digest:
    """Build a digest from enriched and ranked papers.

    Parameters
    ----------
    enriched_papers:
        Papers enriched with Semantic Scholar metadata.
    ranked_papers:
        Papers scored and ranked by rank_papers().
    query:
        The search query used.
    period_start:
        Start of the digest period.
    period_end:
        End of the digest period.
    """
    must_reads = _find_must_reads(ranked_papers)
    hidden_gems = _find_hidden_gems(ranked_papers)
    hot_topics = _extract_hot_topics(enriched_papers)
    category_counts = _count_categories(enriched_papers)
    venue_counts = _count_venues(enriched_papers)
    papers_with_code = sum(1 for p in enriched_papers if p.code_url)

    return Digest(
        query=query,
        period_start=period_start,
        period_end=period_end,
        total_papers=len(enriched_papers),
        category_counts=category_counts,
        papers_with_code=papers_with_code,
        must_reads=must_reads,
        hidden_gems=hidden_gems,
        hot_topics=hot_topics,
        venue_counts=venue_counts,
    )


def digest_to_markdown(digest: Digest) -> str:
    """Convert a digest to a Markdown newsletter format."""
    lines: list[str] = []

    start_str = digest.period_start.strftime("%Y-%m-%d")
    end_str = digest.period_end.strftime("%Y-%m-%d")

    lines.append(f"# Weekly Digest: {digest.query} ({start_str} -> {end_str})")
    lines.append("")

    # Overview
    lines.append("## Overview")
    lines.append("")
    lines.append(f"- **{digest.total_papers} new papers** this period")
    if digest.category_counts:
        cats = ", ".join(f"{cat}: {cnt}" for cat, cnt in list(digest.category_counts.items())[:5])
        lines.append(f"- Categories: {cats}")
    lines.append(f"- {digest.papers_with_code} papers have code available")
    if digest.venue_counts:
        venues = ", ".join(f"{v} ({c})" for v, c in list(digest.venue_counts.items())[:5])
        lines.append(f"- Top venues: {venues}")
    lines.append("")

    # Must Read
    if digest.must_reads:
        lines.append("## Must Read")
        lines.append("")
        for i, rp in enumerate(digest.must_reads, 1):
            p = rp.paper
            code_str = f" | Code: {p.code_url}" if p.code_url else ""
            cite_str = f" ({p.citation_count} citations)" if p.citation_count > 0 else ""
            lines.append(
                f"{i}. **[{p.title}]({p.arxiv_url})**{cite_str}{code_str}"
            )
            lines.append(f"   - Score: {rp.score:.0f} | {', '.join(rp.reasons)}")
        lines.append("")

    # Hidden Gems
    if digest.hidden_gems:
        lines.append("## Hidden Gems")
        lines.append("")
        for rp in digest.hidden_gems:
            p = rp.paper
            days_old = (datetime.now(timezone.utc) - p.published.replace(tzinfo=timezone.utc)).days
            lines.append(
                f"- **[{p.title}]({p.arxiv_url})** "
                f"({p.citation_count} citations, {days_old} days old)"
            )
            if p.code_url:
                lines.append(f"  - Code: {p.code_url}")
        lines.append("")

    # Hot Topics
    if digest.hot_topics:
        lines.append("## Hot Topics")
        lines.append("")
        for keyword, count in digest.hot_topics:
            lines.append(f"- \"{keyword}\" ({count} papers)")
        lines.append("")

    return "\n".join(lines)
