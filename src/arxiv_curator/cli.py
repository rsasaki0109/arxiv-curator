"""CLI interface for arxiv-curator."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests
import typer
from rich.console import Console

from arxiv_curator.arxiv_api import search_papers
from arxiv_curator.formatter import format_as_json, format_as_markdown, format_as_table
from arxiv_curator.parser import parse_awesome_readme, parse_awesome_url

app = typer.Typer(
    name="arxiv-curator",
    help="arXiv paper search and curation CLI tool.",
    add_completion=False,
)
console = Console()


@app.command()
def search(
    keywords: list[str] = typer.Argument(..., help="Search keywords"),
    since: Optional[str] = typer.Option(
        None, "--since", "-s", help="Only papers after this date (YYYY-MM-DD)"
    ),
    max_results: int = typer.Option(20, "--max-results", "-n", help="Max results"),
    fmt: str = typer.Option(
        "table", "--format", "-f", help="Output format: table, json, markdown"
    ),
) -> None:
    """Search arXiv for papers matching keywords."""
    query = " AND ".join(keywords)
    since_date = None
    if since:
        since_date = datetime.fromisoformat(since)

    with console.status("Searching arXiv..."):
        papers = search_papers(query, max_results=max_results, since_date=since_date)

    if not papers:
        console.print("[yellow]No papers found.[/yellow]")
        raise typer.Exit()

    console.print(f"Found [bold green]{len(papers)}[/bold green] papers.\n")

    if fmt == "table":
        console.print(format_as_table(papers))
    elif fmt == "json":
        console.print(format_as_json(papers))
    elif fmt == "markdown":
        console.print(format_as_markdown(papers))
    else:
        console.print(f"[red]Unknown format: {fmt}[/red]")
        raise typer.Exit(1)


@app.command()
def suggest(
    url: str = typer.Argument(..., help="GitHub awesome-list URL"),
    since: Optional[str] = typer.Option(
        None, "--since", "-s", help="Only papers after this date (YYYY-MM-DD)"
    ),
    max_results: int = typer.Option(20, "--max-results", "-n", help="Max results"),
    fmt: str = typer.Option(
        "table", "--format", "-f", help="Output format: table, json, markdown"
    ),
) -> None:
    """Suggest new arXiv papers for an awesome-list repository.

    Extracts keywords from the repo name, searches arXiv, and filters
    out papers already present in the README.
    """
    keywords = parse_awesome_url(url)
    if not keywords:
        console.print("[red]Could not extract keywords from URL.[/red]")
        raise typer.Exit(1)

    console.print(f"Extracted keywords: [bold]{', '.join(keywords)}[/bold]")

    # Fetch README to find existing papers
    existing: set[str] = set()
    raw_url = _github_raw_readme_url(url)
    if raw_url:
        try:
            resp = requests.get(raw_url, timeout=15)
            if resp.ok:
                existing = parse_awesome_readme(resp.text)
                console.print(
                    f"Found [bold]{len(existing)}[/bold] existing entries in README."
                )
        except requests.RequestException:
            console.print("[yellow]Could not fetch README; skipping dedup.[/yellow]")

    query = " AND ".join(keywords)
    since_date = None
    if since:
        since_date = datetime.fromisoformat(since)

    with console.status("Searching arXiv..."):
        papers = search_papers(query, max_results=max_results, since_date=since_date)

    # Deduplicate
    new_papers = []
    for p in papers:
        arxiv_id_match = re.search(r"\d{4}\.\d{4,5}", p.arxiv_url)
        arxiv_id = arxiv_id_match.group() if arxiv_id_match else ""
        if p.title.lower() not in existing and arxiv_id not in existing:
            new_papers.append(p)

    if not new_papers:
        console.print("[yellow]No new papers found.[/yellow]")
        raise typer.Exit()

    console.print(
        f"[bold green]{len(new_papers)}[/bold green] new papers "
        f"(filtered {len(papers) - len(new_papers)} duplicates).\n"
    )

    if fmt == "table":
        console.print(format_as_table(new_papers))
    elif fmt == "json":
        console.print(format_as_json(new_papers))
    elif fmt == "markdown":
        console.print(format_as_markdown(new_papers))
    else:
        console.print(f"[red]Unknown format: {fmt}[/red]")
        raise typer.Exit(1)


@app.command()
def export(
    keywords: list[str] = typer.Argument(..., help="Search keywords"),
    output: Path = typer.Option(..., "--output", "-o", help="Output file path"),
    since: Optional[str] = typer.Option(
        None, "--since", "-s", help="Only papers after this date (YYYY-MM-DD)"
    ),
    max_results: int = typer.Option(20, "--max-results", "-n", help="Max results"),
) -> None:
    """Export arXiv search results to a file.

    File format is determined by extension (.md for markdown, .json for JSON).
    """
    query = " AND ".join(keywords)
    since_date = None
    if since:
        since_date = datetime.fromisoformat(since)

    with console.status("Searching arXiv..."):
        papers = search_papers(query, max_results=max_results, since_date=since_date)

    if not papers:
        console.print("[yellow]No papers found.[/yellow]")
        raise typer.Exit()

    suffix = output.suffix.lower()
    if suffix == ".json":
        content = format_as_json(papers)
    elif suffix in (".md", ".markdown"):
        content = format_as_markdown(papers)
    else:
        console.print(f"[red]Unsupported file extension: {suffix}[/red]")
        raise typer.Exit(1)

    output.write_text(content, encoding="utf-8")
    console.print(
        f"Exported [bold green]{len(papers)}[/bold green] papers to {output}"
    )


def _github_raw_readme_url(github_url: str) -> str | None:
    """Convert a GitHub repo URL to a raw README URL."""
    from urllib.parse import urlparse

    parsed = urlparse(github_url)
    path_parts = parsed.path.strip("/").split("/")
    if len(path_parts) < 2:
        return None
    owner, repo = path_parts[0], path_parts[1]
    return f"https://raw.githubusercontent.com/{owner}/{repo}/main/README.md"


if __name__ == "__main__":
    app()
