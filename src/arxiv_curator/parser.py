"""Parsers for awesome-list GitHub repositories."""

from __future__ import annotations

import re
from urllib.parse import urlparse


def parse_awesome_url(github_url: str) -> list[str]:
    """Extract search keywords from an awesome-list repository URL.

    Examples
    --------
    >>> parse_awesome_url("https://github.com/xxx/Awesome-Transformer-based-SLAM")
    ['transformer', 'SLAM']
    """
    # Handle no-scheme URLs (e.g. "github.com/org/repo")
    if "://" not in github_url:
        github_url = "https://" + github_url

    parsed = urlparse(github_url)
    path_parts = parsed.path.strip("/").split("/")
    if len(path_parts) < 2:
        return []

    repo_name = path_parts[1]

    # Strip .git suffix
    if repo_name.endswith(".git"):
        repo_name = repo_name[:-4]

    # Remove common prefixes/suffixes
    name = repo_name
    for prefix in ("awesome-", "Awesome-"):
        if name.startswith(prefix):
            name = name[len(prefix) :]
    for suffix in ("-list", "-papers", "-resources", "-collection"):
        if name.lower().endswith(suffix):
            name = name[: -len(suffix)]

    # Split on hyphens, underscores, and camelCase boundaries
    tokens = re.split(r"[-_]", name)
    # Further split camelCase — but only for tokens long enough to be
    # actual camelCase words.  Short alphanumeric tokens like "3D" or
    # "V2" are kept intact.
    expanded: list[str] = []
    for token in tokens:
        if len(token) <= 3:
            # Keep short tokens (e.g. "3D", "V2", "LLM") as-is
            expanded.append(token)
        else:
            parts = re.findall(r"[A-Z]+[a-z]*|[a-z]+|[A-Z]+", token)
            expanded.extend(parts if parts else [token])

    # Filter out noise words
    stop_words = {
        "a", "an", "the", "and", "or", "for", "in", "on", "of", "to",
        "with", "based", "using", "via",
    }
    keywords = [t for t in expanded if t.lower() not in stop_words and len(t) > 1]

    return keywords


def parse_awesome_readme(markdown_text: str) -> set[str]:
    """Extract existing arXiv paper IDs and titles from awesome-list markdown.

    Returns a set of identifiers (arxiv IDs like '2301.12345' and
    lower-cased paper titles) that can be used for deduplication.
    """
    identifiers: set[str] = set()

    # Match arXiv IDs  (e.g., 2301.12345, arxiv.org/abs/2301.12345v2)
    arxiv_id_pattern = re.compile(r"\d{4}\.\d{4,5}(?:v\d+)?")
    for match in arxiv_id_pattern.finditer(markdown_text):
        # Normalise: strip version suffix
        raw = match.group()
        identifiers.add(re.sub(r"v\d+$", "", raw))

    # Match markdown link titles that look like paper titles
    # Pattern: **[Title](url)** or [Title](url)
    link_pattern = re.compile(r"\[([^\]]{10,})\]\(https?://[^\)]+\)")
    for match in link_pattern.finditer(markdown_text):
        title = match.group(1).strip()
        identifiers.add(title.lower())

    return identifiers
