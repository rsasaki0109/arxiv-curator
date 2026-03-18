"""Tests for arxiv_api module."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from arxiv_curator.arxiv_api import search_papers
from arxiv_curator.models import Paper


def _make_mock_result(
    title: str = "Test Paper",
    published: datetime | None = None,
) -> MagicMock:
    result = MagicMock()
    result.title = title
    result.authors = [MagicMock(__str__=lambda self: "Author A")]
    result.summary = "This is an abstract."
    result.published = published or datetime(2025, 1, 15, tzinfo=timezone.utc)
    result.entry_id = "https://arxiv.org/abs/2501.12345v1"
    result.pdf_url = "https://arxiv.org/pdf/2501.12345v1"
    result.categories = ["cs.CV"]
    return result


@patch("arxiv_curator.arxiv_api.arxiv.Client")
@patch("arxiv_curator.arxiv_api.arxiv.Search")
def test_search_papers_returns_papers(mock_search_cls, mock_client_cls):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.results.return_value = [_make_mock_result()]

    papers = search_papers("SLAM", max_results=5)

    assert len(papers) == 1
    assert isinstance(papers[0], Paper)
    assert papers[0].title == "Test Paper"
    assert papers[0].authors == ["Author A"]


@patch("arxiv_curator.arxiv_api.arxiv.Client")
@patch("arxiv_curator.arxiv_api.arxiv.Search")
def test_search_papers_filters_by_date(mock_search_cls, mock_client_cls):
    old = _make_mock_result(
        "Old Paper", datetime(2024, 1, 1, tzinfo=timezone.utc)
    )
    new = _make_mock_result(
        "New Paper", datetime(2025, 6, 1, tzinfo=timezone.utc)
    )
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.results.return_value = [new, old]

    papers = search_papers(
        "SLAM",
        max_results=10,
        since_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )

    assert len(papers) == 1
    assert papers[0].title == "New Paper"


@patch("arxiv_curator.arxiv_api.arxiv.Client")
@patch("arxiv_curator.arxiv_api.arxiv.Search")
def test_search_papers_empty(mock_search_cls, mock_client_cls):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.results.return_value = []

    papers = search_papers("nonexistent-topic-xyz", max_results=5)

    assert papers == []
