import re
from dataclasses import dataclass
from typing import Optional, List, Tuple
import structlog

logger = structlog.get_logger(__name__)

# List of (regex_pattern, quality_score) for scoring URLs
SOURCE_QUALITY_PATTERNS: List[Tuple[str, float]] = [
    (r"\.gov(/|$)", 9.5),
    (r"\.edu(/|$)", 9.0),
    (r"nature\.com", 9.5),
    (r"arxiv\.org", 9.0),
    (r"ieee\.org", 9.0),
    (r"reuters\.com", 8.5),
    (r"apnews\.com", 8.5),
    (r"bloomberg\.com", 8.5),
    (r"nytimes\.com", 8.0),
    (r"bbc\.(co\.uk|com)", 8.0),
    (r"wikipedia\.org", 7.0),
    (r"medium\.com", 4.0),
    (r"substack\.com", 4.5),
    (r"github\.com", 6.5),
    (r"blog\.", 4.0),
]

def score_source(url: str) -> float:
    """Returns a source quality score from 0.0 to 10.0 based on URL pattern matching."""
    if not url:
        return 3.0
    for pattern, score in SOURCE_QUALITY_PATTERNS:
        if re.search(pattern, url, re.IGNORECASE):
            return score
    return 5.0  # Default score for generic sources

def recency_score(pub_date: Optional[str]) -> float:
    """Calculates recency score from 0.0 to 1.0 based on publication date."""
    if not pub_date:
        return 0.3  # Default fallback for unknown dates
    
    # Try parsing date, if it fails, return default
    # A simple fallback for text dates or ISO dates
    # In a full engine, we'd compare timestamp, but for robustness:
    try:
        import datetime
        # Try a few common formats
        parsed_date = None
        for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S", "%Y"):
            try:
                parsed_date = datetime.datetime.strptime(pub_date[:19], fmt)
                break
            except ValueError:
                continue
        if not parsed_date:
            return 0.3
        
        now = datetime.datetime.now()
        age_days = (now - parsed_date).days
        if age_days < 0:
            return 1.0
        if age_days <= 30:
            return 1.0
        if age_days <= 365:
            return 0.8
        if age_days <= 365 * 3:
            return 0.6
        if age_days <= 365 * 5:
            return 0.4
        return 0.2
    except Exception:
        return 0.3

@dataclass
class ConfidenceBreakdown:
    total: float
    source_quality: float
    cross_validation: float
    recency: float
    independence: float
    contradiction_penalty: float

def calculate_confidence(
    source_quality: float,
    cross_validation_count: int,
    recency: float,
    independence: float,
    has_contradiction: bool
) -> ConfidenceBreakdown:
    """Calculates claim confidence breakdown using a deterministic formula.

    Formula:
    total = (quality/10 * 0.40) + (min(cv_count/3, 1.0) * 0.25) + (recency * 0.20) + (independence * 0.15) - (0.20 if has_contradiction else 0.0)
    clamped to [0.0, 1.0]
    """
    w_quality = (source_quality / 10.0) * 0.40
    w_cv = min(cross_validation_count / 3.0, 1.0) * 0.25
    w_recency = recency * 0.20
    w_indep = independence * 0.15
    penalty = 0.20 if has_contradiction else 0.0
    
    total = w_quality + w_cv + w_recency + w_indep - penalty
    total = max(0.0, min(1.0, total))
    
    return ConfidenceBreakdown(
        total=round(total, 4),
        source_quality=round(w_quality, 4),
        cross_validation=round(w_cv, 4),
        recency=round(w_recency, 4),
        independence=round(w_indep, 4),
        contradiction_penalty=round(penalty, 4)
    )

def assign_verification_status(
    breakdown: ConfidenceBreakdown,
    mode_threshold: float,
    cross_validation_count: int,
    source_quality: float
) -> str:
    """Assigns verification status based on confidence, source quality, and cross-validation count."""
    if breakdown.contradiction_penalty > 0.0:
        return "Contradicted"
    
    # Verified requires: cv >= 2, source_quality >= 6.0, total >= mode_threshold
    if (cross_validation_count >= 2 and 
        source_quality >= 6.0 and 
        breakdown.total >= mode_threshold):
        return "Verified"
    
    if breakdown.total >= mode_threshold:
        return "Partially Verified"
    elif breakdown.total >= 0.35:
        return "Hypothesis"
    else:
        return "Unverified"
