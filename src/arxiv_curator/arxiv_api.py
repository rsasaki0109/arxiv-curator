"""Wrapper around the arxiv Python package."""

from __future__ import annotations

from datetime import datetime, timezone

import arxiv

from arxiv_curator.models import Paper


def search_papers(
    query: str,
    max_results: int = 20,
    since_date: datetime | None = None,
) -> list[Paper]:
    """Search arXiv for papers matching *query*.

    Parameters
    ----------
    query:
        arXiv search query (supports boolean operators).
    max_results:
        Maximum number of results to return.
    since_date:
        If given, only return papers published on or after this date.

    Returns
    -------
    list[Paper]
    """
    client = arxiv.Client()
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending,
    )

    papers: list[Paper] = []
    for result in client.results(search):
        published = result.published
        if since_date and published < since_date.replace(tzinfo=timezone.utc):
            continue
        papers.append(
            Paper(
                title=result.title,
                authors=[str(a) for a in result.authors],
                abstract=result.summary,
                published=published,
                arxiv_url=result.entry_id,
                pdf_url=result.pdf_url or "",
                categories=result.categories,
            )
        )

    return papers
