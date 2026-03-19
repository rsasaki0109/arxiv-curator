"""Tests for the paper ranking module."""

from datetime import datetime, timedelta, timezone

from arxiv_curator.models import EnrichedPaper
from arxiv_curator.ranker import (
    compute_summary,
    get_category_label,
    rank_papers,
)


def _make_paper(
    title: str = "Test Paper",
    citation_count: int = 0,
    venue: str = "",
    is_open_access: bool = False,
    code_url: str = "",
    days_old: int = 180,
) -> EnrichedPaper:
    """Create an EnrichedPaper for testing."""
    published = datetime.now(timezone.utc) - timedelta(days=days_old)
    return EnrichedPaper(
        title=title,
        authors=["Author A"],
        abstract="Abstract text",
        published=published.replace(tzinfo=None),
        arxiv_url="http://arxiv.org/abs/0000.00000",
        pdf_url="http://arxiv.org/pdf/0000.00000",
        categories=["cs.CV"],
        citation_count=citation_count,
        venue=venue,
        is_open_access=is_open_access,
        code_url=code_url,
    )


class TestRankPapers:
    """Tests for rank_papers scoring logic."""

    def test_high_citations_get_high_score(self) -> None:
        papers = [
            _make_paper(title="Highly cited", citation_count=200),
            _make_paper(title="No citations", citation_count=0),
        ]
        ranked = rank_papers(papers)
        assert ranked[0].paper.title == "Highly cited"
        assert ranked[0].score > ranked[1].score
        assert any("Highly cited" in r for r in ranked[0].reasons)

    def test_recent_paper_gets_recency_bonus(self) -> None:
        papers = [
            _make_paper(title="Recent", days_old=10),
            _make_paper(title="Old", days_old=400),
        ]
        ranked = rank_papers(papers)
        assert ranked[0].paper.title == "Recent"
        assert any("Published this month" in r for r in ranked[0].reasons)

    def test_code_availability_bonus(self) -> None:
        papers = [
            _make_paper(title="With code", code_url="https://github.com/x/y"),
            _make_paper(title="No code"),
        ]
        ranked = rank_papers(papers)
        assert ranked[0].paper.title == "With code"
        assert any("Code available" in r for r in ranked[0].reasons)

    def test_top_venue_bonus(self) -> None:
        papers = [
            _make_paper(title="CVPR paper", venue="CVPR 2025"),
            _make_paper(title="No venue"),
        ]
        ranked = rank_papers(papers)
        assert ranked[0].paper.title == "CVPR paper"
        assert any("Top venue" in r for r in ranked[0].reasons)

    def test_citation_velocity(self) -> None:
        # 300 citations in 30 days => 300 citations/month => fast growing
        paper = _make_paper(
            title="Fast growing", citation_count=300, days_old=30,
        )
        ranked = rank_papers([paper])
        assert any("Fast growing" in r for r in ranked[0].reasons)

    def test_ranking_order_highest_first(self) -> None:
        papers = [
            _make_paper(title="Low", citation_count=0, days_old=400),
            _make_paper(title="High", citation_count=500, days_old=10, code_url="http://x"),
            _make_paper(title="Medium", citation_count=20, days_old=60),
        ]
        ranked = rank_papers(papers)
        scores = [r.score for r in ranked]
        assert scores == sorted(scores, reverse=True)
        assert ranked[0].paper.title == "High"

    def test_paper_with_no_signals(self) -> None:
        paper = _make_paper(days_old=400)
        ranked = rank_papers([paper])
        assert ranked[0].reasons == ["No notable signals"]
        assert ranked[0].score == 0.0

    def test_open_access_bonus(self) -> None:
        papers = [
            _make_paper(title="OA", is_open_access=True),
            _make_paper(title="Not OA", is_open_access=False),
        ]
        ranked = rank_papers(papers)
        oa = next(r for r in ranked if r.paper.title == "OA")
        not_oa = next(r for r in ranked if r.paper.title == "Not OA")
        assert oa.score > not_oa.score
        assert any("Open access" in r for r in oa.reasons)

    def test_empty_list(self) -> None:
        assert rank_papers([]) == []


class TestHiddenGem:
    """Tests for hidden gem detection."""

    def test_hidden_gem_recent_with_code_low_citations(self) -> None:
        paper = _make_paper(
            title="Hidden gem",
            days_old=60,
            code_url="https://github.com/x/y",
            citation_count=2,
        )
        ranked = rank_papers([paper])
        assert any("Hidden gem" in r for r in ranked[0].reasons)

    def test_no_hidden_gem_without_code(self) -> None:
        paper = _make_paper(
            title="No code",
            days_old=60,
            code_url="",
            citation_count=2,
        )
        ranked = rank_papers([paper])
        assert not any("Hidden gem" in r for r in ranked[0].reasons)

    def test_no_hidden_gem_high_citations(self) -> None:
        paper = _make_paper(
            title="Well known",
            days_old=60,
            code_url="https://github.com/x/y",
            citation_count=50,
        )
        ranked = rank_papers([paper])
        assert not any("Hidden gem" in r for r in ranked[0].reasons)

    def test_no_hidden_gem_old_paper(self) -> None:
        paper = _make_paper(
            title="Old paper",
            days_old=200,
            code_url="https://github.com/x/y",
            citation_count=2,
        )
        ranked = rank_papers([paper])
        assert not any("Hidden gem" in r for r in ranked[0].reasons)

    def test_hidden_gem_bonus_score(self) -> None:
        gem = _make_paper(
            title="Gem",
            days_old=60,
            code_url="https://github.com/x/y",
            citation_count=0,
        )
        not_gem = _make_paper(
            title="Not gem",
            days_old=60,
            code_url="https://github.com/x/y",
            citation_count=0,
        )
        # Both same except we manually check gem gets the bonus
        ranked_gem = rank_papers([gem])
        assert any("Hidden gem" in r for r in ranked_gem[0].reasons)
        # The hidden gem bonus adds 10 points
        assert ranked_gem[0].score >= 10


