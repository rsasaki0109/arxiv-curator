"""CLI integration tests using typer.testing.CliRunner."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from arxiv_curator.cli import app
from arxiv_curator.models import Paper

runner = CliRunner()


def _make_paper(title: str = "Test Paper", arxiv_id: str = "2501.12345") -> Paper:
    return Paper(
        title=title,
        authors=["Author A", "Author B"],
        abstract="An abstract.",
        published=datetime(2025, 6, 1, tzinfo=timezone.utc),
        arxiv_url=f"https://arxiv.org/abs/{arxiv_id}v1",
        pdf_url=f"https://arxiv.org/pdf/{arxiv_id}v1",
        categories=["cs.CV"],
    )


# -------------------------------------------------------------------
# search command
# -------------------------------------------------------------------


@patch("arxiv_curator.cli.search_papers")
def test_search_with_valid_args(mock_search):
    mock_search.return_value = [_make_paper()]
    result = runner.invoke(app, ["search", "SLAM"])
    assert result.exit_code == 0
    assert "1" in result.output  # "Found 1 papers"


@patch("arxiv_curator.cli.search_papers")
def test_search_json_format(mock_search):
    mock_search.return_value = [_make_paper()]
    result = runner.invoke(app, ["search", "SLAM", "--format", "json"])
    assert result.exit_code == 0
    assert "Test Paper" in result.output


@patch("arxiv_curator.cli.search_papers")
def test_search_markdown_format(mock_search):
    mock_search.return_value = [_make_paper()]
    result = runner.invoke(app, ["search", "SLAM", "--format", "markdown"])
    assert result.exit_code == 0
    assert "Test Paper" in result.output


def test_search_invalid_since_date():
    result = runner.invoke(app, ["search", "SLAM", "--since", "not-a-date"])
    assert result.exit_code == 1
    assert "Invalid date format" in result.output


# -------------------------------------------------------------------
# suggest command
# -------------------------------------------------------------------


@patch("arxiv_curator.cli.requests.get")
@patch("arxiv_curator.cli.search_papers")
def test_suggest_with_valid_url(mock_search, mock_get):
    mock_search.return_value = [_make_paper()]
    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.text = "## Papers\nNothing here yet."
    mock_get.return_value = mock_resp

    result = runner.invoke(
        app, ["suggest", "https://github.com/user/awesome-SLAM"]
    )
    assert result.exit_code == 0
    assert "new papers" in result.output.lower() or "1" in result.output


def test_suggest_bad_url():
    result = runner.invoke(app, ["suggest", "https://github.com/"])
    assert result.exit_code == 1
    assert "Could not extract keywords" in result.output


# -------------------------------------------------------------------
# export command
# -------------------------------------------------------------------


@patch("arxiv_curator.cli.search_papers")
def test_export_no_results(mock_search):
    mock_search.return_value = []
    result = runner.invoke(
        app, ["export", "nonexistent", "--output", "/tmp/test_out.json"]
    )
    assert result.exit_code == 0
    assert "No papers found" in result.output


# -------------------------------------------------------------------
# enrich command
# -------------------------------------------------------------------


def test_enrich_invalid_since_date():
    result = runner.invoke(app, ["enrich", "SLAM", "--since", "xyz"])
    assert result.exit_code == 1
    assert "Invalid date format" in result.output
