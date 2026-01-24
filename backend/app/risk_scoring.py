"""
Risk Scoring and Deal Scorecard Module

Automatically detects risk factors and generates deal scorecards.
"""
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from . import models, schemas
from . import financial_ingestion


# ============================================================================
# RISK DETECTION RULES
# ============================================================================

RISK_RULES = {
    "financial": [
        {
            "id": "low_ebitdar_margin",
            "title": "Low EBITDAR Margin",
            "check": lambda m: m.get("ebitdar_margin", 0) < 15,
            "severity": "high",
            "description": "EBITDAR margin below 15% indicates potential operational issues",
            "recommendation": "Review expense structure and revenue optimization opportunities"
        },
        {
            "id": "high_labor_ratio",
            "title": "High Labor Ratio",
            "check": lambda m: m.get("labor_ratio", 0) > 65,
            "severity": "medium",
            "description": "Labor costs exceed 65% of revenue",
            "recommendation": "Analyze staffing levels and agency usage"
        },
        {
            "id": "negative_ebitda",
            "title": "Negative EBITDA",
            "check": lambda m: m.get("ebitda", 0) < 0,
            "severity": "high",
            "description": "Facility is operating at a loss before interest and taxes",
            "recommendation": "Requires significant turnaround plan"
        },
        {
            "id": "thin_margins",
            "title": "Thin Operating Margins",
            "check": lambda m: 0 < m.get("ebitdar_margin", 0) < 10,
            "severity": "medium",
            "description": "Operating margins between 0-10% leave little room for error",
            "recommendation": "Identify cost reduction and revenue enhancement opportunities"
        },
    ],
    "operational": [
        {
            "id": "low_occupancy",
            "title": "Low Occupancy",
            "check": lambda d: d.get("occupancy", 100) < 80,
            "severity": "medium",
            "description": "Occupancy below 80% impacts revenue and efficiency",
            "recommendation": "Review marketing strategy and referral relationships"
        },
        {
            "id": "critical_occupancy",
            "title": "Critically Low Occupancy",
            "check": lambda d: d.get("occupancy", 100) < 70,
            "severity": "high",
            "description": "Occupancy below 70% poses significant financial risk",
            "recommendation": "Investigate root causes - quality issues, competition, location"
        },
    ],
    "quality": [
        {
            "id": "low_star_rating",
            "title": "Low CMS Star Rating",
            "check": lambda d: d.get("star_rating", 5) <= 2,
            "severity": "high",
            "description": "CMS overall rating of 2 stars or below indicates quality concerns",
            "recommendation": "Review survey history and quality improvement plans"
        },
        {
            "id": "below_average_rating",
            "title": "Below Average Star Rating",
            "check": lambda d: d.get("star_rating", 5) == 3,
            "severity": "medium",
            "description": "CMS rating of 3 stars is below average",
            "recommendation": "Identify specific improvement areas from CMS data"
        },
    ],
    "compliance": [
        {
            "id": "high_variance_claims",
            "title": "Material OM Variances",
            "check": lambda d: d.get("red_flag_claims", 0) > 0,
            "severity": "high",
            "description": "OM contains claims with significant variances from supporting data",
            "recommendation": "Validate all material claims in due diligence"
        },
        {
            "id": "unverified_claims",
            "title": "Unverified OM Claims",
            "check": lambda d: d.get("unverified_claim_ratio", 0) > 0.5,
            "severity": "medium",
            "description": "More than 50% of OM claims remain unverified",
            "recommendation": "Request additional supporting documentation"
        },
    ],
}


