"""Tests for the digest module."""

from datetime import datetime, timedelta, timezone

from arxiv_curator.digest import (
    Digest,
    _count_categories,
    _count_venues,
    _extract_hot_topics,
    _extract_keywords,
    _find_hidden_gems,
    _find_must_reads,
    build_digest,
    digest_to_markdown,
)
from arxiv_curator.models import EnrichedPaper
from arxiv_curator.ranker import RankedPaper, rank_papers


def _make_paper(
    title: str = "Test Paper",
    citation_count: int = 0,
    venue: str = "",
    is_open_access: bool = False,
    code_url: str = "",
    days_old: int = 10,
    categories: list[str] | None = None,
) -> EnrichedPaper:
    """Create an EnrichedPaper for testing."""
    published = datetime.now(timezone.utc) - timedelta(days=days_old)
    return EnrichedPaper(
        title=title,
        authors=["Author A", "Author B"],
        abstract="Abstract text about the paper",
        published=published.replace(tzinfo=None),
        arxiv_url="http://arxiv.org/abs/0000.00000",
        pdf_url="http://arxiv.org/pdf/0000.00000",
        categories=categories or ["cs.CV"],
        citation_count=citation_count,
        venue=venue,
        is_open_access=is_open_access,
        code_url=code_url,
    )


class TestMustReads:
    """Tests for must_reads extraction."""

    def test_top_3_selected(self) -> None:
        papers = [
            _make_paper(title=f"Paper {i}", citation_count=i * 100)
            for i in range(5)
        ]
        ranked = rank_papers(papers)
        must_reads = _find_must_reads(ranked)
        assert len(must_reads) == 3
        # First must-read should be the highest-scoring
        assert must_reads[0].score >= must_reads[1].score
        assert must_reads[1].score >= must_reads[2].score

    def test_fewer_than_3_papers(self) -> None:
        papers = [_make_paper(title="Only one", citation_count=100)]
        ranked = rank_papers(papers)
        must_reads = _find_must_reads(ranked)
        assert len(must_reads) == 1

    def test_empty_list(self) -> None:
        assert _find_must_reads([]) == []


class TestHiddenGems:
    """Tests for hidden gem detection in digest."""

    def test_recent_with_code_low_citations(self) -> None:
        paper = _make_paper(
            title="Gem Paper",
            days_old=5,
            code_url="https://github.com/x/y",
            citation_count=2,
        )
        ranked = rank_papers([paper])
        gems = _find_hidden_gems(ranked)
        assert len(gems) == 1
        assert gems[0].paper.title == "Gem Paper"

    def test_old_paper_not_gem(self) -> None:
        paper = _make_paper(
            title="Old Paper",
            days_old=60,
            code_url="https://github.com/x/y",
            citation_count=2,
        )
        ranked = rank_papers([paper])
        gems = _find_hidden_gems(ranked)
        assert len(gems) == 0

    def test_no_code_not_gem(self) -> None:
        paper = _make_paper(
            title="No Code",
            days_old=5,
            code_url="",
            citation_count=2,
        )
        ranked = rank_papers([paper])
        gems = _find_hidden_gems(ranked)
        assert len(gems) == 0

    def test_high_citations_not_gem(self) -> None:
        paper = _make_paper(
            title="Famous Paper",
            days_old=5,
            code_url="https://github.com/x/y",
            citation_count=50,
        )
        ranked = rank_papers([paper])
        gems = _find_hidden_gems(ranked)
        assert len(gems) == 0


class TestHotTopics:
    """Tests for hot topic extraction."""

    def test_extracts_top_keywords(self) -> None:
        papers = [
            _make_paper(title="Real-Time Gaussian Splatting"),
            _make_paper(title="Gaussian Splatting for Editing"),
            _make_paper(title="Dynamic Gaussian Scenes"),
        ]
        topics = _extract_hot_topics(papers, top_n=3)
        keywords = [kw for kw, _ in topics]
        assert "gaussian" in keywords
        # "gaussian" should appear in all 3
        gaussian_count = next(c for kw, c in topics if kw == "gaussian")
        assert gaussian_count == 3

    def test_stopwords_excluded(self) -> None:
        papers = [
            _make_paper(title="A New Method for the Problem"),
        ]
        topics = _extract_hot_topics(papers, top_n=10)
        keywords = [kw for kw, _ in topics]
        assert "new" not in keywords
        assert "for" not in keywords
        assert "the" not in keywords

    def test_empty_papers(self) -> None:
        assert _extract_hot_topics([], top_n=5) == []


