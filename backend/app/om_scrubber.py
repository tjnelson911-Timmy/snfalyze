"""
OM/CIM Scrubber Module

Specialized extraction and verification for Offering Memorandum documents.
Compares OM claims against supporting evidence documents.
"""
import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session

from . import models, schemas


# ============================================================================
# OM CLAIM EXTRACTION PATTERNS
# ============================================================================

OM_CLAIM_PATTERNS = {
    "financial": {
        "revenue": {
            "patterns": [
                r"(?:annual|total|gross)\s+revenue\s+(?:of\s+)?(?:approximately\s+)?\$?([\d,]+(?:\.\d+)?)\s*(?:M|million)?",
                r"revenue\s+(?:is|was|of)\s+(?:approximately\s+)?\$?([\d,]+(?:\.\d+)?)",
                r"\$?([\d,]+(?:\.\d+)?)\s*(?:M|million)?\s+(?:in\s+)?(?:annual\s+)?revenue",
            ],
            "units": "dollars",
            "multiplier_patterns": {r"(\d+\.?\d*)\s*M|million": 1000000}
        },
        "ebitdar": {
            "patterns": [
                r"ebitdar\s+(?:of\s+)?(?:approximately\s+)?\$?([\d,]+(?:\.\d+)?)\s*(?:M|million)?",
                r"\$?([\d,]+(?:\.\d+)?)\s*(?:M|million)?\s+ebitdar",
                r"trailing\s+(?:twelve\s+month|12[- ]month|ttm)\s+ebitdar\s+(?:of\s+)?\$?([\d,]+(?:\.\d+)?)",
            ],
            "units": "dollars",
            "multiplier_patterns": {r"(\d+\.?\d*)\s*M|million": 1000000}
        },
        "ebitda": {
            "patterns": [
                r"ebitda\s+(?:of\s+)?(?:approximately\s+)?\$?([\d,]+(?:\.\d+)?)\s*(?:M|million)?",
                r"\$?([\d,]+(?:\.\d+)?)\s*(?:M|million)?\s+ebitda",
            ],
            "units": "dollars",
            "multiplier_patterns": {r"(\d+\.?\d*)\s*M|million": 1000000}
        },
        "noi": {
            "patterns": [
                r"(?:net\s+operating\s+income|noi)\s+(?:of\s+)?(?:approximately\s+)?\$?([\d,]+(?:\.\d+)?)",
                r"\$?([\d,]+(?:\.\d+)?)\s+(?:net\s+operating\s+income|noi)",
            ],
            "units": "dollars",
            "multiplier_patterns": {r"(\d+\.?\d*)\s*M|million": 1000000}
        },
        "margin": {
            "patterns": [
                r"(?:ebitdar|operating|profit)\s+margin\s+(?:of\s+)?([\d.]+)\s*%",
                r"([\d.]+)\s*%\s+(?:ebitdar|operating|profit)\s+margin",
            ],
            "units": "percent"
        },
        "asking_price": {
            "patterns": [
                r"(?:asking|list(?:ing)?)\s+price\s+(?:of\s+)?(?:approximately\s+)?\$?([\d,]+(?:\.\d+)?)\s*(?:M|million)?",
                r"offered\s+(?:at|for)\s+\$?([\d,]+(?:\.\d+)?)\s*(?:M|million)?",
                r"price(?:d)?\s+at\s+\$?([\d,]+(?:\.\d+)?)\s*(?:M|million)?",
            ],
            "units": "dollars",
            "multiplier_patterns": {r"(\d+\.?\d*)\s*M|million": 1000000}
        },
        "cap_rate": {
            "patterns": [
                r"cap(?:italization)?\s+rate\s+(?:of\s+)?([\d.]+)\s*%?",
                r"([\d.]+)\s*%?\s+cap\s+rate",
                r"going[- ]in\s+cap\s+(?:of\s+)?([\d.]+)",
            ],
            "units": "percent"
        },
        "price_per_bed": {
            "patterns": [
                r"(?:price\s+)?per\s+bed\s+(?:of\s+)?\$?([\d,]+)",
                r"\$?([\d,]+)\s+per\s+(?:licensed\s+)?bed",
            ],
            "units": "dollars"
        },
    },
    "operational": {
        "beds": {
            "patterns": [
                r"(\d+)\s+(?:licensed\s+)?(?:bed|unit)(?:s)?",
                r"(?:licensed\s+)?(?:bed|unit)\s+count\s+(?:of\s+)?(\d+)",
                r"(\d+)[- ]bed\s+(?:facility|community|property)",
            ],
            "units": "count"
        },
        "occupancy": {
            "patterns": [
                r"(?:current\s+)?occupancy\s+(?:rate\s+)?(?:of\s+|at\s+)?([\d.]+)\s*%",
                r"([\d.]+)\s*%\s+(?:current\s+)?occupancy",
                r"averaging\s+([\d.]+)\s*%\s+occupancy",
                r"stabilized\s+(?:at\s+)?([\d.]+)\s*%",
            ],
            "units": "percent"
        },
        "census": {
            "patterns": [
                r"(?:average\s+)?(?:daily\s+)?census\s+(?:of\s+)?(\d+)",
                r"(\d+)\s+(?:average\s+)?(?:daily\s+)?census",
                r"adc\s+(?:of\s+)?(\d+)",
            ],
            "units": "count"
        },
        "payor_medicare": {
            "patterns": [
                r"medicare\s+(?:is\s+|at\s+)?([\d.]+)\s*%",
                r"([\d.]+)\s*%\s+medicare",
            ],
            "units": "percent"
        },
        "payor_medicaid": {
            "patterns": [
                r"medicaid\s+(?:is\s+|at\s+)?([\d.]+)\s*%",
                r"([\d.]+)\s*%\s+medicaid",
            ],
            "units": "percent"
        },
        "payor_private": {
            "patterns": [
                r"private\s+pay\s+(?:is\s+|at\s+)?([\d.]+)\s*%",
                r"([\d.]+)\s*%\s+private\s+pay",
            ],
            "units": "percent"
        },
    },
    "quality": {
        "star_rating": {
            "patterns": [
                r"(\d+)[- ]star\s+(?:overall\s+)?(?:rating|facility)",
                r"(?:cms|medicare)\s+(?:overall\s+)?rating\s+(?:of\s+)?(\d+)",
                r"overall\s+(?:star\s+)?rating\s+(?:of\s+)?(\d+)",
            ],
            "units": "rating"
        },
        "health_inspection_rating": {
            "patterns": [
                r"health\s+inspection\s+(?:rating\s+)?(?:of\s+)?(\d+)",
                r"(\d+)[- ]star\s+health\s+inspection",
            ],
            "units": "rating"
        },
        "staffing_rating": {
            "patterns": [
                r"staffing\s+(?:rating\s+)?(?:of\s+)?(\d+)",
                r"(\d+)[- ]star\s+staffing",
            ],
            "units": "rating"
        },
        "deficiencies": {
            "patterns": [
                r"(\d+)\s+(?:total\s+)?deficienc(?:y|ies)",
                r"deficiency[- ]free",
                r"zero\s+deficiencies",
            ],
            "units": "count"
        },
    },
    "staffing": {
        "hprd": {
            "patterns": [
                r"([\d.]+)\s+(?:total\s+)?hprd",
                r"hours\s+per\s+(?:resident|patient)\s+day\s+(?:of\s+)?([\d.]+)",
                r"([\d.]+)\s+nursing\s+hours",
            ],
            "units": "hours"
        },
        "rn_hprd": {
            "patterns": [
                r"([\d.]+)\s+rn\s+hprd",
                r"rn\s+hours?\s+(?:of\s+)?([\d.]+)",
            ],
            "units": "hours"
        },
    },
}


