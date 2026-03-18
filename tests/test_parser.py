"""Tests for parser module."""

from arxiv_curator.parser import parse_awesome_readme, parse_awesome_url


class TestParseAwesomeUrl:
    def test_basic_awesome_url(self):
        url = "https://github.com/xxx/Awesome-Transformer-based-SLAM"
        keywords = parse_awesome_url(url)
        # Should contain transformer and SLAM, not "based" or "Awesome"
        lower = [k.lower() for k in keywords]
        assert "transformer" in lower
        assert "slam" in lower
        assert "awesome" not in lower
        assert "based" not in lower

    def test_hyphenated_name(self):
        url = "https://github.com/user/awesome-visual-slam-papers"
        keywords = parse_awesome_url(url)
        lower = [k.lower() for k in keywords]
        assert "visual" in lower
        assert "slam" in lower

    def test_camel_case_split(self):
        url = "https://github.com/user/Awesome-PointCloud"
        keywords = parse_awesome_url(url)
        lower = [k.lower() for k in keywords]
        assert "point" in lower
        assert "cloud" in lower

    def test_invalid_url_returns_empty(self):
        assert parse_awesome_url("https://github.com/") == []
        assert parse_awesome_url("not-a-url") == []


class TestParseAwesomeReadme:
    def test_extracts_arxiv_ids(self):
        md = """
## Papers
- [Paper A](https://arxiv.org/abs/2301.12345) - desc
- [Paper B](https://arxiv.org/abs/2305.67890v2) - desc
"""
        ids = parse_awesome_readme(md)
        assert "2301.12345" in ids
        assert "2305.67890" in ids  # version stripped

    def test_extracts_paper_titles(self):
        md = '- **[A Long Paper Title About SLAM](https://example.com)** - desc'
        ids = parse_awesome_readme(md)
        assert "a long paper title about slam" in ids

    def test_empty_markdown(self):
        assert parse_awesome_readme("") == set()
