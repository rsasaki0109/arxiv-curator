"""Tests for Semantic Scholar API integration."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from arxiv_curator.models import EnrichedPaper, Paper
from arxiv_curator.semantic_scholar import (
    _extract_arxiv_id,
    enrich_paper,
    enrich_papers,
)


def _make_paper(**kwargs) -> Paper:
    defaults = {
        "title": "Test Paper",
        "authors": ["Alice", "Bob"],
        "abstract": "A test abstract.",
        "published": datetime(2025, 1, 15, tzinfo=timezone.utc),
        "arxiv_url": "http://arxiv.org/abs/2501.12345v1",
        "pdf_url": "http://arxiv.org/pdf/2501.12345v1",
        "categories": ["cs.CV"],
    }
    defaults.update(kwargs)
    return Paper(**defaults)


class TestExtractArxivId:
    def test_standard_url(self):
        assert _extract_arxiv_id("http://arxiv.org/abs/2501.12345v1") == "2501.12345"

    def test_five_digit_id(self):
        assert _extract_arxiv_id("http://arxiv.org/abs/2603.17165v1") == "2603.17165"

    def test_no_match(self):
        assert _extract_arxiv_id("https://example.com/paper") is None


class TestEnrichPaper:
    @patch("arxiv_curator.semantic_scholar.requests.get")
    def test_successful_enrichment(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "citationCount": 42,
            "venue": "CVPR",
            "year": 2025,
            "isOpenAccess": True,
            "openAccessPdf": {"url": "https://example.com/paper.pdf"},
            "externalIds": {"ArXiv": "2501.12345", "DOI": "10.1234/test"},
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        paper = _make_paper()
        enriched = enrich_paper(paper)

        assert isinstance(enriched, EnrichedPaper)
        assert enriched.citation_count == 42
        assert enriched.venue == "CVPR"
        assert enriched.is_open_access is True
        assert enriched.title == paper.title
        assert enriched.authors == paper.authors

    @patch("arxiv_curator.semantic_scholar.requests.get")
    def test_paper_not_found_returns_defaults(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp

        paper = _make_paper()
        enriched = enrich_paper(paper)

        assert isinstance(enriched, EnrichedPaper)
        assert enriched.citation_count == 0
        assert enriched.venue == ""
        assert enriched.is_open_access is False

    @patch("arxiv_curator.semantic_scholar.requests.get")
    def test_network_error_returns_defaults(self, mock_get):
        import requests

        mock_get.side_effect = requests.ConnectionError("Network error")

        paper = _make_paper()
        enriched = enrich_paper(paper)

        assert isinstance(enriched, EnrichedPaper)
        assert enriched.citation_count == 0

    def test_no_arxiv_id_returns_defaults(self):
        paper = _make_paper(arxiv_url="https://example.com/no-id")
        enriched = enrich_paper(paper)

        assert isinstance(enriched, EnrichedPaper)
        assert enriched.citation_count == 0

    @patch("arxiv_curator.semantic_scholar.requests.get")
    def test_papers_with_code_url(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "citationCount": 10,
            "venue": "",
            "year": 2025,
            "isOpenAccess": False,
            "openAccessPdf": None,
            "externalIds": {
                "ArXiv": "2501.12345",
                "PapersWithCode": "test-paper",
            },
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        paper = _make_paper()
        enriched = enrich_paper(paper)

        assert enriched.code_url == "https://paperswithcode.com/paper/test-paper"


class TestEnrichPapers:
    @patch("arxiv_curator.semantic_scholar.time.sleep")
    @patch("arxiv_curator.semantic_scholar.enrich_paper")
    def test_enriches_all_papers_with_delay(self, mock_enrich, mock_sleep):
        papers = [_make_paper(title=f"Paper {i}") for i in range(3)]
        mock_enrich.side_effect = [
            EnrichedPaper.from_paper(p, citation_count=i)
            for i, p in enumerate(papers)
        ]

        results = enrich_papers(papers)

        assert len(results) == 3
        assert results[0].citation_count == 0
        assert results[1].citation_count == 1
        assert results[2].citation_count == 2
        # Sleep called between requests (not before the first)
        assert mock_sleep.call_count == 2


class TestEnrichedPaper:
    def test_from_paper(self):
        paper = _make_paper()
        enriched = EnrichedPaper.from_paper(paper, citation_count=5, venue="ICRA")
        assert enriched.title == paper.title
        assert enriched.citation_count == 5
        assert enriched.venue == "ICRA"

    def test_to_markdown_with_extras(self):
        paper = _make_paper()
        enriched = EnrichedPaper.from_paper(
            paper, citation_count=100, venue="NeurIPS"
        )
        md = enriched.to_markdown()
        assert "Citations: 100" in md
        assert "NeurIPS" in md

    def test_to_markdown_no_extras(self):
        paper = _make_paper()
        enriched = EnrichedPaper.from_paper(paper)
        md = enriched.to_markdown()
        assert "Citations" not in md

    def test_to_dict_includes_enriched_fields(self):
        paper = _make_paper()
        enriched = EnrichedPaper.from_paper(paper, citation_count=7, venue="IROS")
        d = enriched.to_dict()
        assert d["citation_count"] == 7
        assert d["venue"] == "IROS"
        assert d["is_open_access"] is False
