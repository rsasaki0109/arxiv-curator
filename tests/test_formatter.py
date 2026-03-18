"""Tests for the formatter module."""

import json
from datetime import datetime, timezone

from rich.table import Table

from arxiv_curator.formatter import format_as_json, format_as_markdown, format_as_table
from arxiv_curator.models import EnrichedPaper, Paper


def _make_paper(title: str = "Test Paper") -> Paper:
    return Paper(
        title=title,
        authors=["Alice", "Bob", "Charlie"],
        abstract="An abstract.",
        published=datetime(2025, 3, 15, tzinfo=timezone.utc),
        arxiv_url="https://arxiv.org/abs/2503.12345v1",
        pdf_url="https://arxiv.org/pdf/2503.12345v1",
        categories=["cs.CV", "cs.RO"],
    )


def _make_enriched_paper(title: str = "Enriched Paper") -> EnrichedPaper:
    base = _make_paper(title)
    return EnrichedPaper.from_paper(
        base,
        citation_count=42,
        venue="CVPR 2025",
        is_open_access=True,
        code_url="https://github.com/example/repo",
    )


class TestFormatAsTable:
    def test_returns_rich_table(self):
        table = format_as_table([_make_paper()])
        assert isinstance(table, Table)

    def test_table_with_multiple_papers(self):
        papers = [_make_paper("Paper A"), _make_paper("Paper B")]
        table = format_as_table(papers)
        assert isinstance(table, Table)
        assert table.row_count == 2

    def test_table_with_enriched_papers(self):
        papers = [_make_enriched_paper()]
        table = format_as_table(papers)
        assert isinstance(table, Table)
        # Enriched table has extra columns: Citations, Venue, OA
        col_names = [c.header for c in table.columns]
        assert "Citations" in col_names
        assert "Venue" in col_names

    def test_empty_list(self):
        table = format_as_table([])
        assert isinstance(table, Table)
        assert table.row_count == 0


class TestFormatAsMarkdown:
    def test_returns_markdown_string(self):
        md = format_as_markdown([_make_paper()])
        assert isinstance(md, str)
        assert md.startswith("# arXiv Papers")
        assert "Test Paper" in md

    def test_contains_paper_link(self):
        md = format_as_markdown([_make_paper()])
        assert "https://arxiv.org/abs/2503.12345v1" in md

    def test_enriched_paper_includes_extras(self):
        md = format_as_markdown([_make_enriched_paper()])
        assert "Citations: 42" in md
        assert "CVPR 2025" in md

    def test_empty_list(self):
        md = format_as_markdown([])
        assert "# arXiv Papers" in md


class TestFormatAsJson:
    def test_returns_valid_json(self):
        raw = format_as_json([_make_paper()])
        data = json.loads(raw)
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["title"] == "Test Paper"

    def test_json_has_expected_keys(self):
        raw = format_as_json([_make_paper()])
        data = json.loads(raw)
        paper = data[0]
        assert "title" in paper
        assert "authors" in paper
        assert "published" in paper
        assert "arxiv_url" in paper

    def test_enriched_paper_json(self):
        raw = format_as_json([_make_enriched_paper()])
        data = json.loads(raw)
        paper = data[0]
        assert paper["citation_count"] == 42
        assert paper["venue"] == "CVPR 2025"

    def test_empty_list(self):
        raw = format_as_json([])
        data = json.loads(raw)
        assert data == []
