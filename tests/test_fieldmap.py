"""Tests for the fieldmap module."""

from __future__ import annotations

import json
from datetime import datetime

from arxiv_curator.fieldmap import (
    FieldMap,
    build_field_map,
    field_map_to_json,
    field_map_to_markdown,
    _extract_keywords,
)
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

    def test_json_includes_new_fields(self) -> None:
        papers = [
            _make_paper(title="SLAM Visual Odometry", citation_count=100),
            _make_paper(title="SLAM Dense Mapping", citation_count=50),
        ]
        fm = build_field_map(papers)
        fm.query = "SLAM"
        result = field_map_to_json(fm)
        data = json.loads(result)

        assert "topic_clusters" in data
        assert "code_ratio_by_year" in data
        assert "key_papers" in data
        assert "gaps" in data


class TestExtractKeywords:
    def test_removes_stopwords(self) -> None:
        keywords = _extract_keywords("A New Method for Visual SLAM")
        assert "new" not in keywords
        assert "for" not in keywords
        assert "method" in keywords
        assert "visual" in keywords
        assert "slam" in keywords

    def test_short_words_excluded(self) -> None:
        keywords = _extract_keywords("An AI in VR")
        # Words shorter than 3 chars are excluded
        assert "ai" not in keywords
        assert "vr" not in keywords

    def test_lowercase(self) -> None:
        keywords = _extract_keywords("Transformer SLAM")
        assert "transformer" in keywords
        assert "slam" in keywords


class TestTopicClusters:
    def test_clusters_group_common_keywords(self) -> None:
        papers = [
            _make_paper(title="Visual SLAM with Transformers"),
            _make_paper(title="Dense Visual SLAM"),
            _make_paper(title="Transformer Based Object Detection"),
        ]
        fm = build_field_map(papers)
        # "visual" appears in 2 papers, "slam" in 2
        assert "visual" in fm.topic_clusters
        assert "slam" in fm.topic_clusters
        assert len(fm.topic_clusters["visual"]) == 2
        assert len(fm.topic_clusters["slam"]) == 2

    def test_single_occurrence_excluded(self) -> None:
        papers = [
            _make_paper(title="Visual SLAM"),
            _make_paper(title="Object Detection"),
        ]
        fm = build_field_map(papers)
        # "visual", "slam", "object", "detection" each appear once
        assert "visual" not in fm.topic_clusters
        assert "slam" not in fm.topic_clusters

    def test_empty_papers(self) -> None:
        fm = build_field_map([])
        assert fm.topic_clusters == {}


class TestCodeRatioByYear:
    def test_code_ratio_tracks_yearly(self) -> None:
        papers = [
            _make_paper(year=2024, code_url="https://github.com/a/b"),
            _make_paper(year=2024),
            _make_paper(year=2025, code_url="https://github.com/c/d"),
            _make_paper(year=2025, code_url="https://github.com/e/f"),
        ]
        fm = build_field_map(papers)
        assert 2024 in fm.code_ratio_by_year
        assert 2025 in fm.code_ratio_by_year
        # 2024: 1 with code, 2 total
        assert fm.code_ratio_by_year[2024] == (1, 2)
        # 2025: 2 with code, 2 total
        assert fm.code_ratio_by_year[2025] == (2, 2)

    def test_no_code_year(self) -> None:
        papers = [_make_paper(year=2024), _make_paper(year=2024)]
        fm = build_field_map(papers)
        assert fm.code_ratio_by_year[2024] == (0, 2)

    def test_empty(self) -> None:
        fm = build_field_map([])
        assert fm.code_ratio_by_year == {}


class TestKeyPapers:
    def test_top_by_citations(self) -> None:
        papers = [
            _make_paper(title="Low", citation_count=5),
            _make_paper(title="High", citation_count=100),
            _make_paper(title="Mid", citation_count=50),
        ]
        fm = build_field_map(papers)
        # key_papers should be indices sorted by citation count desc
        assert len(fm.key_papers) == 3  # top 5 but only 3 papers
        # First key paper should be index 1 (High, 100 citations)
        assert fm.key_papers[0] == 1
        # Second should be index 2 (Mid, 50 citations)
        assert fm.key_papers[1] == 2

    def test_max_five(self) -> None:
        papers = [_make_paper(citation_count=i) for i in range(10)]
        fm = build_field_map(papers)
        assert len(fm.key_papers) == 5


class TestGapAnalysis:
    def test_low_code_availability_gap(self) -> None:
        papers = [
            _make_paper(year=2024),
            _make_paper(year=2024),
            _make_paper(year=2024),
            _make_paper(year=2024),
            _make_paper(year=2024),
        ]
        fm = build_field_map(papers)
        # 0% code availability should be flagged
        code_gaps = [g for g in fm.gaps if "code available" in g]
        assert len(code_gaps) >= 1
        assert "0%" in code_gaps[0]

    def test_no_gaps_when_all_have_code(self) -> None:
        papers = [
            _make_paper(
                year=2024,
                code_url=f"https://github.com/user/repo{i}",
            )
            for i in range(5)
        ]
        fm = build_field_map(papers)
        code_gaps = [g for g in fm.gaps if "code available" in g]
        assert len(code_gaps) == 0

    def test_empty_papers_no_gaps(self) -> None:
        fm = build_field_map([])
        assert fm.gaps == []


class TestFieldMapToMarkdown:
    def test_contains_summary(self) -> None:
        paper = _make_paper(citation_count=10)
        fm = build_field_map([paper])
        fm.query = "SLAM"
        md = field_map_to_markdown(fm)
        assert "# Field Map: SLAM" in md
        assert "Total papers" in md
        assert "Papers with code" in md

    def test_contains_sections(self) -> None:
        papers = [
            _make_paper(
                title="Visual SLAM Method",
                year=2024,
                citation_count=100,
                venue="CVPR",
                code_url="https://github.com/a/b",
            ),
            _make_paper(
                title="Visual SLAM Approach",
                year=2025,
                citation_count=50,
                venue="ICRA",
            ),
        ]
        fm = build_field_map(papers)
        fm.query = "visual SLAM"
        md = field_map_to_markdown(fm)

        assert "## Top Venues" in md
        assert "## Yearly Distribution" in md
        assert "## Topic Clusters" in md
        assert "## Code Availability Trend" in md
        assert "## Key Papers" in md
        assert "## Top Papers by Citations" in md

    def test_markdown_is_string(self) -> None:
        fm = build_field_map([])
        fm.query = "test"
        md = field_map_to_markdown(fm)
        assert isinstance(md, str)

    def test_empty_field_map(self) -> None:
        fm = build_field_map([])
        fm.query = "empty"
        md = field_map_to_markdown(fm)
        assert "# Field Map: empty" in md
        assert "Total papers" in md
