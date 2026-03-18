"""Data models for arxiv-curator.

Defines the Paper dataclass used across the project.
The JSON schema is designed to be compatible with github-curator.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime


@dataclass
class Paper:
    """Represents an arXiv paper."""

    title: str
    authors: list[str]
    abstract: str
    published: datetime
    arxiv_url: str
    pdf_url: str
    categories: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary with ISO-format datetime."""
        data = asdict(self)
        data["published"] = self.published.isoformat()
        return data

    def to_markdown(self) -> str:
        """Format as an awesome-list style markdown entry."""
        authors_str = ", ".join(self.authors[:3])
        if len(self.authors) > 3:
            authors_str += " et al."
        date_str = self.published.strftime("%Y-%m-%d")
        return (
            f"- **[{self.title}]({self.arxiv_url})** - "
            f"{authors_str} ({date_str})"
        )

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


# JSON Schema for interoperability with github-curator
PAPER_JSON_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Paper",
    "description": "arXiv paper metadata (shared with github-curator)",
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "authors": {"type": "array", "items": {"type": "string"}},
        "abstract": {"type": "string"},
        "published": {"type": "string", "format": "date-time"},
        "arxiv_url": {"type": "string", "format": "uri"},
        "pdf_url": {"type": "string", "format": "uri"},
        "categories": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["title", "authors", "abstract", "published", "arxiv_url", "pdf_url"],
}