def extract_om_claims(text: str, document_id: int, deal_id: int) -> List[Dict]:
    """
    Extract claims from OM/CIM text.
    Returns list of claim dictionaries ready to be stored.
    """
    claims = []
    text_lower = text.lower()

    for category, type_configs in OM_CLAIM_PATTERNS.items():
        for claim_type, config in type_configs.items():
            for pattern in config["patterns"]:
                for match in re.finditer(pattern, text_lower, re.IGNORECASE):
                    # Get the matched value
                    value = match.group(1) if match.groups() else None

                    # Handle special cases
                    if value is None:
                        if "deficiency-free" in match.group(0) or "zero deficiencies" in match.group(0):
                            value = "0"
                        else:
                            continue

                    # Clean and parse numeric value
                    numeric_value = None
                    try:
                        clean_value = value.replace(",", "")
                        numeric_value = float(clean_value)

                        # Apply multipliers
                        if "multiplier_patterns" in config:
                            for mult_pattern, multiplier in config["multiplier_patterns"].items():
                                if re.search(mult_pattern, text[match.start():match.end()+20], re.IGNORECASE):
                                    numeric_value *= multiplier
                                    break
                    except ValueError:
                        pass

                    # Get context (surrounding sentence)
                    sentence_start = max(0, text.rfind('.', 0, match.start()) + 1)
                    sentence_end = text.find('.', match.end())
                    if sentence_end == -1:
                        sentence_end = min(len(text), match.end() + 200)
                    claim_text = text[sentence_start:sentence_end].strip()

                    # Get snippet for provenance
                    snippet_start = max(0, match.start() - 50)
                    snippet_end = min(len(text), match.end() + 50)
                    snippet = text[snippet_start:snippet_end].strip()

                    claims.append({
                        "document_id": document_id,
                        "deal_id": deal_id,
                        "claim_category": category,
                        "claim_type": claim_type,
                        "claim_text": claim_text[:500],
                        "claimed_value": value,
                        "numeric_value": numeric_value,
                        "units": config.get("units"),
                        "source_snippet": snippet,
                        "confidence": 0.7,
                        "verification_status": "pending"
                    })
                    break  # Only take first match per claim type

    return claims


