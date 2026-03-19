"""Tests for the fieldmap module."""

from __future__ import annotations

import json
from datetime import datetime

from arxiv_curator.fieldmap import FieldMap, build_field_map, field_map_to_json
from arxiv_curator.models import EnrichedPaper


def _make_paper(
    title: str = "Test Paper",
    abstract: str = "Some abstract",
    year: int = 2025,
    venue: str = "",
    citation_count: int = 0,
    code_url: str = "",
) -> EnrichedPaper:
    return EnrichedPaper(
        title=title,
        authors=["Author A"],
        abstract=abstract,
        published=datetime(year, 6, 1),
        arxiv_url=f"http://arxiv.org/abs/{year}01.00001v1",
        pdf_url=f"http://arxiv.org/pdf/{year}01.00001v1",
        categories=["cs.CV"],
        citation_count=citation_count,
        venue=venue,
        is_open_access=False,
        code_url=code_url,
    )


class TestBuildFieldMap:
    def test_empty_list(self) -> None:
        fm = build_field_map([])
        assert fm.total_papers == 0
        assert fm.papers_with_code == 0
        assert fm.papers_without_code == 0
        assert fm.entries == []
        assert fm.top_venues == {}
        assert fm.yearly_counts == {}

    def test_github_url_in_abstract(self) -> None:
        paper = _make_paper(
            abstract="Code at https://github.com/user/repo for details."
        )
        fm = build_field_map([paper])
        assert fm.papers_with_code == 1
        assert fm.entries[0].github_urls == ["https://github.com/user/repo"]

    def test_code_url_from_semantic_scholar(self) -> None:
        paper = _make_paper(code_url="https://paperswithcode.com/paper/foo")
        fm = build_field_map([paper])
        assert fm.papers_with_code == 1
        assert "https://paperswithcode.com/paper/foo" in fm.entries[0].github_urls

    def test_dedup_code_url_and_abstract(self) -> None:
        paper = _make_paper(
            abstract="Code: https://github.com/user/repo",
            code_url="https://github.com/user/repo",
        )
        fm = build_field_map([paper])
        assert fm.entries[0].github_urls == ["https://github.com/user/repo"]

    def test_no_code(self) -> None:
        paper = _make_paper()
        fm = build_field_map([paper])
        assert fm.papers_with_code == 0
        assert fm.papers_without_code == 1

    def test_venue_counting(self) -> None:
        papers = [
            _make_paper(venue="CVPR"),
            _make_paper(venue="CVPR"),
            _make_paper(venue="ICRA"),
        ]
        fm = build_field_map(papers)
        assert fm.top_venues == {"CVPR": 2, "ICRA": 1}

    def test_empty_venue_ignored(self) -> None:
        papers = [_make_paper(venue=""), _make_paper(venue="  ")]
        fm = build_field_map(papers)
        assert fm.top_venues == {}

    def test_yearly_counts(self) -> None:
        papers = [
            _make_paper(year=2024),
            _make_paper(year=2024),
            _make_paper(year=2025),
        ]
        fm = build_field_map(papers)
        assert fm.yearly_counts == {2024: 2, 2025: 1}

    def test_yearly_counts_sorted(self) -> None:
        papers = [
            _make_paper(year=2025),
            _make_paper(year=2023),
            _make_paper(year=2024),
        ]
        fm = build_field_map(papers)
        assert list(fm.yearly_counts.keys()) == [2023, 2024, 2025]


class TestFieldMapToJson:
    def test_valid_json(self) -> None:
        paper = _make_paper(
            abstract="See https://github.com/a/b",
            venue="NeurIPS",
            citation_count=42,
        )
        fm = build_field_map([paper])
        fm.query = "test query"
        result = field_map_to_json(fm)
        data = json.loads(result)

        assert data["query"] == "test query"
        assert data["total_papers"] == 1
        assert data["papers_with_code"] == 1
        assert data["code_ratio"] == "100%"
        assert len(data["entries"]) == 1
        assert data["entries"][0]["has_code"] is True
        assert data["entries"][0]["citations"] == 42

    def test_empty_produces_valid_json(self) -> None:
        fm = build_field_map([])
        fm.query = ""
        result = field_map_to_json(fm)
        data = json.loads(result)
        assert data["total_papers"] == 0
        assert data["code_ratio"] == "0%"
        assert data["entries"] == []
