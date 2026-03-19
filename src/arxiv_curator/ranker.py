"""Paper ranking by multiple signals: citations, recency, code, venue."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone

from arxiv_curator.models import EnrichedPaper


# Category label thresholds
CATEGORY_MUST_READ = 70
CATEGORY_RECOMMENDED = 50
CATEGORY_WORTH_CHECKING = 30


def get_category_label(score: float) -> str:
    """Return a human-readable category label based on score."""
    if score >= CATEGORY_MUST_READ:
        return "Must read"
    elif score >= CATEGORY_RECOMMENDED:
        return "Recommended"
    elif score >= CATEGORY_WORTH_CHECKING:
        return "Worth checking"
    return "Low priority"


@dataclass
class RankedPaper:
    """A paper with its computed score and human-readable reasons."""

    paper: EnrichedPaper
    score: float
    reasons: list[str] = field(default_factory=list)
    percentile: float = 0.0
    category: str = ""


def _is_hidden_gem(paper: EnrichedPaper, days_old: int) -> bool:
    """Check if a paper qualifies as a hidden gem.

    A hidden gem is a recent paper (< 6 months) with code available
    but low citations (< 5), suggesting it is underappreciated.
    """
    return (
        days_old < 180
        and bool(paper.code_url)
        and paper.citation_count < 5
    )


def rank_papers(papers: list[EnrichedPaper]) -> list[RankedPaper]:
    """Score and rank papers by multiple signals.

    Signals (approximate max contribution):
      - Citation count (log-scaled)  ~50
      - Recency                      30
      - Citation velocity            25
      - Code availability            20
      - Top venue                    15
      - Hidden gem bonus             10
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

        # 7. Hidden gem detection
        if _is_hidden_gem(paper, days_old):
            score += 10
            reasons.append("Hidden gem (recent + code, low citations yet)")

        if not reasons:
            reasons.append("No notable signals")

        ranked.append(RankedPaper(paper=paper, score=score, reasons=reasons))

    ranked.sort(key=lambda r: r.score, reverse=True)

    # Compute percentile ranks
    n = len(ranked)
    for i, rp in enumerate(ranked):
        # i=0 is the highest score => percentile close to 100
        rp.percentile = (1 - i / max(n, 1)) * 100
        rp.category = get_category_label(rp.score)

    return ranked


def compute_summary(ranked: list[RankedPaper]) -> dict:
    """Compute summary statistics for ranked papers.

    Returns a dict with keys:
      - must_read: count of "Must read" papers
      - recommended: count of "Recommended" papers
      - worth_checking: count of "Worth checking" papers
      - low_priority: count of "Low priority" papers
      - with_code: count of papers with code
      - total: total number of papers
      - top_venue: count of papers at top venues
      - avg_citations: average citation count
    """
    if not ranked:
        return {
            "must_read": 0,
            "recommended": 0,
            "worth_checking": 0,
            "low_priority": 0,
            "with_code": 0,
            "total": 0,
            "top_venue": 0,
            "avg_citations": 0.0,
        }

    top_venues = {
        "CVPR", "ICCV", "ECCV", "NeurIPS", "ICML", "ICLR",
        "AAAI", "ICRA", "IROS", "RSS", "CoRL",
    }

    must_read = sum(1 for r in ranked if r.category == "Must read")
    recommended = sum(1 for r in ranked if r.category == "Recommended")
    worth_checking = sum(1 for r in ranked if r.category == "Worth checking")
    low_priority = sum(1 for r in ranked if r.category == "Low priority")
    with_code = sum(1 for r in ranked if r.paper.code_url)
    total = len(ranked)

    top_venue_count = 0
    for r in ranked:
        if r.paper.venue:
            for v in top_venues:
                if v.lower() in r.paper.venue.lower():
                    top_venue_count += 1
                    break

    total_citations = sum(r.paper.citation_count for r in ranked)
    avg_citations = total_citations / total

    return {
        "must_read": must_read,
        "recommended": recommended,
        "worth_checking": worth_checking,
        "low_priority": low_priority,
        "with_code": with_code,
        "total": total,
        "top_venue": top_venue_count,
        "avg_citations": round(avg_citations, 1),
    }
