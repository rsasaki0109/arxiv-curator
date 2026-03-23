"""CLI interface for arxiv-curator."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from arxiv_curator import __version__
from arxiv_curator.arxiv_api import search_papers
from arxiv_curator.formatter import (
    format_as_json,
    format_as_markdown,
    format_as_table,
    format_digest,
    format_rank_summary,
    format_ranked_table,
)
from arxiv_curator.models import Paper
from arxiv_curator.parser import (
    fetch_readme_content,
    filter_new_papers,
    parse_awesome_readme,
    parse_awesome_url,
)
from arxiv_curator.ranker import compute_summary, rank_papers
from arxiv_curator.semantic_scholar import enrich_papers

app = typer.Typer(
    name="arxiv-curator",
    help="arXiv paper search and curation CLI tool.",
    add_completion=False,
)
console = Console()
err_console = Console(stderr=True)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _parse_since(since: str | None) -> datetime | None:
    """Parse a ``--since`` date string, or exit with a friendly message."""
    if since is None:
        return None
    try:
        return datetime.fromisoformat(since)
    except ValueError:
        console.print(
            f"[red]Invalid date format: '{since}'. Use YYYY-MM-DD.[/red]"
        )
        raise typer.Exit(1)


def _filter_category(papers: list[Paper], category: str | None) -> list[Paper]:
    """Filter papers by arXiv category if given."""
    if category:
        return [p for p in papers if category in p.categories]
    return papers


def _log(fmt: str) -> Console:
    """Return the console for status/progress messages.

    When the output format is JSON, messages go to stderr so that
    stdout contains only valid JSON.
    """
    if fmt == "json":
        return err_console
    return console


def _output_papers(
    papers: list[Paper],
    fmt: str,
    out_console: Console,
) -> None:
    """Render *papers* to *out_console* in the requested format."""
    if fmt == "table":
        out_console.print(format_as_table(papers))
    elif fmt == "json":
        sys.stdout.write(format_as_json(papers) + "\n")
        sys.stdout.flush()
    elif fmt == "markdown":
        sys.stdout.write(format_as_markdown(papers) + "\n")
        sys.stdout.flush()
    else:
        out_console.print(f"[red]Unknown format: {fmt}[/red]")
        raise typer.Exit(1)


def _sort_papers(papers: list[Paper], sort: str) -> list[Paper]:
    """Sort papers by the given criterion."""
    if sort == "date":
        return sorted(papers, key=lambda p: p.published, reverse=True)
    elif sort == "title":
        return sorted(papers, key=lambda p: p.title.lower())
    # "relevance" — keep the original order from arXiv API
    return papers


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"arxiv-curator {__version__}")
        raise typer.Exit()


# ---------------------------------------------------------------------------
# App-level callback (--version)
# ---------------------------------------------------------------------------


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        help="Show version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    """arXiv paper search and curation CLI tool."""


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


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
    category: Optional[str] = typer.Option(
        None, "--category", "-c", help="Filter by arXiv category (e.g. cs.CV, cs.RO)"
    ),
    sort: str = typer.Option(
        "relevance", "--sort", help="Sort by: relevance, date, title"
    ),
    enrich: bool = typer.Option(
        False, "--enrich", "-e", help="Enrich with Semantic Scholar data"
    ),
) -> None:
    """Search arXiv for papers matching keywords."""
    query = " AND ".join(keywords)
    since_date = _parse_since(since)
    log = _log(fmt)

    with log.status("Searching arXiv..."):
        papers = search_papers(query, max_results=max_results, since_date=since_date, category=category)

    # Safety-net post-filter (API query should already restrict category)
    papers = _filter_category(papers, category)

    if not papers:
        log.print("[yellow]No papers found.[/yellow]")
        raise typer.Exit()

    papers = _sort_papers(papers, sort)

    log.print(f"Found [bold green]{len(papers)}[/bold green] papers.\n")

    if enrich:
        with log.status("Enriching with Semantic Scholar..."):
            papers = enrich_papers(papers)

    _output_papers(papers, fmt, console)


@app.command()
def suggest(
    url: str = typer.Argument(..., help="GitHub repository URL"),
    since: Optional[str] = typer.Option(
        None, "--since", "-s", help="Only papers after this date (YYYY-MM-DD)"
    ),
    max_results: int = typer.Option(20, "--max-results", "-n", help="Max results"),
    fmt: str = typer.Option(
        "table", "--format", "-f", help="Output format: table, json, markdown"
    ),
    sort: str = typer.Option(
        "relevance", "--sort", help="Sort by: relevance, date, title"
    ),
    append_to: Optional[Path] = typer.Option(
        None, "--append-to", help="Append markdown entries to the specified file"
    ),
    enrich: bool = typer.Option(
        False, "--enrich", "-e", help="Enrich with Semantic Scholar data"
    ),
) -> None:
    """Suggest new arXiv papers for a GitHub repository.

    Extracts keywords from the repo name, searches arXiv, and filters
    out papers already present in the README.
    """
    log = _log(fmt)
    keywords = parse_awesome_url(url)
    if not keywords:
        log.print("[red]Could not extract keywords from URL.[/red]")
        raise typer.Exit(1)

    log.print(f"Extracted keywords: [bold]{', '.join(keywords)}[/bold]")

    # Fetch README to find existing papers
    existing: set[str] = set()
    readme_text = fetch_readme_content(url)
    if readme_text:
        existing = parse_awesome_readme(readme_text)
        log.print(
            f"Found [bold]{len(existing)}[/bold] existing entries in README."
        )
    else:
        log.print("[yellow]Could not fetch README; skipping dedup.[/yellow]")

    query = " AND ".join(keywords)
    since_date = _parse_since(since)

    with log.status("Searching arXiv..."):
        papers = search_papers(query, max_results=max_results, since_date=since_date)

    # Deduplicate using shared helper
    new_papers = filter_new_papers(papers, existing)

    if not new_papers:
        log.print("[yellow]No new papers found.[/yellow]")
        raise typer.Exit()

    new_papers = _sort_papers(new_papers, sort)

    log.print(
        f"[bold green]{len(new_papers)}[/bold green] new papers "
        f"(filtered {len(papers) - len(new_papers)} duplicates).\n"
    )

    if enrich:
        with log.status("Enriching with Semantic Scholar..."):
            new_papers = enrich_papers(new_papers)

    _output_papers(new_papers, fmt, console)

    # Append to file if requested
    if append_to:
        md_lines = [p.to_markdown() for p in new_papers]
        md_content = "\n".join(md_lines) + "\n"
        with open(append_to, "a", encoding="utf-8") as f:
            f.write(md_content)
        console.print(
            f"\nAppended [bold green]{len(new_papers)}[/bold green] entries to {append_to}"
        )

    # Summary hint
    if fmt != "markdown" and not append_to:
        console.print(
            f"\n[dim]Found {len(new_papers)} new papers not in the awesome list. "
            "Run with --format markdown to get copy-paste ready output, "
            "or --append-to FILE to save them.[/dim]"
        )


@app.command(name="enrich")
def enrich_cmd(
    keywords: list[str] = typer.Argument(..., help="Search keywords"),
    since: Optional[str] = typer.Option(
        None, "--since", "-s", help="Only papers after this date (YYYY-MM-DD)"
    ),
    max_results: int = typer.Option(20, "--max-results", "-n", help="Max results"),
    fmt: str = typer.Option(
        "table", "--format", "-f", help="Output format: table, json, markdown"
    ),
    category: Optional[str] = typer.Option(
        None, "--category", "-c", help="Filter by arXiv category (e.g. cs.CV, cs.RO)"
    ),
) -> None:
    """Search arXiv and enrich results with Semantic Scholar data.

    Searches arXiv for papers, then queries Semantic Scholar for each
    paper to add citation counts, venue, and open access information.
    """
    query = " AND ".join(keywords)
    since_date = _parse_since(since)
    log = _log(fmt)

    with log.status("Searching arXiv..."):
        papers = search_papers(query, max_results=max_results, since_date=since_date, category=category)

    papers = _filter_category(papers, category)

    if not papers:
        log.print("[yellow]No papers found.[/yellow]")
        raise typer.Exit()

    log.print(f"Found [bold green]{len(papers)}[/bold green] papers on arXiv.\n")

    with log.status("Enriching with Semantic Scholar..."):
        enriched = enrich_papers(papers)

    _output_papers(enriched, fmt, console)


@app.command()
def export(
    keywords: list[str] = typer.Argument(..., help="Search keywords"),
    output: Path = typer.Option(..., "--output", "-o", help="Output file path"),
    since: Optional[str] = typer.Option(
        None, "--since", "-s", help="Only papers after this date (YYYY-MM-DD)"
    ),
    max_results: int = typer.Option(20, "--max-results", "-n", help="Max results"),
    category: Optional[str] = typer.Option(
        None, "--category", "-c", help="Filter by arXiv category (e.g. cs.CV, cs.RO)"
    ),
) -> None:
    """Export arXiv search results to a file.

    File format is determined by extension (.md for markdown, .json for JSON).
    """
    query = " AND ".join(keywords)
    since_date = _parse_since(since)

    with console.status("Searching arXiv..."):
        papers = search_papers(query, max_results=max_results, since_date=since_date, category=category)

    papers = _filter_category(papers, category)

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


@app.command()
def watch(
    keywords: Optional[list[str]] = typer.Argument(None, help="Search keywords"),
    output_dir: Path = typer.Option(
        ".", "--output-dir", "-o", help="Directory to store results JSON"
    ),
    days: int = typer.Option(7, "--days", "-d", help="Look back N days"),
    max_results: int = typer.Option(50, "--max-results", "-n", help="Max results"),
    category: Optional[str] = typer.Option(
        None, "--category", "-c", help="Filter by arXiv category (e.g. cs.CV, cs.RO)"
    ),
    from_awesome: Optional[str] = typer.Option(
        None,
        "--from-awesome",
        help="Extract keywords from an awesome-list GitHub URL",
    ),
) -> None:
    """Watch arXiv for new papers (designed for periodic runs).

    Searches for papers from the last N days, deduplicates against
    previously seen results, and appends new papers to a JSON file.

    You can provide keywords directly or use --from-awesome to extract
    them from a GitHub awesome-list URL.
    """
    # Resolve keywords from --from-awesome or positional args
    resolved_keywords: list[str]
    if from_awesome:
        resolved_keywords = parse_awesome_url(from_awesome)
        if not resolved_keywords:
            console.print("[red]Could not extract keywords from URL.[/red]")
            raise typer.Exit(1)
        console.print(
            f"Extracted keywords from awesome list: "
            f"[bold]{', '.join(resolved_keywords)}[/bold]"
        )
    elif keywords:
        resolved_keywords = keywords
    else:
        console.print("[red]Provide keywords or --from-awesome URL.[/red]")
        raise typer.Exit(1)

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_name = "_".join(resolved_keywords).replace(" ", "_").lower()
    output_file = output_dir / f"watch_{safe_name}.json"

    # Load existing papers
    existing_ids: set[str] = set()
    existing_papers: list[dict] = []
    if output_file.exists():
        try:
            existing_papers = json.loads(output_file.read_text(encoding="utf-8"))
            for p in existing_papers:
                existing_ids.add(p.get("arxiv_url", ""))
        except (json.JSONDecodeError, KeyError):
            console.print(
                f"[yellow]Warning: {output_file} contains corrupt JSON. "
                f"Starting fresh.[/yellow]"
            )

    since_date = datetime.now(tz=timezone.utc) - timedelta(days=days)
    query = " AND ".join(resolved_keywords)

    with console.status("Searching arXiv..."):
        papers = search_papers(query, max_results=max_results, since_date=since_date, category=category)

    papers = _filter_category(papers, category)

    new_papers = [p for p in papers if p.arxiv_url not in existing_ids]

    if new_papers:
        all_papers = existing_papers + [p.to_dict() for p in new_papers]
        # Use plain print() to avoid Rich markup in JSON data
        output_file.write_text(
            json.dumps(all_papers, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    console.print(
        f"Found [bold green]{len(new_papers)}[/bold green] new papers "
        f"(total {len(existing_papers) + len(new_papers)} in {output_file})."
    )


@app.command()
def rank(
    keywords: list[str] = typer.Argument(..., help="Search keywords"),
    since: Optional[str] = typer.Option(
        None, "--since", "-s", help="Only papers after this date (YYYY-MM-DD)"
    ),
    max_results: int = typer.Option(20, "--max-results", "-n", help="Max results"),
    category: Optional[str] = typer.Option(
        None, "--category", "-c", help="Filter by arXiv category (e.g. cs.CV, cs.RO)"
    ),
    top: int = typer.Option(10, "--top", "-t", help="Show top N papers"),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Save results as JSON file with scoring details"
    ),
) -> None:
    """Rank papers by relevance: citations, recency, code availability, venue.

    Searches arXiv, enriches via Semantic Scholar, and scores each paper
    to surface "今読むべき論文" (papers you should read now).
    """
    query = " AND ".join(keywords)
    since_date = _parse_since(since)

    with console.status("Searching arXiv (by relevance)..."):
        papers = search_papers(query, max_results=max_results, since_date=since_date, sort_by="relevance", category=category)

    papers = _filter_category(papers, category)

    if not papers:
        console.print("[yellow]No papers found.[/yellow]")
        raise typer.Exit()

    console.print(f"Found [bold green]{len(papers)}[/bold green] papers on arXiv.\n")

    with console.status("Enriching with Semantic Scholar..."):
        enriched = enrich_papers(papers)

    ranked = rank_papers(enriched)
    display_ranked = ranked[:top]

    console.print(format_ranked_table(display_ranked))

    # Summary statistics
    summary = compute_summary(ranked)
    console.print()
    console.print(format_rank_summary(summary))

    console.print(
        f"\n[dim]Showing top {len(display_ranked)} of {len(enriched)} papers, "
        "ranked by citations, recency, code availability, and venue.[/dim]"
    )

    # Save JSON output if requested
    if output:
        ranked_data = []
        for rp in ranked:
            entry = rp.paper.to_dict()
            entry["score"] = round(rp.score, 1)
            entry["percentile"] = round(rp.percentile, 1)
            entry["category"] = rp.category
            entry["reasons"] = rp.reasons
            ranked_data.append(entry)
        result = {
            "query": query,
            "total_papers": len(ranked),
            "summary": summary,
            "papers": ranked_data,
        }
        output.write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        console.print(
            f"\nSaved ranking results to [bold green]{output}[/bold green]"
        )


@app.command(name="map")
def field_map_cmd(
    keywords: list[str] = typer.Argument(..., help="Research topic keywords"),
    since: Optional[str] = typer.Option(
        None, "--since", "-s", help="Only papers after this date (YYYY-MM-DD)"
    ),
    max_results: int = typer.Option(
        50, "--max-results", "-n", help="Max results"
    ),
    category: Optional[str] = typer.Option(
        None, "--category", "-c", help="Filter by arXiv category (e.g. cs.CV, cs.RO)"
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Output file (JSON or Markdown based on extension)"
    ),
    markdown: bool = typer.Option(
        False, "--markdown", help="Output as Markdown instead of Rich tables"
    ),
) -> None:
    """Build a field map: papers, code, venues, and trends for a research topic."""
    from arxiv_curator.fieldmap import (
        build_field_map,
        field_map_to_json,
        field_map_to_markdown,
    )
    from arxiv_curator.formatter import format_field_map

    query = " AND ".join(keywords)
    since_date = _parse_since(since)

    with console.status("Searching arXiv (by relevance)..."):
        papers = search_papers(query, max_results=max_results, since_date=since_date, sort_by="relevance", category=category)

    papers = _filter_category(papers, category)

    if not papers:
        console.print("[yellow]No papers found.[/yellow]")
        raise typer.Exit()

    console.print(f"Found [bold green]{len(papers)}[/bold green] papers on arXiv.\n")

    with console.status("Enriching with Semantic Scholar..."):
        enriched = enrich_papers(papers)

    fm = build_field_map(enriched)
    fm.query = query

    if markdown:
        # Output as Markdown
        md = field_map_to_markdown(fm)
        print(md)
    else:
        # Display Rich summary
        for renderable in format_field_map(fm):
            console.print(renderable)
            console.print()

    # Save to file if requested
    if output:
        suffix = output.suffix.lower()
        if suffix in (".md", ".markdown"):
            output.write_text(field_map_to_markdown(fm), encoding="utf-8")
        else:
            output.write_text(field_map_to_json(fm), encoding="utf-8")
        console.print(
            f"\nSaved field map to [bold green]{output}[/bold green]"
        )


@app.command()
def digest(
    keywords: list[str] = typer.Argument(..., help="Search keywords"),
    days: int = typer.Option(7, "--days", "-d", help="Look back N days"),
    max_results: int = typer.Option(50, "--max-results", "-n", help="Max results"),
    category: Optional[str] = typer.Option(
        None, "--category", "-c", help="Filter by arXiv category (e.g. cs.CV, cs.RO)"
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Save digest as Markdown report"
    ),
    strict: bool = typer.Option(
        False, "--strict", help="Only keep papers with query keywords in title"
    ),
) -> None:
    """Generate a weekly field digest: must-reads, hidden gems, and trends.

    One command to get a newsletter-style summary of recent papers in your field.
    Searches arXiv, enriches via Semantic Scholar, ranks papers, and presents
    a digest with top papers, hidden gems, and hot topics.
    """
    from arxiv_curator.digest import build_digest, digest_to_markdown

    query = " AND ".join(keywords)
    period_end = datetime.now(tz=timezone.utc)
    period_start = period_end - timedelta(days=days)

    with console.status("Searching arXiv..."):
        papers = search_papers(
            query,
            max_results=max_results,
            since_date=period_start,
            sort_by="date",
            category=category,
        )

    papers = _filter_category(papers, category)

    # Strict mode: only keep papers where at least one query keyword appears in title
    if strict:
        query_keywords = [kw.lower() for kw in keywords]
        papers = [
            p for p in papers
            if any(qk in p.title.lower() for qk in query_keywords)
        ]
        if papers:
            console.print(
                f"[dim]Strict mode: kept {len(papers)} papers with query keywords in title.[/dim]"
            )

    if not papers:
        console.print("[yellow]No papers found.[/yellow]")
        raise typer.Exit()

    console.print(f"Found [bold green]{len(papers)}[/bold green] papers on arXiv.\n")

    with console.status("Enriching with Semantic Scholar..."):
        enriched = enrich_papers(papers)

    ranked = rank_papers(enriched)

    dg = build_digest(enriched, ranked, query, period_start, period_end)

    for renderable in format_digest(dg):
        console.print(renderable)
        console.print()

    # Save Markdown report if requested
    if output:
        md = digest_to_markdown(dg)
        output.write_text(md, encoding="utf-8")
        console.print(
            f"\nSaved digest to [bold green]{output}[/bold green]"
        )


if __name__ == "__main__":
    app()
