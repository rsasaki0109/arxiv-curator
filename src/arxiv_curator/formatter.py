"""Output formatters for paper results."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from arxiv_curator.models import EnrichedPaper, Paper

if TYPE_CHECKING:
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

        row = [
            str(i),
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
    table = Table(title="Ranked Papers — 今読むべき論文", show_lines=True)
    table.add_column("Rank", style="dim", width=5, justify="right")
    table.add_column("Score", width=7, justify="right")
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

        signals = ", ".join(rp.reasons)
        table.add_row(
            str(i),
            score_str,
            rp.paper.title,
            str(rp.paper.citation_count),
            rp.paper.venue or "-",
            rp.paper.published.strftime("%Y-%m-%d"),
            signals,
        )

    return table


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

    return [summary_panel, venue_table, year_panel, papers_table]


def format_as_json(papers: list[Paper]) -> str:
    """Serialize papers to a JSON string."""
    return json.dumps(
        [p.to_dict() for p in papers],
        ensure_ascii=False,
        indent=2,
    )