def detect_risks(
    db: Session,
    deal_id: int
) -> List[Dict[str, Any]]:
    """
    Detect risks for a deal based on available data.
    Returns list of detected risks.
    """
    detected = []

    # Get deal
    deal = db.query(models.Deal).filter(models.Deal.id == deal_id).first()
    if not deal:
        return []

    # Get financial metrics
    try:
        fin_metrics = financial_ingestion.calculate_summary_metrics(db, deal_id)
    except:
        fin_metrics = {}

    # Get claims data
    claims = db.query(models.Claim).filter(models.Claim.deal_id == deal_id).all()
    red_flag_claims = len([c for c in claims if c.is_red_flag])
    unverified_claims = len([c for c in claims if c.verification_status == "pending"])
    total_claims = len(claims)

    # Get property data for operational metrics
    properties = db.query(models.Property).filter(models.Property.deal_id == deal_id).all()
    avg_occupancy = None
    avg_star_rating = None
    if properties:
        occupancies = [p.current_occupancy for p in properties if p.current_occupancy]
        ratings = [p.star_rating for p in properties if p.star_rating]
        if occupancies:
            avg_occupancy = sum(occupancies) / len(occupancies)
        if ratings:
            avg_star_rating = sum(ratings) / len(ratings)

    # Build context for risk checks
    deal_context = {
        "occupancy": avg_occupancy or (deal.ebitdar / deal.total_beds * 100 if deal.ebitdar and deal.total_beds else 100),
        "star_rating": avg_star_rating,
        "red_flag_claims": red_flag_claims,
        "unverified_claim_ratio": unverified_claims / total_claims if total_claims > 0 else 0,
    }

    # Check financial risks
    for rule in RISK_RULES["financial"]:
        if fin_metrics and rule["check"](fin_metrics):
            detected.append({
                "rule_id": rule["id"],
                "risk_category": "financial",
                "risk_type": rule["id"],
                "severity": rule["severity"],
                "title": rule["title"],
                "description": rule["description"],
                "recommendation": rule["recommendation"],
            })

    # Check operational risks
    for rule in RISK_RULES["operational"]:
        if deal_context.get("occupancy") and rule["check"](deal_context):
            detected.append({
                "rule_id": rule["id"],
                "risk_category": "operational",
                "risk_type": rule["id"],
                "severity": rule["severity"],
                "title": rule["title"],
                "description": rule["description"],
                "recommendation": rule["recommendation"],
            })

    # Check quality risks
    for rule in RISK_RULES["quality"]:
        if deal_context.get("star_rating") and rule["check"](deal_context):
            detected.append({
                "rule_id": rule["id"],
                "risk_category": "quality",
                "risk_type": rule["id"],
                "severity": rule["severity"],
                "title": rule["title"],
                "description": rule["description"],
                "recommendation": rule["recommendation"],
            })

    # Check compliance risks
    for rule in RISK_RULES["compliance"]:
        if rule["check"](deal_context):
            detected.append({
                "rule_id": rule["id"],
                "risk_category": "compliance",
                "risk_type": rule["id"],
                "severity": rule["severity"],
                "title": rule["title"],
                "description": rule["description"],
                "recommendation": rule["recommendation"],
            })

    return detected


def create_risk_flags_for_deal(
    db: Session,
    deal_id: int
) -> int:
    """
    Detect and store risk flags for a deal.
    Returns count of new flags created.
    """
    # Get existing flags
    existing = db.query(models.RiskFlag).filter(
        models.RiskFlag.deal_id == deal_id,
        models.RiskFlag.status == "open"
    ).all()
    existing_types = {f.risk_type for f in existing}

    # Detect risks
    detected = detect_risks(db, deal_id)

    # Create new flags
    count = 0
    for risk in detected:
        if risk["risk_type"] not in existing_types:
            flag = models.RiskFlag(
                deal_id=deal_id,
                risk_category=risk["risk_category"],
                risk_type=risk["risk_type"],
                severity=risk["severity"],
                title=risk["title"],
                description=risk["description"],
                recommendation=risk["recommendation"],
                status="open"
            )
            db.add(flag)
            count += 1

    db.commit()
    return count


# ============================================================================
# SCORECARD CALCULATION
# ============================================================================

def calculate_financial_score(
    db: Session,
    deal_id: int
) -> float:
    """
    Calculate financial health score (0-100).
    """
    try:
        metrics = financial_ingestion.calculate_summary_metrics(db, deal_id)
    except:
        return 50.0  # Default if no data

    score = 50.0  # Base score

    # EBITDAR Margin scoring
    margin = metrics.get("ebitdar_margin", 0)
    if margin >= 25:
        score += 20
    elif margin >= 20:
        score += 15
    elif margin >= 15:
        score += 10
    elif margin >= 10:
        score += 5
    elif margin < 5:
        score -= 15

    # Labor ratio scoring
    labor = metrics.get("labor_ratio", 50)
    if labor <= 50:
        score += 15
    elif labor <= 55:
        score += 10
    elif labor <= 60:
        score += 5
    elif labor > 70:
        score -= 10

    # Positive EBITDA
    if metrics.get("ebitda", 0) > 0:
        score += 15
    else:
        score -= 20

    return max(0, min(100, score))


