"""Wrapper around the arxiv Python package."""

from __future__ import annotations

import logging
import urllib.error
from datetime import datetime, timezone

import arxiv

from arxiv_curator.models import Paper

logger = logging.getLogger(__name__)


def _build_query(query: str, category: str | None = None) -> str:
    """Build an arXiv API query string.

    - If *category* is given, prepend ``cat:<category> AND``.
    - If the query looks like a multi-word phrase (contains spaces and no
      explicit field prefix like ``ti:`` or ``all:``), wrap it with a
      ``ti:`` prefix so arXiv searches the title for the exact phrase.
    """
    q = query.strip()

    # If the query is already using arXiv field prefixes, leave it alone.
    has_field_prefix = any(
        q.lower().startswith(p) for p in ("ti:", "au:", "abs:", "all:", "cat:")
    )

    has_boolean = any(op in q.upper() for op in (" AND ", " OR ", " NOT "))

    if not has_field_prefix and not has_boolean and " " in q:
        # Multi-word query – search as an exact phrase in the title field
        # for better relevance, combined with an all-fields search.
        q = f'ti:"{q}" OR all:"{q}"'

    if category:
        q = f"cat:{category} AND ({q})"

    return q


def search_papers(
    query: str,
    max_results: int = 20,
    since_date: datetime | None = None,
    sort_by: str = "date",
    category: str | None = None,
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
    category:
        If given, include the category in the arXiv query so the API
        returns papers from that category directly.

    Returns
    -------
    list[Paper]

    Raises
    ------
    RuntimeError
        If the arXiv API is unreachable or returns an unexpected error.
    """
    api_query = _build_query(query, category)
    client = arxiv.Client()
    sort_criterion = (
        arxiv.SortCriterion.Relevance if sort_by == "relevance"
        else arxiv.SortCriterion.SubmittedDate
    )
    search = arxiv.Search(
        query=api_query,
        max_results=max_results,
        sort_by=sort_criterion,
        sort_order=arxiv.SortOrder.Descending,
    )

    try:
        results = list(client.results(search))
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Failed to reach arXiv API: {exc}") from exc
    except ConnectionError as exc:
        raise RuntimeError(f"Connection error while contacting arXiv: {exc}") from exc
    except arxiv.UnexpectedEmptyPageError as exc:
        logger.warning("arXiv returned an empty page: %s", exc)
        return []
    except arxiv.HTTPError as exc:
        raise RuntimeError(f"arXiv API HTTP error: {exc}") from exc

    papers: list[Paper] = []
    for result in results:
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