def find_evidence_for_claim(
    db: Session,
    claim: models.Claim,
    deal_id: int
) -> List[Dict]:
    """
    Search for evidence in other documents that could verify or dispute a claim.
    Returns list of potential evidence matches.
    """
    evidence = []

    # Get extracted fields from other documents
    fields = db.query(models.ExtractedField).filter(
        models.ExtractedField.deal_id == deal_id,
        models.ExtractedField.document_id != claim.document_id
    ).all()

    # Map claim types to field keys
    claim_field_mapping = {
        "revenue": ["revenue", "total_revenue"],
        "ebitdar": ["ebitdar"],
        "ebitda": ["ebitda"],
        "noi": ["noi", "net_operating_income"],
        "beds": ["beds", "licensed_beds", "bed_count"],
        "occupancy": ["occupancy", "occupancy_rate"],
        "cap_rate": ["cap_rate"],
        "margin": ["margin", "operating_margin", "ebitdar_margin"],
        "star_rating": ["star_rating", "overall_rating"],
    }

    related_keys = claim_field_mapping.get(claim.claim_type, [claim.claim_type])

    for field in fields:
        if field.field_key.lower() in related_keys:
            evidence.append({
                "type": "extracted_field",
                "source_document_id": field.document_id,
                "field_id": field.id,
                "field_key": field.field_key,
                "field_value": field.field_value,
                "numeric_value": field.numeric_value,
                "source_snippet": field.source_snippet,
                "confidence": field.confidence
            })

    # Also check financial line items for financial claims
    if claim.claim_category == "financial":
        account_mapping = {
            "revenue": ["REV-999", "REV-100"],
            "ebitdar": ["SUM-100"],
            "ebitda": ["SUM-110"],
            "noi": ["SUM-130"],
        }

        account_codes = account_mapping.get(claim.claim_type, [])
        if account_codes:
            line_items = db.query(models.FinancialLineItem).filter(
                models.FinancialLineItem.deal_id == deal_id,
                models.FinancialLineItem.standard_account_code.in_(account_codes)
            ).all()

            for item in line_items:
                evidence.append({
                    "type": "financial_line_item",
                    "source_document_id": item.document_id,
                    "account_code": item.standard_account_code,
                    "amount": item.amount,
                    "period_type": item.period_type,
                    "period_label": item.period_label,
                })

    return evidence


def calculate_variance(
    claimed_value: Optional[float],
    evidence_value: Optional[float]
) -> Tuple[Optional[float], Optional[float]]:
    """
    Calculate variance between claimed and evidence values.
    Returns (variance_amount, variance_percent).
    """
    if claimed_value is None or evidence_value is None:
        return None, None

    if claimed_value == 0:
        if evidence_value == 0:
            return 0, 0
        return None, None

    variance = evidence_value - claimed_value
    variance_pct = (variance / claimed_value) * 100

    return variance, variance_pct


def determine_severity(variance_pct: Optional[float], claim_type: str) -> str:
    """
    Determine severity of a variance based on magnitude and claim type.
    """
    if variance_pct is None:
        return "unknown"

    abs_variance = abs(variance_pct)

    # Different thresholds for different claim types
    high_sensitivity = ["ebitdar", "ebitda", "noi", "revenue"]  # 5% = high
    medium_sensitivity = ["occupancy", "margin", "cap_rate"]    # 10% = high
    low_sensitivity = ["beds", "star_rating"]                   # 20% = high

    if claim_type in high_sensitivity:
        if abs_variance > 10:
            return "high"
        elif abs_variance > 5:
            return "medium"
        else:
            return "low"
    elif claim_type in medium_sensitivity:
        if abs_variance > 15:
            return "high"
        elif abs_variance > 10:
            return "medium"
        else:
            return "low"
    else:
        if abs_variance > 20:
            return "high"
        elif abs_variance > 10:
            return "medium"
        else:
            return "low"


