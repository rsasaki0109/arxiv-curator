"""Paper ranking by multiple signals: citations, recency, code, venue."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone

from arxiv_curator.models import EnrichedPaper


@dataclass
class RankedPaper:
    """A paper with its computed score and human-readable reasons."""

    paper: EnrichedPaper
    score: float
    reasons: list[str] = field(default_factory=list)


def rank_papers(papers: list[EnrichedPaper]) -> list[RankedPaper]:
    """Score and rank papers by multiple signals.

    Signals (approximate max contribution):
      - Citation count (log-scaled)  ~50
      - Recency                      30
      - Citation velocity            25
      - Code availability            20
      - Top venue                    15
      - Open access                   5
    """
    ranked: list[RankedPaper] = []

    for paper in papers:
        score = 0.0
        reasons: list[str] = []

        # 1. Citation score (log scale to avoid bias toward old papers)
        if paper.citation_count > 0:
            citation_score = math.log1p(paper.citation_count) * 10
            score += citation_score
            if paper.citation_count >= 100:
                reasons.append(f"Highly cited ({paper.citation_count})")
            elif paper.citation_count >= 10:
                reasons.append(f"Well cited ({paper.citation_count})")

        # 2. Recency score (newer = higher, decay over months)
        published_utc = paper.published.replace(tzinfo=timezone.utc)
        days_old = (datetime.now(timezone.utc) - published_utc).days
        if days_old <= 30:
            score += 30
            reasons.append("Published this month")
        elif days_old <= 90:
            score += 20
            reasons.append("Published in last 3 months")
        elif days_old <= 365:
            score += 10
            reasons.append("Published this year")

        # 3. Code availability bonus
        if paper.code_url:
            score += 20
            reasons.append("Code available")

        # 4. Open access bonus
        if paper.is_open_access:
            score += 5
            reasons.append("Open access")

        # 5. Venue bonus (published at top venue)
        top_venues = [
            "CVPR", "ICCV", "ECCV", "NeurIPS", "ICML", "ICLR",
            "AAAI", "ICRA", "IROS", "RSS", "CoRL",
        ]
        if paper.venue:
            for venue in top_venues:
                if venue.lower() in paper.venue.lower():
                    score += 15
                    reasons.append(f"Top venue ({paper.venue})")
                    break

        # 6. Citation velocity (citations per month since publication)
        if paper.citation_count > 0 and days_old > 0:
            velocity = paper.citation_count / max(days_old / 30, 1)
            if velocity >= 10:
                score += 25
                reasons.append(f"Fast growing ({velocity:.0f} citations/month)")
            elif velocity >= 3:
                score += 15
                reasons.append(f"Growing ({velocity:.0f} citations/month)")

        if not reasons:
            reasons.append("No notable signals")

        ranked.append(RankedPaper(paper=paper, score=score, reasons=reasons))

    ranked.sort(key=lambda r: r.score, reverse=True)
    return ranked