class TestPercentile:
    """Tests for percentile calculation."""

    def test_single_paper_percentile(self) -> None:
        paper = _make_paper(title="Only paper", citation_count=100)
        ranked = rank_papers([paper])
        assert ranked[0].percentile == 100.0

    def test_multiple_papers_percentile_order(self) -> None:
        papers = [
            _make_paper(title="Low", citation_count=0, days_old=400),
            _make_paper(title="High", citation_count=500, days_old=10, code_url="http://x"),
            _make_paper(title="Medium", citation_count=20, days_old=60),
        ]
        ranked = rank_papers(papers)
        # First paper (highest score) should have highest percentile
        assert ranked[0].percentile > ranked[1].percentile
        assert ranked[1].percentile > ranked[2].percentile

    def test_percentile_range(self) -> None:
        papers = [_make_paper(title=f"Paper {i}", citation_count=i * 10) for i in range(10)]
        ranked = rank_papers(papers)
        for rp in ranked:
            assert 0 <= rp.percentile <= 100

    def test_empty_list_no_percentile_error(self) -> None:
        ranked = rank_papers([])
        assert ranked == []


class TestCategoryLabel:
    """Tests for category label assignment."""

    def test_must_read(self) -> None:
        assert get_category_label(70) == "Must read"
        assert get_category_label(100) == "Must read"

    def test_recommended(self) -> None:
        assert get_category_label(50) == "Recommended"
        assert get_category_label(69) == "Recommended"

    def test_worth_checking(self) -> None:
        assert get_category_label(30) == "Worth checking"
        assert get_category_label(49) == "Worth checking"

    def test_low_priority(self) -> None:
        assert get_category_label(0) == "Low priority"
        assert get_category_label(29) == "Low priority"

    def test_category_assigned_to_ranked_papers(self) -> None:
        papers = [
            _make_paper(title="High", citation_count=500, days_old=10, code_url="http://x"),
            _make_paper(title="Low", citation_count=0, days_old=400),
        ]
        ranked = rank_papers(papers)
        # High scorer should be "Must read" or "Recommended"
        assert ranked[0].category in ("Must read", "Recommended")
        # Low scorer should be "Low priority"
        assert ranked[1].category == "Low priority"


class TestComputeSummary:
    """Tests for summary statistics."""

    def test_empty_summary(self) -> None:
        summary = compute_summary([])
        assert summary["total"] == 0
        assert summary["must_read"] == 0
        assert summary["avg_citations"] == 0.0

    def test_summary_counts(self) -> None:
        papers = [
            _make_paper(title="High", citation_count=500, days_old=10, code_url="http://x"),
            _make_paper(title="Medium", citation_count=20, days_old=60, code_url="http://y"),
            _make_paper(title="Low", citation_count=0, days_old=400),
        ]
        ranked = rank_papers(papers)
        summary = compute_summary(ranked)

        assert summary["total"] == 3
        assert summary["with_code"] == 2
        assert summary["avg_citations"] == round((500 + 20 + 0) / 3, 1)

    def test_summary_with_code_percentage(self) -> None:
        papers = [
            _make_paper(title="A", code_url="http://x"),
            _make_paper(title="B", code_url=""),
            _make_paper(title="C", code_url="http://y"),
            _make_paper(title="D", code_url=""),
        ]
        ranked = rank_papers(papers)
        summary = compute_summary(ranked)
        assert summary["with_code"] == 2
        assert summary["total"] == 4

    def test_summary_top_venue(self) -> None:
        papers = [
            _make_paper(title="A", venue="CVPR 2025"),
            _make_paper(title="B", venue="ICRA 2025"),
            _make_paper(title="C", venue="Some Workshop"),
            _make_paper(title="D", venue=""),
        ]
        ranked = rank_papers(papers)
        summary = compute_summary(ranked)
        assert summary["top_venue"] == 2

    def test_summary_category_counts(self) -> None:
        papers = [
            _make_paper(title="Must read", citation_count=500, days_old=10, code_url="http://x", venue="CVPR"),
            _make_paper(title="Low", citation_count=0, days_old=400),
        ]
        ranked = rank_papers(papers)
        summary = compute_summary(ranked)
        # At least one must_read and one low_priority
        assert summary["must_read"] + summary["recommended"] >= 1
        assert summary["low_priority"] >= 1