class TestCategoryAndVenueCounts:
    """Tests for category and venue counting."""

    def test_category_counts(self) -> None:
        papers = [
            _make_paper(title="A", categories=["cs.CV", "cs.GR"]),
            _make_paper(title="B", categories=["cs.CV"]),
            _make_paper(title="C", categories=["cs.RO"]),
        ]
        counts = _count_categories(papers)
        assert counts["cs.CV"] == 2
        assert counts["cs.GR"] == 1
        assert counts["cs.RO"] == 1

    def test_venue_counts(self) -> None:
        papers = [
            _make_paper(title="A", venue="CVPR 2025"),
            _make_paper(title="B", venue="CVPR 2025"),
            _make_paper(title="C", venue="ICCV 2025"),
            _make_paper(title="D", venue=""),
        ]
        counts = _count_venues(papers)
        assert counts["CVPR 2025"] == 2
        assert counts["ICCV 2025"] == 1
        assert "" not in counts

    def test_empty_lists(self) -> None:
        assert _count_categories([]) == {}
        assert _count_venues([]) == {}


class TestBuildDigest:
    """Tests for the build_digest function."""

    def test_builds_complete_digest(self) -> None:
        papers = [
            _make_paper(title="Top Paper", citation_count=500, venue="CVPR 2025", categories=["cs.CV"]),
            _make_paper(title="Gem Paper", days_old=3, code_url="https://github.com/x/y", citation_count=0),
            _make_paper(title="Regular Paper", citation_count=10),
        ]
        ranked = rank_papers(papers)
        now = datetime.now(tz=timezone.utc)
        dg = build_digest(
            enriched_papers=papers,
            ranked_papers=ranked,
            query="test query",
            period_start=now - timedelta(days=7),
            period_end=now,
        )

        assert dg.query == "test query"
        assert dg.total_papers == 3
        assert len(dg.must_reads) == 3
        assert dg.papers_with_code == 1
        assert isinstance(dg.hot_topics, list)
        assert isinstance(dg.category_counts, dict)
        assert isinstance(dg.venue_counts, dict)

    def test_empty_papers(self) -> None:
        now = datetime.now(tz=timezone.utc)
        dg = build_digest([], [], "test", now - timedelta(days=7), now)
        assert dg.total_papers == 0
        assert dg.must_reads == []
        assert dg.hidden_gems == []
        assert dg.hot_topics == []


class TestDigestToMarkdown:
    """Tests for Markdown export."""

    def test_contains_header(self) -> None:
        papers = [
            _make_paper(title="Test Paper", citation_count=100, venue="CVPR"),
        ]
        ranked = rank_papers(papers)
        now = datetime.now(tz=timezone.utc)
        dg = build_digest(papers, ranked, "gaussian splatting", now - timedelta(days=7), now)
        md = digest_to_markdown(dg)

        assert "# Weekly Digest: gaussian splatting" in md
        assert "## Overview" in md
        assert "1 new papers" in md

    def test_contains_must_read(self) -> None:
        papers = [
            _make_paper(title="Important Paper", citation_count=500),
        ]
        ranked = rank_papers(papers)
        now = datetime.now(tz=timezone.utc)
        dg = build_digest(papers, ranked, "test", now - timedelta(days=7), now)
        md = digest_to_markdown(dg)

        assert "## Must Read" in md
        assert "Important Paper" in md

    def test_contains_hidden_gems(self) -> None:
        papers = [
            _make_paper(
                title="Hidden Gem Paper",
                days_old=3,
                code_url="https://github.com/x/y",
                citation_count=0,
            ),
        ]
        ranked = rank_papers(papers)
        now = datetime.now(tz=timezone.utc)
        dg = build_digest(papers, ranked, "test", now - timedelta(days=7), now)
        md = digest_to_markdown(dg)

        assert "## Hidden Gems" in md
        assert "Hidden Gem Paper" in md

    def test_contains_hot_topics(self) -> None:
        papers = [
            _make_paper(title="Gaussian Splatting Method A"),
            _make_paper(title="Gaussian Splatting Method B"),
        ]
        ranked = rank_papers(papers)
        now = datetime.now(tz=timezone.utc)
        dg = build_digest(papers, ranked, "test", now - timedelta(days=7), now)
        md = digest_to_markdown(dg)

        assert "## Hot Topics" in md
        assert "gaussian" in md.lower()

    def test_empty_digest_markdown(self) -> None:
        now = datetime.now(tz=timezone.utc)
        dg = build_digest([], [], "test", now - timedelta(days=7), now)
        md = digest_to_markdown(dg)
        assert "# Weekly Digest: test" in md
        assert "0 new papers" in md
