"""Tests for the paper ranking module."""

from datetime import datetime, timedelta, timezone

from arxiv_curator.models import EnrichedPaper
from arxiv_curator.ranker import rank_papers


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
