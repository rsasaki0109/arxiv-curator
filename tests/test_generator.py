"""Tests for the generator module."""

from datetime import datetime, timedelta, timezone

from arxiv_curator.generator import (
    GeneratedList,
    _categorize_papers,
    _extract_github_urls,
    build_generated_list,
    generated_list_to_markdown,
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
    abstract: str = "Abstract text about the paper",
    arxiv_url: str = "http://arxiv.org/abs/0000.00000",
) -> EnrichedPaper:
    """Create an EnrichedPaper for testing."""
    published = datetime.now(timezone.utc) - timedelta(days=days_old)
    return EnrichedPaper(
        title=title,
        authors=["Author A", "Author B"],
        abstract=abstract,
        published=published.replace(tzinfo=None),
        arxiv_url=arxiv_url,
        pdf_url="http://arxiv.org/pdf/0000.00000",
        categories=categories or ["cs.CV"],
        citation_count=citation_count,
        venue=venue,
        is_open_access=is_open_access,
        code_url=code_url,
    )


class TestExtractGithubUrls:
    """Tests for _extract_github_urls."""

    def test_extracts_single_url(self) -> None:
        text = "Code is available at https://github.com/user/repo for reproduction."
        urls = _extract_github_urls(text)
        assert urls == ["https://github.com/user/repo"]

    def test_extracts_multiple_urls(self) -> None:
        text = (
            "See https://github.com/user/repo1 and "
            "https://github.com/org/repo2 for details."
        )
        urls = _extract_github_urls(text)
        assert len(urls) == 2
        assert "https://github.com/user/repo1" in urls
        assert "https://github.com/org/repo2" in urls

    def test_no_urls(self) -> None:
        text = "No code links here."
        assert _extract_github_urls(text) == []

    def test_handles_http(self) -> None:
        text = "Available at http://github.com/user/repo"
        urls = _extract_github_urls(text)
        assert urls == ["http://github.com/user/repo"]

    def test_handles_dots_and_hyphens(self) -> None:
        text = "See https://github.com/user-name/repo.name for code."
        urls = _extract_github_urls(text)
        assert urls == ["https://github.com/user-name/repo.name"]


class TestCategorizePapers:
    """Tests for _categorize_papers."""

    def test_groups_by_shared_keywords(self) -> None:
        papers = [
            _make_paper(title="Reconstruction via NeRF Methods", arxiv_url="http://arxiv.org/abs/0001"),
            _make_paper(title="Neural Reconstruction Approach", arxiv_url="http://arxiv.org/abs/0002"),
            _make_paper(title="SLAM Integration Pipeline", arxiv_url="http://arxiv.org/abs/0003"),
            _make_paper(title="Visual SLAM Framework", arxiv_url="http://arxiv.org/abs/0004"),
        ]
        categories = _categorize_papers(papers, ["gaussian"])
        # "reconstruction" and "slam" should form groups
        all_cat_papers = [p for ps in categories.values() for p in ps]
        assert len(all_cat_papers) == 4  # all papers assigned

    def test_query_keywords_excluded(self) -> None:
        papers = [
            _make_paper(title="Gaussian Splatting Editing", arxiv_url="http://arxiv.org/abs/0001"),
            _make_paper(title="Gaussian Splatting Rendering", arxiv_url="http://arxiv.org/abs/0002"),
            _make_paper(title="Gaussian Splatting Compression", arxiv_url="http://arxiv.org/abs/0003"),
        ]
        categories = _categorize_papers(papers, ["gaussian", "splatting"])
        # "gaussian" and "splatting" should NOT be category names
        for cat_name in categories:
            assert cat_name.lower() not in ["gaussian", "splatting"]

    def test_empty_papers(self) -> None:
        assert _categorize_papers([], ["test"]) == {}

    def test_single_paper_goes_to_other(self) -> None:
        papers = [_make_paper(title="Unique Paper About Nothing")]
        categories = _categorize_papers(papers, ["test"])
        assert "Other" in categories
        assert len(categories["Other"]) == 1