def generate_om_scrub_report(
    db: Session,
    document_id: int
) -> schemas.OMScrubReport:
    """
    Generate a comprehensive OM scrub report for a document.
    """
    doc = db.query(models.Document).filter(models.Document.id == document_id).first()
    if not doc:
        raise ValueError(f"Document {document_id} not found")

    # Get all claims from this document
    claims = db.query(models.Claim).filter(
        models.Claim.document_id == document_id
    ).all()

    claims_summary = []
    variances = []
    red_flags = []
    diligence_questions = []

    for claim in claims:
        # Build claim summary
        claim_summary = schemas.OMClaimSummary(
            claim_id=claim.id,
            category=claim.claim_category,
            type=claim.claim_type,
            claim_text=claim.claim_text,
            claimed_value=claim.claimed_value,
            timeframe=claim.timeframe,
            confidence=claim.confidence,
            source_page=claim.source_page,
            source_snippet=claim.source_snippet,
            verified_value=claim.verified_value,
            variance_pct=claim.variance_pct,
            status=claim.verification_status,
            is_red_flag=claim.is_red_flag
        )
        claims_summary.append(claim_summary)

        # Check for variances
        if claim.variance is not None and claim.variance != 0:
            severity = determine_severity(claim.variance_pct, claim.claim_type)
            variances.append(schemas.OMVarianceItem(
                claim_type=claim.claim_type,
                om_value=claim.claimed_value or "",
                evidence_value=claim.verified_value or "",
                variance=f"{claim.variance:,.2f}" if claim.variance else "",
                variance_pct=claim.variance_pct or 0,
                evidence_source="Financial data",
                severity=severity
            ))

            # Add to red flags if high severity
            if severity == "high":
                red_flags.append(
                    f"Large variance in {claim.claim_type}: OM claims {claim.claimed_value}, "
                    f"evidence shows {claim.verified_value} ({claim.variance_pct:+.1f}%)"
                )

        # Generate diligence questions for unverified claims
        if claim.verification_status == "pending":
            diligence_questions.append(
                f"Verify {claim.claim_type}: OM states '{claim.claimed_value}'. "
                f"Request supporting documentation."
            )

    # Add standard diligence questions
    standard_questions = [
        "Request trailing 12-month P&L to verify EBITDAR claims",
        "Obtain current census report to verify occupancy",
        "Request most recent CMS survey report",
        "Verify payor mix with recent AR aging report",
    ]

    for q in standard_questions:
        if q not in diligence_questions:
            diligence_questions.append(q)

    # Calculate overall confidence
    if claims:
        verified_claims = [c for c in claims if c.verification_status == "verified"]
        overall_confidence = len(verified_claims) / len(claims)
    else:
        overall_confidence = 0.0

    return schemas.OMScrubReport(
        deal_id=doc.deal_id,
        document_id=document_id,
        document_name=doc.original_filename,
        generated_at=datetime.utcnow(),
        claims_summary=claims_summary,
        variances=variances,
        red_flags=red_flags,
        diligence_questions=diligence_questions[:10],  # Limit to top 10
        overall_confidence=overall_confidence
    )


def verify_claims_against_evidence(db: Session, deal_id: int) -> int:
    """
    Automatically verify claims against extracted evidence.
    Returns count of claims updated.
    """
    claims = db.query(models.Claim).filter(
        models.Claim.deal_id == deal_id,
        models.Claim.verification_status == "pending"
    ).all()

    updated_count = 0

    for claim in claims:
        evidence = find_evidence_for_claim(db, claim, deal_id)

        if not evidence:
            continue

        # Find best matching evidence
        best_match = None
        best_confidence = 0

        for ev in evidence:
            if ev.get("confidence", 0) > best_confidence:
                if ev["type"] == "extracted_field" and ev.get("numeric_value"):
                    best_match = ev
                    best_confidence = ev.get("confidence", 0)
                elif ev["type"] == "financial_line_item" and ev.get("amount"):
                    best_match = ev
                    best_confidence = 0.8  # Default high confidence for financial data

        if best_match:
            evidence_value = best_match.get("numeric_value") or best_match.get("amount")

            if evidence_value and claim.numeric_value:
                variance, variance_pct = calculate_variance(claim.numeric_value, evidence_value)

                claim.verified_value = str(evidence_value)
                claim.variance = variance
                claim.variance_pct = variance_pct

                # Determine verification status
                severity = determine_severity(variance_pct, claim.claim_type)
                if severity == "low":
                    claim.verification_status = "verified"
                elif severity == "high":
                    claim.verification_status = "flagged"
                    claim.is_red_flag = True
                else:
                    claim.verification_status = "disputed"

                updated_count += 1

    db.commit()
    return updated_count
