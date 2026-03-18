"""Output formatters for paper results."""

from __future__ import annotations

import json

from rich.table import Table

from arxiv_curator.models import Paper


def format_as_table(papers: list[Paper]) -> Table:
    """Create a rich Table from a list of papers."""
    table = Table(title="arXiv Papers", show_lines=True)
    table.add_column("#", style="dim", width=4)
    table.add_column("Title", style="bold cyan", max_width=60)
    table.add_column("Authors", max_width=30)
    table.add_column("Published", style="green", width=12)
    table.add_column("Categories", style="magenta", max_width=20)

    for i, paper in enumerate(papers, 1):
        authors_str = ", ".join(paper.authors[:2])
        if len(paper.authors) > 2:
            authors_str += " et al."
        table.add_row(
            str(i),
            paper.title,
            authors_str,
            paper.published.strftime("%Y-%m-%d"),
            ", ".join(paper.categories[:3]),
        )

    return table


def format_as_markdown(papers: list[Paper]) -> str:
    """Format papers as awesome-list style markdown."""
    lines = ["# arXiv Papers\n"]
    for paper in papers:
        lines.append(paper.to_markdown())
    lines.append("")
    return "\n".join(lines)


def format_as_json(papers: list[Paper]) -> str:
    """Serialize papers to a JSON string."""
    return json.dumps(
        [p.to_dict() for p in papers],
        ensure_ascii=False,
        indent=2,
    )
