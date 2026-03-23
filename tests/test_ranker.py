"""Tests for the paper ranking module."""

from datetime import datetime, timedelta, timezone

from arxiv_curator.models import EnrichedPaper
from arxiv_curator.ranker import (
    _score_benchmark_mention,
    _score_code_mention,
    _score_multi_author,
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
    abstract: str = "Abstract text",
    authors: list[str] | None = None,
) -> EnrichedPaper:
    """Create an EnrichedPaper for testing."""
    published = datetime.now(timezone.utc) - timedelta(days=days_old)
    return EnrichedPaper(
        title=title,
        authors=authors if authors is not None else ["Author A"],
        abstract=abstract,
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
        ranked = rank_papers([paper], use_position=False)
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


class TestCodeMentionScoring:
    """Tests for code mention in abstract scoring."""

    def test_github_url_in_abstract(self) -> None:
        pts, reason = _score_code_mention("Code at https://github.com/foo/bar")
        assert pts == 15.0
        assert reason == "Code in abstract"

    def test_source_code_phrase(self) -> None:
        pts, _ = _score_code_mention("Our source code is released.")
        assert pts == 15.0

    def test_open_source_phrase(self) -> None:
        pts, _ = _score_code_mention("We provide an open-source implementation.")
        assert pts == 15.0

    def test_no_code_mention(self) -> None:
        pts, reason = _score_code_mention("We study perception for robotics.")
        assert pts == 0.0
        assert reason is None

    def test_code_mention_not_applied_when_code_url_exists(self) -> None:
        """If Semantic Scholar already found a code_url, the abstract
        code-mention bonus should NOT be added (avoid double counting)."""
        paper = _make_paper(
            abstract="Code at https://github.com/foo/bar",
            code_url="https://github.com/foo/bar",
            days_old=5,
        )
        ranked = rank_papers([paper], use_position=False)
        # Should have "Code available" but NOT "Code in abstract"
        assert any("Code available" in r for r in ranked[0].reasons)
        assert not any("Code in abstract" in r for r in ranked[0].reasons)


class TestBenchmarkScoring:
    """Tests for benchmark/evaluation mention scoring."""

    def test_benchmark_word(self) -> None:
        pts, reason = _score_benchmark_mention("We evaluate on a benchmark dataset.")
        assert pts == 5.0
        assert reason == "Benchmark results"

    def test_sota_mention(self) -> None:
        pts, _ = _score_benchmark_mention("Our method achieves SOTA results.")
        assert pts == 5.0

    def test_outperforms_mention(self) -> None:
        pts, _ = _score_benchmark_mention("Our approach outperforms prior work.")
        assert pts == 5.0

    def test_no_benchmark(self) -> None:
        pts, reason = _score_benchmark_mention("We propose a new model.")
        assert pts == 0.0
        assert reason is None


class TestMultiAuthorScoring:
    """Tests for multi-author collaboration scoring."""

    def test_more_than_5_authors(self) -> None:
        pts, reason = _score_multi_author(["A", "B", "C", "D", "E", "F"])
        assert pts == 5.0
        assert "6 authors" in reason

    def test_4_authors(self) -> None:
        pts, reason = _score_multi_author(["A", "B", "C", "D"])
        assert pts == 3.0
        assert "4 authors" in reason

    def test_3_authors_no_bonus(self) -> None:
        pts, reason = _score_multi_author(["A", "B", "C"])
        assert pts == 0.0
        assert reason is None

    def test_single_author_no_bonus(self) -> None:
        pts, _ = _score_multi_author(["A"])
        assert pts == 0.0


class TestCitationIndependentRanking:
    """Integration tests: papers with code mentions rank higher when
    all citations are zero (the core problem being fixed)."""

    def test_code_mention_differentiates_zero_citation_papers(self) -> None:
        """When all papers have 0 citations, code mention should break ties."""
        papers = [
            _make_paper(
                title="Paper A",
                abstract="We propose a method.",
                days_old=5,
            ),
            _make_paper(
                title="Paper B",
                abstract="Code at https://github.com/x/y. We propose a method.",
                days_old=5,
            ),
        ]
        ranked = rank_papers(papers, use_position=False)
        assert ranked[0].paper.title == "Paper B"
        assert ranked[0].score > ranked[1].score

    def test_benchmark_differentiates_zero_citation_papers(self) -> None:
        papers = [
            _make_paper(
                title="Paper A",
                abstract="We propose a method.",
                days_old=5,
            ),
            _make_paper(
                title="Paper B",
                abstract="Our method outperforms all baselines on the benchmark.",
                days_old=5,
            ),
        ]
        ranked = rank_papers(papers, use_position=False)
        assert ranked[0].paper.title == "Paper B"

    def test_multi_author_differentiates_zero_citation_papers(self) -> None:
        papers = [
            _make_paper(
                title="Paper A",
                abstract="We propose a method.",
                authors=["A", "B"],
                days_old=5,
            ),
            _make_paper(
                title="Paper B",
                abstract="We propose a method.",
                authors=["A", "B", "C", "D", "E", "F"],
                days_old=5,
            ),
        ]
        ranked = rank_papers(papers, use_position=False)
        assert ranked[0].paper.title == "Paper B"

    def test_all_signals_combined_for_new_papers(self) -> None:
        """A new paper with code mention + benchmark + many authors should
        score significantly higher than a plain new paper."""
        plain = _make_paper(
            title="Plain",
            abstract="A simple approach.",
            authors=["A"],
            days_old=3,
        )
        rich = _make_paper(
            title="Rich",
            abstract=(
                "Our open-source implementation outperforms baselines "
                "on the benchmark. Code at https://github.com/x/y"
            ),
            authors=["A", "B", "C", "D", "E", "F"],
            days_old=3,
        )
        ranked = rank_papers([plain, rich], use_position=False)
        assert ranked[0].paper.title == "Rich"
        # Expect at least 20 points difference (15+5+5 = 25 from new signals)
        assert ranked[0].score - ranked[1].score >= 20
