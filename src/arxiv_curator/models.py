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


@dataclass
class EnrichedPaper(Paper):
    """Paper enriched with Semantic Scholar metadata."""

    citation_count: int = 0
    venue: str = ""
    is_open_access: bool = False
    code_url: str = ""

    @classmethod
    def from_paper(
        cls,
        paper: Paper,
        citation_count: int = 0,
        venue: str = "",
        is_open_access: bool = False,
        code_url: str = "",
    ) -> "EnrichedPaper":
        """Create an EnrichedPaper from a base Paper."""
        return cls(
            title=paper.title,
            authors=paper.authors,
            abstract=paper.abstract,
            published=paper.published,
            arxiv_url=paper.arxiv_url,
            pdf_url=paper.pdf_url,
            categories=paper.categories,
            citation_count=citation_count,
            venue=venue,
            is_open_access=is_open_access,
            code_url=code_url,
        )

    def to_markdown(self) -> str:
        """Format as an awesome-list style markdown entry with enriched info."""
        base = super().to_markdown()
        extras = []
        if self.citation_count > 0:
            extras.append(f"Citations: {self.citation_count}")
        if self.venue:
            extras.append(self.venue)
        if self.code_url:
            extras.append(f"[Code]({self.code_url})")
        if extras:
            return f"{base} | {' | '.join(extras)}"
        return base