def calculate_operational_score(
    db: Session,
    deal_id: int
) -> float:
    """
    Calculate operational health score (0-100).
    """
    deal = db.query(models.Deal).filter(models.Deal.id == deal_id).first()
    properties = db.query(models.Property).filter(models.Property.deal_id == deal_id).all()

    score = 50.0

    # Occupancy scoring
    occupancies = [p.current_occupancy for p in properties if p.current_occupancy]
    if occupancies:
        avg_occ = sum(occupancies) / len(occupancies)
        if avg_occ >= 95:
            score += 25
        elif avg_occ >= 90:
            score += 20
        elif avg_occ >= 85:
            score += 15
        elif avg_occ >= 80:
            score += 10
        elif avg_occ >= 75:
            score += 5
        elif avg_occ < 70:
            score -= 15

    # Bed count (scale advantages)
    if deal and deal.total_beds:
        if deal.total_beds >= 150:
            score += 10
        elif deal.total_beds >= 100:
            score += 5
        elif deal.total_beds < 60:
            score -= 5

    return max(0, min(100, score))


def calculate_quality_score(
    db: Session,
    deal_id: int
) -> float:
    """
    Calculate quality score (0-100).
    """
    properties = db.query(models.Property).filter(models.Property.deal_id == deal_id).all()

    score = 50.0

    # Star rating scoring
    ratings = [p.star_rating for p in properties if p.star_rating]
    if ratings:
        avg_rating = sum(ratings) / len(ratings)
        if avg_rating >= 4.5:
            score += 30
        elif avg_rating >= 4:
            score += 20
        elif avg_rating >= 3.5:
            score += 10
        elif avg_rating >= 3:
            score += 0
        elif avg_rating >= 2:
            score -= 15
        else:
            score -= 25

    # Check for survey-related extracted fields
    survey_issues = db.query(models.ExtractedField).filter(
        models.ExtractedField.deal_id == deal_id,
        models.ExtractedField.field_key.in_(["deficiencies", "immediate_jeopardy"])
    ).all()

    for field in survey_issues:
        if field.field_key == "immediate_jeopardy" and field.field_value:
            score -= 20
        elif field.field_key == "deficiencies":
            try:
                count = int(field.numeric_value or 0)
                if count > 10:
                    score -= 10
                elif count > 5:
                    score -= 5
            except:
                pass

    return max(0, min(100, score))


def calculate_compliance_score(
    db: Session,
    deal_id: int
) -> float:
    """
    Calculate compliance/diligence score (0-100).
    """
    score = 50.0

    # Check claim verification status
    claims = db.query(models.Claim).filter(models.Claim.deal_id == deal_id).all()

    if claims:
        verified = len([c for c in claims if c.verification_status == "verified"])
        disputed = len([c for c in claims if c.verification_status == "disputed"])
        flagged = len([c for c in claims if c.verification_status == "flagged"])

        verification_rate = verified / len(claims)
        score += verification_rate * 30

        # Penalize for red flags
        score -= flagged * 5
        score -= disputed * 2

    # Check for risk flags
    flags = db.query(models.RiskFlag).filter(
        models.RiskFlag.deal_id == deal_id,
        models.RiskFlag.status == "open"
    ).all()

    for flag in flags:
        if flag.severity == "high":
            score -= 10
        elif flag.severity == "medium":
            score -= 5

    return max(0, min(100, score))


def generate_recommendation(
    overall_score: float,
    high_risk_count: int,
    key_risks: List[Dict]
) -> str:
    """
    Generate deal recommendation based on scores and risks.
    """
    if high_risk_count > 2:
        return "pass"
    elif overall_score >= 75 and high_risk_count == 0:
        return "strong_proceed"
    elif overall_score >= 60:
        return "proceed_with_caution"
    elif overall_score >= 45:
        return "needs_further_review"
    else:
        return "not_recommended"


