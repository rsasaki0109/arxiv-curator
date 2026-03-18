"""Tests for CLI enhancements: sort, append-to, watch --from-awesome."""

from datetime import datetime, timezone
from pathlib import Path

from arxiv_curator.cli import _sort_papers
from arxiv_curator.models import Paper


def _make_paper(title: str, published: datetime) -> Paper:
    return Paper(
        title=title,
        authors=["Author"],
        abstract="Abstract",
        published=published,
        arxiv_url=f"https://arxiv.org/abs/0000.00000",
        pdf_url="",
        categories=["cs.CV"],
    )


class TestSortPapers:
    def test_sort_by_date(self):
        old = _make_paper("Old", datetime(2024, 1, 1, tzinfo=timezone.utc))
        new = _make_paper("New", datetime(2025, 6, 1, tzinfo=timezone.utc))
        mid = _make_paper("Mid", datetime(2025, 3, 1, tzinfo=timezone.utc))
        result = _sort_papers([old, new, mid], "date")
        assert [p.title for p in result] == ["New", "Mid", "Old"]

    def test_sort_by_title(self):
        a = _make_paper("Alpha", datetime(2025, 1, 1, tzinfo=timezone.utc))
        c = _make_paper("Charlie", datetime(2025, 1, 1, tzinfo=timezone.utc))
        b = _make_paper("Bravo", datetime(2025, 1, 1, tzinfo=timezone.utc))
        result = _sort_papers([c, a, b], "title")
        assert [p.title for p in result] == ["Alpha", "Bravo", "Charlie"]

    def test_sort_by_relevance_preserves_order(self):
        papers = [
            _make_paper("Z", datetime(2025, 1, 1, tzinfo=timezone.utc)),
            _make_paper("A", datetime(2025, 6, 1, tzinfo=timezone.utc)),
        ]
        result = _sort_papers(papers, "relevance")
        assert [p.title for p in result] == ["Z", "A"]