class TestBuildGeneratedList:
    """Tests for build_generated_list."""

    def test_builds_complete_list(self) -> None:
        papers = [
            _make_paper(
                title="Top Gaussian Paper",
                citation_count=500,
                venue="CVPR 2025",
                code_url="https://github.com/x/y",
                arxiv_url="http://arxiv.org/abs/0001",
            ),
            _make_paper(
                title="Second Gaussian Paper",
                citation_count=100,
                venue="ICCV 2025",
                arxiv_url="http://arxiv.org/abs/0002",
            ),
            _make_paper(
                title="Regular Paper",
                citation_count=10,
                arxiv_url="http://arxiv.org/abs/0003",
            ),
        ]
        ranked = rank_papers(papers)
        gl = build_generated_list(
            papers, ranked, "3D AND gaussian", ["3D", "gaussian"], "2023-01-01"
        )

        assert gl.query == "3D AND gaussian"
        assert gl.total_papers == 3
        assert gl.papers_with_code >= 1
        assert isinstance(gl.top_venues, dict)
        assert len(gl.must_reads) > 0
        assert isinstance(gl.categories, dict)
        assert len(gl.all_papers) == 3

    def test_period_extraction(self) -> None:
        papers = [
            _make_paper(title="Paper A", days_old=365, arxiv_url="http://arxiv.org/abs/0001"),
            _make_paper(title="Paper B", days_old=10, arxiv_url="http://arxiv.org/abs/0002"),
        ]
        ranked = rank_papers(papers)
        gl = build_generated_list(papers, ranked, "test", ["test"], "2023-01-01")

        assert "to" in gl.period

    def test_empty_papers(self) -> None:
        gl = build_generated_list([], [], "test", ["test"], "2023-01-01")
        assert gl.total_papers == 0
        assert gl.papers_with_code == 0
        assert gl.must_reads == []
        assert gl.categories == {}
        assert gl.period == "2023-01-01"

    def test_venue_counting(self) -> None:
        papers = [
            _make_paper(title="Paper A", venue="CVPR", arxiv_url="http://arxiv.org/abs/0001"),
            _make_paper(title="Paper B", venue="CVPR", arxiv_url="http://arxiv.org/abs/0002"),
            _make_paper(title="Paper C", venue="ICCV", arxiv_url="http://arxiv.org/abs/0003"),
        ]
        ranked = rank_papers(papers)
        gl = build_generated_list(papers, ranked, "test", ["test"], "2023-01-01")
        assert gl.top_venues.get("CVPR") == 2
        assert gl.top_venues.get("ICCV") == 1

    def test_code_counting_from_abstract(self) -> None:
        papers = [
            _make_paper(
                title="Paper with Code in Abstract",
                abstract="Code at https://github.com/user/repo",
                arxiv_url="http://arxiv.org/abs/0001",
            ),
        ]
        ranked = rank_papers(papers)
        gl = build_generated_list(papers, ranked, "test", ["test"], "2023-01-01")
        assert gl.papers_with_code == 1


class TestGeneratedListToMarkdown:
    """Tests for generated_list_to_markdown."""

    def _build_gl(self, papers: list[EnrichedPaper] | None = None) -> GeneratedList:
        if papers is None:
            papers = [
                _make_paper(
                    title="Important Paper",
                    citation_count=500,
                    venue="CVPR 2025",
                    code_url="https://github.com/x/y",
                    arxiv_url="http://arxiv.org/abs/0001",
                ),
                _make_paper(
                    title="Another Paper",
                    citation_count=50,
                    arxiv_url="http://arxiv.org/abs/0002",
                ),
            ]
        ranked = rank_papers(papers)
        return build_generated_list(
            papers, ranked, "test AND topic", ["test", "topic"], "2023-01-01"
        )

    def test_contains_title(self) -> None:
        gl = self._build_gl()
        md = generated_list_to_markdown(gl)
        assert "# test topic" in md

    def test_contains_summary(self) -> None:
        gl = self._build_gl()
        md = generated_list_to_markdown(gl)
        assert "## Summary" in md
        assert "2 papers" in md
        assert "with code implementations" in md

    def test_contains_must_read_table(self) -> None:
        gl = self._build_gl()
        md = generated_list_to_markdown(gl)
        assert "## Must Read" in md
        assert "| Paper | Year | Citations | Venue | Code |" in md
        assert "Important Paper" in md

    def test_contains_generated_by(self) -> None:
        gl = self._build_gl()
        md = generated_list_to_markdown(gl)
        assert "arxiv-curator" in md

    def test_code_link_in_must_read(self) -> None:
        gl = self._build_gl()
        md = generated_list_to_markdown(gl)
        assert "[Code](https://github.com/x/y)" in md

    def test_venue_in_must_read(self) -> None:
        gl = self._build_gl()
        md = generated_list_to_markdown(gl)
        assert "CVPR 2025" in md

    def test_empty_list(self) -> None:
        gl = self._build_gl(papers=[])
        md = generated_list_to_markdown(gl)
        assert "# test topic" in md
        assert "0 papers" in md

    def test_github_url_from_abstract(self) -> None:
        papers = [
            _make_paper(
                title="Paper With Abstract Code",
                abstract="Code: https://github.com/user/repo",
                citation_count=200,
                arxiv_url="http://arxiv.org/abs/0001",
            ),
        ]
        gl = self._build_gl(papers=papers)
        md = generated_list_to_markdown(gl)
        assert "[Code](https://github.com/user/repo)" in md