def generate_recommendation_summary(
    recommendation: str,
    scores: Dict[str, float],
    key_risks: List[Dict],
    key_strengths: List[Dict]
) -> str:
    """
    Generate human-readable recommendation summary.
    """
    summaries = {
        "strong_proceed": "Deal shows strong fundamentals across financial, operational, and quality metrics with no major risk factors identified.",
        "proceed_with_caution": "Deal has acceptable metrics but requires attention to identified risk areas during due diligence.",
        "needs_further_review": "Deal has mixed signals requiring additional analysis and verification before proceeding.",
        "not_recommended": "Deal has significant concerns that would require substantial turnaround effort.",
        "pass": "Multiple high-severity risks identified. Recommend passing unless strategic considerations override.",
    }

    base = summaries.get(recommendation, "")

    # Add specific callouts
    callouts = []
    if scores.get("financial_score", 0) < 40:
        callouts.append("Financial metrics are concerning.")
    if scores.get("quality_score", 0) < 40:
        callouts.append("Quality indicators need improvement.")
    if scores.get("operational_score", 0) > 70:
        callouts.append("Strong operational profile.")

    if callouts:
        base += " " + " ".join(callouts)

    return base


def calculate_deal_scorecard(
    db: Session,
    deal_id: int
) -> models.DealScorecard:
    """
    Calculate comprehensive deal scorecard.
    """
    # Calculate component scores
    financial_score = calculate_financial_score(db, deal_id)
    operational_score = calculate_operational_score(db, deal_id)
    quality_score = calculate_quality_score(db, deal_id)
    compliance_score = calculate_compliance_score(db, deal_id)

    # Market score (placeholder - could integrate external data)
    market_score = 50.0

    # Lease score (placeholder)
    lease_score = 50.0

    # Calculate overall score (weighted average)
    weights = {
        "financial": 0.30,
        "operational": 0.25,
        "quality": 0.20,
        "compliance": 0.15,
        "market": 0.05,
        "lease": 0.05,
    }

    overall_score = (
        financial_score * weights["financial"] +
        operational_score * weights["operational"] +
        quality_score * weights["quality"] +
        compliance_score * weights["compliance"] +
        market_score * weights["market"] +
        lease_score * weights["lease"]
    )

    # Get risk flags
    flags = db.query(models.RiskFlag).filter(
        models.RiskFlag.deal_id == deal_id,
        models.RiskFlag.status == "open"
    ).all()

    high_risk_count = len([f for f in flags if f.severity == "high"])

    key_risks = [
        {"title": f.title, "severity": f.severity, "category": f.risk_category}
        for f in flags[:5]
    ]

    # Identify strengths
    key_strengths = []
    if financial_score >= 70:
        key_strengths.append({"area": "financial", "description": "Strong financial performance"})
    if operational_score >= 70:
        key_strengths.append({"area": "operational", "description": "Solid operational metrics"})
    if quality_score >= 70:
        key_strengths.append({"area": "quality", "description": "Good quality indicators"})

    # Generate recommendation
    recommendation = generate_recommendation(overall_score, high_risk_count, key_risks)

    scores = {
        "financial_score": financial_score,
        "operational_score": operational_score,
        "quality_score": quality_score,
    }
    recommendation_summary = generate_recommendation_summary(
        recommendation, scores, key_risks, key_strengths
    )

    # Get or create scorecard
    scorecard = db.query(models.DealScorecard).filter(
        models.DealScorecard.deal_id == deal_id
    ).first()

    if not scorecard:
        scorecard = models.DealScorecard(deal_id=deal_id)
        db.add(scorecard)

    # Update scorecard
    scorecard.financial_score = financial_score
    scorecard.operational_score = operational_score
    scorecard.compliance_score = compliance_score
    scorecard.quality_score = quality_score
    scorecard.market_score = market_score
    scorecard.lease_score = lease_score
    scorecard.overall_score = overall_score
    scorecard.recommendation = recommendation
    scorecard.recommendation_summary = recommendation_summary
    scorecard.key_risks = key_risks
    scorecard.key_strengths = key_strengths
    scorecard.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(scorecard)

    return scorecard
