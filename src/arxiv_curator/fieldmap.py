"""Field map generation for research topics.

Builds a structured overview mapping papers to their code implementations
on GitHub, with venue and yearly trend statistics.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from arxiv_curator.models import EnrichedPaper


@dataclass
class PaperWithCode:
    """A paper paired with its discovered GitHub URLs."""

    paper: EnrichedPaper
    github_urls: list[str] = field(default_factory=list)


@dataclass
class FieldMap:
    """Structured overview of a research field."""

    query: str
    total_papers: int
    papers_with_code: int
    papers_without_code: int
    top_venues: dict[str, int]  # venue -> count
    yearly_counts: dict[int, int]  # year -> count
    entries: list[PaperWithCode] = field(default_factory=list)


def build_field_map(papers: list[EnrichedPaper]) -> FieldMap:
    """Build a structured field map from enriched papers."""
    entries: list[PaperWithCode] = []
    venue_counts: dict[str, int] = {}
    year_counts: dict[int, int] = {}

    for paper in papers:
        # Extract GitHub URLs from abstract
        github_urls = re.findall(
            r"https?://github\.com/[\w-]+/[\w.-]+", paper.abstract
        )
        if paper.code_url and paper.code_url not in github_urls:
            github_urls.append(paper.code_url)

        entries.append(PaperWithCode(paper=paper, github_urls=github_urls))

        # Count venues
        if paper.venue:
            venue = paper.venue.strip()
            if venue:
                venue_counts[venue] = venue_counts.get(venue, 0) + 1

        # Count years
        year = paper.published.year
        year_counts[year] = year_counts.get(year, 0) + 1

    papers_with_code = sum(1 for e in entries if e.github_urls)

    # Sort venues by count, years chronologically
    sorted_venues = dict(
        sorted(venue_counts.items(), key=lambda x: x[1], reverse=True)
    )
    sorted_years = dict(sorted(year_counts.items()))

    return FieldMap(
        query="",
        total_papers=len(papers),
        papers_with_code=papers_with_code,
        papers_without_code=len(papers) - papers_with_code,
        top_venues=sorted_venues,
        yearly_counts=sorted_years,
        entries=entries,
    )


def field_map_to_json(fm: FieldMap) -> str:
    """Convert field map to JSON."""
    data = {
        "query": fm.query,
        "total_papers": fm.total_papers,
        "papers_with_code": fm.papers_with_code,
        "papers_without_code": fm.papers_without_code,
        "code_ratio": f"{fm.papers_with_code / max(fm.total_papers, 1) * 100:.0f}%",
        "top_venues": fm.top_venues,
        "yearly_counts": {str(k): v for k, v in fm.yearly_counts.items()},
        "entries": [
            {
                "title": e.paper.title,
                "arxiv_url": e.paper.arxiv_url,
                "published": e.paper.published.isoformat(),
                "citations": e.paper.citation_count,
                "venue": e.paper.venue,
                "github_urls": e.github_urls,
                "has_code": bool(e.github_urls),
            }
            for e in fm.entries
        ],
    }
    return json.dumps(data, ensure_ascii=False, indent=2)
