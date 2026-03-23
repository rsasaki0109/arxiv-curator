"""Field map generation for research topics.

Builds a structured overview mapping papers to their code implementations
on GitHub, with venue and yearly trend statistics, topic clustering,
code availability trends, key paper identification, and gap analysis.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field

from arxiv_curator.models import EnrichedPaper

# Common English stopwords to exclude from keyword clustering
STOPWORDS: set[str] = {
    # English function words
    "a", "an", "the", "for", "of", "and", "in", "with", "using", "based",
    "via", "to", "on", "from", "by", "is", "are", "at", "its", "it",
    "as", "or", "be", "this", "that", "we", "our", "their", "can",
    "not", "no", "do", "has", "have", "was", "were", "been", "being",
    "which", "what", "where", "when", "how", "all", "each", "every",
    "more", "most", "other", "some", "such", "than", "too", "very",
    "new", "towards", "through", "into", "over", "between", "about",
    "under", "after", "before", "up", "down", "out", "off", "above",
    "below", "both", "but", "if", "then", "so", "any", "only", "own",
    "same", "also", "just",
    # Common academic adjectives / qualifiers (not meaningful as topics)
    "high", "better", "fast", "robust", "novel", "improved", "efficient",
    "large", "small", "simple", "deep", "real", "time", "low", "accurate",
    "general", "generalized", "unified", "adaptive", "dynamic", "scalable",
    "fully", "single", "multi", "end", "one", "two", "first", "level",
    # Generic academic nouns (too vague for topic clustering)
    "method", "approach", "framework", "model", "network", "system",
    "performance", "quality", "fidelity", "resolution",
}


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
    topic_clusters: dict[str, list[int]] = field(default_factory=dict)
    code_ratio_by_year: dict[int, tuple[int, int]] = field(default_factory=dict)
    key_papers: list[int] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)


def _extract_keywords(title: str) -> list[str]:
    """Extract significant lowercase words from a paper title."""
    words = re.findall(r"[a-zA-Z]{3,}", title)
    return [w.lower() for w in words if w.lower() not in STOPWORDS]


def _build_topic_clusters(
    entries: list[PaperWithCode],
) -> dict[str, list[int]]:
    """Group paper indices by dominant keywords in their titles."""
    word_to_indices: dict[str, list[int]] = {}
    for idx, entry in enumerate(entries):
        keywords = _extract_keywords(entry.paper.title)
        for kw in set(keywords):  # deduplicate per paper
            word_to_indices.setdefault(kw, []).append(idx)

    # Keep keywords that appear in at least 2 papers, sorted by frequency
    clusters = {
        kw: indices
        for kw, indices in sorted(
            word_to_indices.items(), key=lambda x: len(x[1]), reverse=True
        )
        if len(indices) >= 2
    }
    return clusters


def _build_code_ratio_by_year(
    entries: list[PaperWithCode],
) -> dict[int, tuple[int, int]]:
    """Track code availability ratio by year."""
    year_stats: dict[int, list[int]] = {}  # year -> [with_code, total]
    for entry in entries:
        year = entry.paper.published.year
        if year not in year_stats:
            year_stats[year] = [0, 0]
        year_stats[year][1] += 1
        if entry.github_urls:
            year_stats[year][0] += 1
    return {
        year: (stats[0], stats[1])
        for year, stats in sorted(year_stats.items())
    }


def _find_key_papers(entries: list[PaperWithCode], top_n: int = 5) -> list[int]:
    """Identify key papers (top N by citation count)."""
    indexed = [(idx, entry.paper.citation_count) for idx, entry in enumerate(entries)]
    indexed.sort(key=lambda x: x[1], reverse=True)
    return [idx for idx, _ in indexed[:top_n]]


def _analyze_gaps(
    entries: list[PaperWithCode],
    topic_clusters: dict[str, list[int]],
    code_ratio_by_year: dict[int, tuple[int, int]],
    yearly_counts: dict[int, int],
) -> list[str]:
    """Identify gaps in the research field."""
    gaps: list[str] = []

    # Gap: years with low code availability
    for year, (with_code, total) in code_ratio_by_year.items():
        if total > 0:
            ratio = with_code / total * 100
            if ratio < 30:
                gaps.append(
                    f"Only {with_code} paper{'s' if with_code != 1 else ''} "
                    f"in {year} had code available ({ratio:.0f}%)"
                )

    # Gap: years with very few papers (if we have multi-year data)
    if len(yearly_counts) >= 2:
        avg_count = sum(yearly_counts.values()) / len(yearly_counts)
        for year, count in yearly_counts.items():
            if count < avg_count * 0.3 and avg_count > 2:
                gaps.append(
                    f"Low activity in {year}: only {count} paper{'s' if count != 1 else ''} "
                    f"(avg {avg_count:.0f})"
                )

    # Gap: top keywords with low code availability
    for kw, indices in list(topic_clusters.items())[:10]:
        papers_with_code = sum(
            1 for idx in indices if entries[idx].github_urls
        )
        total = len(indices)
        if total >= 3 and papers_with_code / total < 0.3:
            gaps.append(
                f"Topic '{kw}': only {papers_with_code}/{total} papers have code"
            )

    # Gap: top keywords where newest paper is old
    if entries:
        for kw, indices in list(topic_clusters.items())[:10]:
            years = [entries[idx].paper.published.year for idx in indices]
            max_year = max(years)
            all_years = [e.paper.published.year for e in entries]
            latest_year = max(all_years)
            if latest_year - max_year >= 2:
                gaps.append(f"No papers on '{kw}' since {max_year}")

    return gaps


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

    # Build new analytics
    topic_clusters = _build_topic_clusters(entries)
    code_ratio_by_year = _build_code_ratio_by_year(entries)
    key_papers = _find_key_papers(entries)
    gaps = _analyze_gaps(entries, topic_clusters, code_ratio_by_year, sorted_years)

    return FieldMap(
        query="",
        total_papers=len(papers),
        papers_with_code=papers_with_code,
        papers_without_code=len(papers) - papers_with_code,
        top_venues=sorted_venues,
        yearly_counts=sorted_years,
        entries=entries,
        topic_clusters=topic_clusters,
        code_ratio_by_year=code_ratio_by_year,
        key_papers=key_papers,
        gaps=gaps,
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
        "topic_clusters": {
            kw: len(indices)
            for kw, indices in list(fm.topic_clusters.items())[:20]
        },
        "code_ratio_by_year": {
            str(year): {"with_code": wc, "total": t}
            for year, (wc, t) in fm.code_ratio_by_year.items()
        },
        "key_papers": [
            {
                "title": fm.entries[idx].paper.title,
                "citations": fm.entries[idx].paper.citation_count,
                "arxiv_url": fm.entries[idx].paper.arxiv_url,
            }
            for idx in fm.key_papers
            if idx < len(fm.entries)
        ],
        "gaps": fm.gaps,
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


def field_map_to_markdown(fm: FieldMap) -> str:
    """Convert field map to a readable Markdown report."""
    lines: list[str] = []
    lines.append(f"# Field Map: {fm.query}\n")

    # Summary
    ratio = fm.papers_with_code / max(fm.total_papers, 1) * 100
    lines.append("## Summary\n")
    lines.append(f"- **Total papers:** {fm.total_papers}")
    lines.append(f"- **Papers with code:** {fm.papers_with_code} ({ratio:.0f}%)")
    lines.append(f"- **Papers without code:** {fm.papers_without_code}")
    lines.append("")

    # Top venues
    if fm.top_venues:
        lines.append("## Top Venues\n")
        lines.append("| Venue | Papers |")
        lines.append("|---|---:|")
        for venue, count in list(fm.top_venues.items())[:10]:
            lines.append(f"| {venue} | {count} |")
        lines.append("")

    # Yearly distribution
    if fm.yearly_counts:
        lines.append("## Yearly Distribution\n")
        lines.append("| Year | Papers |")
        lines.append("|---|---:|")
        for year, count in fm.yearly_counts.items():
            lines.append(f"| {year} | {count} |")
        lines.append("")

    # Topic clusters
    if fm.topic_clusters:
        lines.append("## Topic Clusters\n")
        lines.append("| Keyword | Papers |")
        lines.append("|---|---:|")
        for kw, indices in list(fm.topic_clusters.items())[:15]:
            lines.append(f"| {kw} | {len(indices)} |")
        lines.append("")

    # Code availability trend
    if fm.code_ratio_by_year:
        lines.append("## Code Availability Trend\n")
        lines.append("| Year | With Code | Total | Ratio |")
        lines.append("|---|---:|---:|---:|")
        for year, (wc, total) in fm.code_ratio_by_year.items():
            pct = wc / max(total, 1) * 100
            lines.append(f"| {year} | {wc} | {total} | {pct:.0f}% |")
        lines.append("")

    # Key papers
    if fm.key_papers:
        lines.append("## Key Papers\n")
        for rank, idx in enumerate(fm.key_papers, 1):
            if idx < len(fm.entries):
                entry = fm.entries[idx]
                p = entry.paper
                code_str = ""
                if entry.github_urls:
                    code_str = f" | [Code]({entry.github_urls[0]})"
                lines.append(
                    f"{rank}. **[{p.title}]({p.arxiv_url})** "
                    f"({p.published.strftime('%Y-%m-%d')}) "
                    f"- Citations: {p.citation_count}{code_str}"
                )
        lines.append("")

    # Gaps & opportunities
    if fm.gaps:
        lines.append("## Gaps & Opportunities\n")
        for gap in fm.gaps:
            lines.append(f"- {gap}")
        lines.append("")

    # Top papers by citations
    sorted_entries = sorted(
        fm.entries, key=lambda e: e.paper.citation_count, reverse=True
    )[:10]
    if sorted_entries:
        lines.append("## Top Papers by Citations\n")
        lines.append("| # | Title | Citations | Published | Code |")
        lines.append("|---|---|---:|---|---|")
        for i, entry in enumerate(sorted_entries, 1):
            code_str = ", ".join(entry.github_urls) if entry.github_urls else "-"
            lines.append(
                f"| {i} | [{entry.paper.title}]({entry.paper.arxiv_url}) "
                f"| {entry.paper.citation_count} "
                f"| {entry.paper.published.strftime('%Y-%m-%d')} "
                f"| {code_str} |"
            )
        lines.append("")

    return "\n".join(lines)
