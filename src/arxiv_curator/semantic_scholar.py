"""Semantic Scholar API integration for enriching paper metadata.

Provides citation counts, venue information, and open access status
that the arXiv API cannot provide.

API docs: https://api.semanticscholar.org/
Rate limit: 100 requests per 5 minutes (without API key).
"""

from __future__ import annotations

import re
import time

import requests

from arxiv_curator.models import EnrichedPaper, Paper

S2_BASE_URL = "https://api.semanticscholar.org/graph/v1"
S2_FIELDS = "citationCount,venue,year,isOpenAccess,openAccessPdf,externalIds"
REQUEST_INTERVAL = 3.0  # seconds between requests (100 req / 5 min without API key)


def _extract_arxiv_id(arxiv_url: str) -> str | None:
    """Extract the arXiv ID (e.g. '2603.17165') from an arXiv URL."""
    match = re.search(r"(\d{4}\.\d{4,5})", arxiv_url)
    return match.group(1) if match else None


def enrich_paper(paper: Paper, timeout: int = 10) -> EnrichedPaper:
    """Enrich a Paper with Semantic Scholar metadata.

    Looks up the paper by arXiv ID and returns an EnrichedPaper with
    citation count, venue, and open access info.

    Returns an EnrichedPaper with default values if the paper is not
    found in Semantic Scholar (e.g. very new papers).
    """
    arxiv_id = _extract_arxiv_id(paper.arxiv_url)
    if not arxiv_id:
        return EnrichedPaper.from_paper(paper)

    url = f"{S2_BASE_URL}/paper/ARXIV:{arxiv_id}"
    max_retries = 3
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, params={"fields": S2_FIELDS}, timeout=timeout)
            if resp.status_code == 404:
                return EnrichedPaper.from_paper(paper)
            if resp.status_code == 429:
                wait = min(2 ** attempt * 5, 30)  # 5s, 10s, 30s
                time.sleep(wait)
                continue
            resp.raise_for_status()
            data = resp.json()
            break
        except (requests.RequestException, ValueError):
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            return EnrichedPaper.from_paper(paper)
    else:
        return EnrichedPaper.from_paper(paper)

    citation_count = data.get("citationCount") or 0
    venue = data.get("venue") or ""
    is_open_access = data.get("isOpenAccess") or False

    # Try to get code URL from externalIds (Papers with Code link via DBLP, etc.)
    code_url = ""
    external_ids = data.get("externalIds") or {}
    if "PapersWithCode" in external_ids:
        pwc_id = external_ids["PapersWithCode"]
        if pwc_id:
            code_url = f"https://paperswithcode.com/paper/{pwc_id}"

    return EnrichedPaper.from_paper(
        paper,
        citation_count=citation_count,
        venue=venue,
        is_open_access=is_open_access,
        code_url=code_url,
    )


def enrich_papers(
    papers: list[Paper], timeout: int = 10
) -> list[EnrichedPaper]:
    """Enrich a list of papers with Semantic Scholar metadata.

    Adds a delay between requests to respect rate limits.
    """
    enriched = []
    for i, paper in enumerate(papers):
        if i > 0:
            time.sleep(REQUEST_INTERVAL)
        enriched.append(enrich_paper(paper, timeout=timeout))
    return enriched
