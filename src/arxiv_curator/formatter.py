"""Output formatters for paper results."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from arxiv_curator.models import EnrichedPaper, Paper

if TYPE_CHECKING:
    from arxiv_curator.digest import Digest
    from arxiv_curator.fieldmap import FieldMap
    from arxiv_curator.ranker import RankedPaper


def _is_enriched(papers: list[Paper]) -> bool:
    """Check if all papers in the list are EnrichedPaper instances."""
    return len(papers) > 0 and all(isinstance(p, EnrichedPaper) for p in papers)


def format_as_table(papers: list[Paper]) -> Table:
    """Create a rich Table from a list of papers."""
    enriched = _is_enriched(papers)

    table = Table(title="arXiv Papers", show_lines=True)
    table.add_column("#", style="dim", width=4)
    table.add_column("arXiv", style="cyan", width=14)
    table.add_column("Title", style="bold cyan", max_width=60)
    table.add_column("Authors", max_width=30)
    table.add_column("Published", style="green", width=12)
    table.add_column("Categories", style="magenta", max_width=20)

    if enriched:
        table.add_column("Citations", style="yellow", justify="right", width=10)
        table.add_column("Venue", style="blue", max_width=25)
        table.add_column("OA", style="green", width=4)

    for i, paper in enumerate(papers, 1):
        authors_str = ", ".join(paper.authors[:2])
        if len(paper.authors) > 2:
            authors_str += " et al."

        # Extract arXiv ID from URL (e.g. "https://arxiv.org/abs/2603.20194v1" → "2603.20194")
        arxiv_id = paper.arxiv_url.rstrip("/").split("/")[-1]
        # Strip version suffix like "v1"
        if "v" in arxiv_id:
            arxiv_id = arxiv_id.rsplit("v", 1)[0]

        row = [
            str(i),
            arxiv_id,
            paper.title,
            authors_str,
            paper.published.strftime("%Y-%m-%d"),
            ", ".join(paper.categories[:3]),
        ]

        if enriched:
            ep: EnrichedPaper = paper  # type: ignore[assignment]
            row.append(str(ep.citation_count))
            row.append(ep.venue or "-")
            row.append("Y" if ep.is_open_access else "-")

        table.add_row(*row)

    return table


def format_as_markdown(papers: list[Paper]) -> str:
    """Format papers as awesome-list style markdown."""
    lines = ["# arXiv Papers\n"]
    for paper in papers:
        lines.append(paper.to_markdown())
    lines.append("")
    return "\n".join(lines)


def format_ranked_table(ranked: list[RankedPaper]) -> Table:
    """Create a Rich table for ranked papers."""
    table = Table(title="Ranked Papers", show_lines=True)
    table.add_column("Rank", style="dim", width=5, justify="right")
    table.add_column("Score", width=7, justify="right")
    table.add_column("Percentile", width=10, justify="right")
    table.add_column("Category", width=15)
    table.add_column("Title", style="bold cyan", max_width=50)
    table.add_column("Citations", style="yellow", justify="right", width=10)
    table.add_column("Venue", style="blue", max_width=20)
    table.add_column("Published", style="green", width=12)
    table.add_column("Signals", max_width=40)

    for i, rp in enumerate(ranked, 1):
        # Color-code score: green >= 50, yellow >= 25, otherwise default
        if rp.score >= 50:
            score_str = f"[bold green]{rp.score:.0f}[/bold green]"
        elif rp.score >= 25:
            score_str = f"[yellow]{rp.score:.0f}[/yellow]"
        else:
            score_str = f"{rp.score:.0f}"

        percentile_str = f"Top {100 - rp.percentile:.0f}%" if rp.percentile < 100 else "Top 0%"
        # For the top paper, show "Top 0%" -> adjust to show meaningful value
        percentile_str = f"Top {max(100 - rp.percentile, 1):.0f}%"

        # Color-code category
        cat = rp.category
        if cat == "Must read":
            cat_str = f"[bold green]{cat}[/bold green]"
        elif cat == "Recommended":
            cat_str = f"[yellow]{cat}[/yellow]"
        elif cat == "Worth checking":
            cat_str = f"[blue]{cat}[/blue]"
        else:
            cat_str = f"[dim]{cat}[/dim]"

        signals = ", ".join(rp.reasons)
        table.add_row(
            str(i),
            score_str,
            percentile_str,
            cat_str,
            rp.paper.title,
            str(rp.paper.citation_count),
            rp.paper.venue or "-",
            rp.paper.published.strftime("%Y-%m-%d"),
            signals,
        )

    return table


def format_rank_summary(summary: dict) -> str:
    """Format rank summary statistics as a string."""
    total = summary["total"]
    with_code = summary["with_code"]
    code_pct = (with_code / total * 100) if total > 0 else 0
    lines = [
        "Summary:",
        f"  Must read: {summary['must_read']} papers",
        f"  Recommended: {summary['recommended']} papers",
        f"  With code: {with_code}/{total} ({code_pct:.0f}%)",
        f"  Top venue papers: {summary['top_venue']}",
        f"  Average citations: {summary['avg_citations']}",
    ]
    return "\n".join(lines)


def format_field_map(fm: FieldMap) -> list[Panel | Table]:
    """Create Rich renderables for a field map summary.

    Returns a list of Rich objects (panels / tables) that the caller
    can print one by one.
    """
    from arxiv_curator.fieldmap import FieldMap  # noqa: F811 — runtime import

    # --- Summary panel ---
    ratio = fm.papers_with_code / max(fm.total_papers, 1) * 100
    summary_lines = [
        f"Total papers:      {fm.total_papers}",
        f"Papers with code:  {fm.papers_with_code} ({ratio:.0f}%)",
        f"Papers w/o code:   {fm.papers_without_code}",
    ]
    summary_panel = Panel(
        "\n".join(summary_lines),
        title=f"Field Map: {fm.query}",
        border_style="bold cyan",
    )

    # --- Venues table ---
    venue_table = Table(title="Top Venues", show_lines=False)
    venue_table.add_column("Venue", style="bold blue", max_width=40)
    venue_table.add_column("Papers", justify="right", style="yellow", width=8)
    for venue, count in list(fm.top_venues.items())[:10]:
        venue_table.add_row(venue, str(count))

    # --- Yearly trend ---
    year_lines: list[str] = []
    if fm.yearly_counts:
        max_count = max(fm.yearly_counts.values())
        bar_width = 30
        for year, count in fm.yearly_counts.items():
            bar_len = int(count / max(max_count, 1) * bar_width)
            bar = "\u2588" * bar_len
            year_lines.append(f"  {year}  {bar} {count}")
    year_panel = Panel(
        "\n".join(year_lines) if year_lines else "(no data)",
        title="Yearly Distribution",
        border_style="green",
    )

    # --- Topic Clusters ---
    cluster_lines: list[str] = []
    if fm.topic_clusters:
        for kw, indices in list(fm.topic_clusters.items())[:15]:
            cluster_lines.append(f"  {kw:<25s} {len(indices)} papers")
    cluster_panel = Panel(
        "\n".join(cluster_lines) if cluster_lines else "(no clusters found)",
        title="Topic Clusters",
        border_style="magenta",
    )

    # --- Code Availability Trend ---
    code_trend_lines: list[str] = []
    if fm.code_ratio_by_year:
        for year, (wc, total) in fm.code_ratio_by_year.items():
            pct = wc / max(total, 1) * 100
            bar_len = int(pct / 100 * 20)
            bar = "\u2588" * bar_len + "\u2591" * (20 - bar_len)
            code_trend_lines.append(
                f"  {year}  {bar} {wc}/{total} ({pct:.0f}%)"
            )
    code_trend_panel = Panel(
        "\n".join(code_trend_lines) if code_trend_lines else "(no data)",
        title="Code Availability Trend",
        border_style="yellow",
    )

    # --- Key Papers ---
    key_papers_table = Table(title="Key Papers", show_lines=True)
    key_papers_table.add_column("#", style="dim", width=4)
    key_papers_table.add_column("Title", style="bold yellow", max_width=50)
    key_papers_table.add_column(
        "Citations", style="bold green", justify="right", width=10
    )
    key_papers_table.add_column("Published", style="green", width=12)
    key_papers_table.add_column("Code", max_width=50)
    for rank, idx in enumerate(fm.key_papers, 1):
        if idx < len(fm.entries):
            entry = fm.entries[idx]
            code_str = ", ".join(entry.github_urls) if entry.github_urls else "-"
            key_papers_table.add_row(
                str(rank),
                entry.paper.title,
                str(entry.paper.citation_count),
                entry.paper.published.strftime("%Y-%m-%d"),
                code_str,
            )

    # --- Top papers table (by citation, max 10) ---
    sorted_entries = sorted(
        fm.entries, key=lambda e: e.paper.citation_count, reverse=True
    )[:10]
    papers_table = Table(title="Top Papers by Citations", show_lines=True)
    papers_table.add_column("#", style="dim", width=4)
    papers_table.add_column("Title", style="bold cyan", max_width=50)
    papers_table.add_column("Citations", style="yellow", justify="right", width=10)
    papers_table.add_column("Published", style="green", width=12)
    papers_table.add_column("Code", max_width=50)
    for i, entry in enumerate(sorted_entries, 1):
        code_str = ", ".join(entry.github_urls) if entry.github_urls else "-"
        papers_table.add_row(
            str(i),
            entry.paper.title,
            str(entry.paper.citation_count),
            entry.paper.published.strftime("%Y-%m-%d"),
            code_str,
        )

    # --- Gaps & Opportunities ---
    gap_lines: list[str] = []
    if fm.gaps:
        for gap in fm.gaps:
            gap_lines.append(f"  - {gap}")
    gaps_panel = Panel(
        "\n".join(gap_lines) if gap_lines else "(no gaps identified)",
        title="Gaps & Opportunities",
        border_style="red",
    )

    return [
        summary_panel,
        venue_table,
        year_panel,
        cluster_panel,
        code_trend_panel,
        key_papers_table,
        papers_table,
        gaps_panel,
    ]


def format_digest(digest: Digest) -> list[Panel | Table]:
    """Create Rich renderables for a digest newsletter.

    Returns a list of Rich objects (panels / tables) that the caller
    can print one by one.
    """
    from datetime import timezone

    start_str = digest.period_start.strftime("%Y-%m-%d")
    end_str = digest.period_end.strftime("%Y-%m-%d")

    # --- Header panel ---
    header_panel = Panel(
        f"[bold]{digest.query}[/bold]\n{start_str} -> {end_str}",
        title="Weekly Digest",
        border_style="bold cyan",
    )

    # --- Overview panel ---
    overview_lines = [
        f"  {digest.total_papers} new papers this period",
    ]
    if digest.category_counts:
        cats = ", ".join(
            f"{cat}: {cnt}"
            for cat, cnt in list(digest.category_counts.items())[:5]
        )
        overview_lines.append(f"  Categories: {cats}")
    overview_lines.append(
        f"  {digest.papers_with_code} papers have code available"
    )
    if digest.venue_counts:
        venues = ", ".join(
            f"{v} ({c})" for v, c in list(digest.venue_counts.items())[:5]
        )
        overview_lines.append(f"  Top venues: {venues}")
    overview_panel = Panel(
        "\n".join(overview_lines),
        title="Overview",
        border_style="green",
    )

    # --- Must Read table ---
    must_read_table = Table(title="Must Read (Top 3 by score)", show_lines=True)
    must_read_table.add_column("Rank", style="dim", width=5, justify="right")
    must_read_table.add_column("Score", width=7, justify="right")
    must_read_table.add_column("Title", style="bold cyan", max_width=50)
    must_read_table.add_column("Citations", style="yellow", justify="right", width=10)
    must_read_table.add_column("Code", max_width=40)
    must_read_table.add_column("Signals", max_width=40)
    for i, rp in enumerate(digest.must_reads, 1):
        p = rp.paper
        if rp.score >= 50:
            score_str = f"[bold green]{rp.score:.0f}[/bold green]"
        elif rp.score >= 25:
            score_str = f"[yellow]{rp.score:.0f}[/yellow]"
        else:
            score_str = f"{rp.score:.0f}"
        code_str = p.code_url if p.code_url else "-"
        signals = ", ".join(rp.reasons)
        must_read_table.add_row(
            str(i),
            score_str,
            p.title,
            str(p.citation_count),
            code_str,
            signals,
        )

    result: list[Panel | Table] = [header_panel, overview_panel, must_read_table]

    # --- Hidden Gems panel ---
    if digest.hidden_gems:
        now = __import__("datetime").datetime.now(timezone.utc)
        gem_lines: list[str] = []
        for rp in digest.hidden_gems:
            p = rp.paper
            days_old = (now - p.published.replace(tzinfo=timezone.utc)).days
            gem_lines.append(
                f"  {p.title} ({p.citation_count} citations, {days_old} days old)"
            )
            if p.code_url:
                gem_lines.append(f"    -> {p.code_url}")
        gems_panel = Panel(
            "\n".join(gem_lines),
            title="Hidden Gems (recent + code, low citations)",
            border_style="yellow",
        )
        result.append(gems_panel)

    # --- Papers by Topic table ---
    if digest.topic_groups:
        for topic, papers in digest.topic_groups.items():
            topic_table = Table(
                title=f"Papers about {topic}: {len(papers)} papers",
                show_lines=True,
            )
            topic_table.add_column("#", style="dim", width=4, justify="right")
            topic_table.add_column("Score", width=7, justify="right")
            topic_table.add_column("Title", style="bold cyan", max_width=50)
            topic_table.add_column("Signals", max_width=50)
            for idx, rp in enumerate(papers, 1):
                if rp.score >= 50:
                    s_str = f"[bold green]{rp.score:.0f}[/bold green]"
                elif rp.score >= 25:
                    s_str = f"[yellow]{rp.score:.0f}[/yellow]"
                else:
                    s_str = f"{rp.score:.0f}"
                topic_table.add_row(
                    str(idx),
                    s_str,
                    rp.paper.title,
                    ", ".join(rp.reasons),
                )
            result.append(topic_table)

    # --- Hot Topics panel ---
    if digest.hot_topics:
        topic_lines = [
            f'  "{kw}" ({count} papers)' for kw, count in digest.hot_topics
        ]
        topics_panel = Panel(
            "\n".join(topic_lines),
            title="Hot Topics",
            border_style="magenta",
        )
        result.append(topics_panel)

    return result


def format_as_json(papers: list[Paper]) -> str:
    """Serialize papers to a JSON string."""
    return json.dumps(
        [p.to_dict() for p in papers],
        ensure_ascii=False,
        indent=2,
    )
