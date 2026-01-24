"""
Export and Report Generation Module

Generates IC memos, OM scrub reports, and data exports.
"""
import io
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from . import models, schemas
from . import financial_ingestion
from . import risk_scoring
from . import om_scrubber


# ============================================================================
# IC MEMO GENERATION
# ============================================================================

def generate_ic_memo(db: Session, deal_id: int) -> Dict[str, Any]:
    """
    Generate Investment Committee memo content.
    Returns structured data that can be rendered as HTML, PDF, or Word.
    """
    deal = db.query(models.Deal).filter(models.Deal.id == deal_id).first()
    if not deal:
        raise ValueError(f"Deal {deal_id} not found")

    # Get related data
    properties = db.query(models.Property).filter(models.Property.deal_id == deal_id).all()
    documents = db.query(models.Document).filter(models.Document.deal_id == deal_id).all()
    risk_flags = db.query(models.RiskFlag).filter(
        models.RiskFlag.deal_id == deal_id,
        models.RiskFlag.status == "open"
    ).all()
    scenarios = db.query(models.Scenario).filter(models.Scenario.deal_id == deal_id).all()

    # Get scorecard
    scorecard = db.query(models.DealScorecard).filter(
        models.DealScorecard.deal_id == deal_id
    ).first()

    # Get financial metrics
    try:
        fin_metrics = financial_ingestion.calculate_summary_metrics(db, deal_id)
    except:
        fin_metrics = {}

    # Get verified claims
    claims = db.query(models.Claim).filter(
        models.Claim.deal_id == deal_id,
        models.Claim.verification_status == "verified"
    ).all()

    # Build memo structure
    memo = {
        "generated_at": datetime.utcnow().isoformat(),
        "deal": {
            "id": deal.id,
            "name": deal.name,
            "status": deal.status,
            "deal_type": deal.deal_type,
            "asking_price": deal.asking_price,
            "ebitdar": deal.ebitdar,
            "cap_rate": deal.cap_rate,
            "total_beds": deal.total_beds,
            "price_per_bed": deal.price_per_bed,
            "broker": {
                "name": deal.broker_name,
                "company": deal.broker_company,
                "email": deal.broker_email,
                "phone": deal.broker_phone,
            },
            "seller_name": deal.seller_name,
            "source": deal.source,
            "investment_thesis": deal.investment_thesis,
        },
        "executive_summary": {
            "recommendation": scorecard.recommendation if scorecard else None,
            "recommendation_summary": scorecard.recommendation_summary if scorecard else None,
            "overall_score": scorecard.overall_score if scorecard else None,
            "key_metrics": {
                "asking_price": deal.asking_price,
                "ebitdar": fin_metrics.get("ebitdar") or deal.ebitdar,
                "ebitdar_margin": fin_metrics.get("ebitdar_margin"),
                "cap_rate": deal.cap_rate,
                "total_beds": deal.total_beds,
                "price_per_bed": deal.price_per_bed,
                "occupancy": _avg_property_metric(properties, "current_occupancy"),
            }
        },
        "portfolio_summary": {
            "property_count": len(properties),
            "total_beds": sum(p.licensed_beds or 0 for p in properties),
            "states": list(set(p.state for p in properties if p.state)),
            "properties": [
                {
                    "name": p.name,
                    "type": p.property_type,
                    "city": p.city,
                    "state": p.state,
                    "beds": p.licensed_beds,
                    "star_rating": p.star_rating,
                    "occupancy": p.current_occupancy,
                }
                for p in properties
            ]
        },
        "financial_analysis": {
            "metrics": fin_metrics,
            "scenarios": [
                {
                    "name": s.name,
                    "description": s.description,
                    "is_base_case": s.is_base_case,
                    "ebitdar": s.ebitdar,
                    "noi": s.noi,
                    "cap_rate": s.cap_rate,
                    "implied_value": s.implied_value,
                    "price_per_bed": s.price_per_bed,
                }
                for s in scenarios
            ]
        },
        "scorecard": {
            "financial_score": scorecard.financial_score if scorecard else None,
            "operational_score": scorecard.operational_score if scorecard else None,
            "quality_score": scorecard.quality_score if scorecard else None,
            "compliance_score": scorecard.compliance_score if scorecard else None,
            "overall_score": scorecard.overall_score if scorecard else None,
        } if scorecard else None,
        "risk_assessment": {
            "high_risks": [
                {
                    "title": f.title,
                    "category": f.risk_category,
                    "description": f.description,
                    "recommendation": f.recommendation,
                }
                for f in risk_flags if f.severity == "high"
            ],
            "medium_risks": [
                {
                    "title": f.title,
                    "category": f.risk_category,
                    "description": f.description,
                }
                for f in risk_flags if f.severity == "medium"
            ],
            "key_strengths": scorecard.key_strengths if scorecard else [],
        },
        "diligence_summary": {
            "documents_reviewed": len(documents),
            "claims_verified": len(claims),
            "verified_claims": [
                {
                    "category": c.claim_category,
                    "type": c.claim_type,
                    "claimed": c.claimed_value,
                    "verified": c.verified_value,
                }
                for c in claims[:10]
            ]
        },
        "notes": deal.notes,
    }

    return memo


def _avg_property_metric(properties: List[models.Property], metric: str) -> Optional[float]:
    """Calculate average of a property metric."""
    values = [getattr(p, metric) for p in properties if getattr(p, metric, None)]
    return sum(values) / len(values) if values else None


def _fmt_currency(val):
    """Format currency value."""
    if val is None:
        return "N/A"
    if val >= 1000000:
        return f"${val/1000000:,.1f}M"
    return f"${val:,.0f}"


def _fmt_pct(val):
    """Format percentage value."""
    if val is None:
        return "N/A"
    return f"{val:.1f}%"


def _format_recommendation(rec: Optional[str]) -> str:
    """Format recommendation for display."""
    mapping = {
        "strong_proceed": "Strong Proceed",
        "proceed_with_caution": "Proceed with Caution",
        "needs_further_review": "Needs Further Review",
        "not_recommended": "Not Recommended",
        "pass": "Pass",
    }
    return mapping.get(rec, rec or "Pending Analysis")


def _render_property_rows(properties, fmt_pct_fn):
    """Render property table rows."""
    rows = []
    for p in properties:
        stars = "⭐" * (p["star_rating"] or 0) if p.get("star_rating") else "N/A"
        row = f"""
        <tr>
            <td>{p['name']}</td>
            <td>{p['city']}, {p['state']}</td>
            <td>{p['beds'] or 'N/A'}</td>
            <td>{stars}</td>
            <td>{fmt_pct_fn(p['occupancy'])}</td>
        </tr>"""
        rows.append(row)
    return "".join(rows)


def _render_scenario_rows(scenarios, fmt_currency_fn, fmt_pct_fn):
    """Render scenario table rows."""
    rows = []
    for s in scenarios:
        base_label = " (Base Case)" if s["is_base_case"] else ""
        row = f"""<tr>
            <td>{s['name']}{base_label}</td>
            <td>{fmt_currency_fn(s['ebitdar'])}</td>
            <td>{fmt_pct_fn(s['cap_rate'])}</td>
            <td>{fmt_currency_fn(s['implied_value'])}</td>
            <td>{fmt_currency_fn(s['price_per_bed'])}</td>
        </tr>"""
        rows.append(row)
    return "".join(rows)


def _render_high_risks(risks):
    """Render high risk items."""
    if not risks:
        return "<p>No high priority risks identified.</p>"
    items = []
    for r in risks:
        item = f"""
    <div class="risk-item high">
        <strong>{r['title']}</strong> ({r['category']})
        <p>{r['description']}</p>
        <p><em>Recommendation: {r['recommendation']}</em></p>
    </div>"""
        items.append(item)
    return "".join(items)


def _render_medium_risks(risks):
    """Render medium risk items."""
    if not risks:
        return "<p>No medium priority risks identified.</p>"
    items = []
    for r in risks:
        item = f"""
    <div class="risk-item medium">
        <strong>{r['title']}</strong> ({r['category']})
        <p>{r['description']}</p>
    </div>"""
        items.append(item)
    return "".join(items)


def _render_strengths(strengths):
    """Render key strengths."""
    if not strengths:
        return ""
    items = []
    for s in strengths:
        area = s.get("area", "General")
        desc = s.get("description", "")
        items.append(f"<li><strong>{area}:</strong> {desc}</li>")
    return f"""
    <h3>Key Strengths</h3>
    <ul>
        {"".join(items)}
    </ul>"""


def _generate_scorecard_html(scorecard: Dict) -> str:
    """Generate scorecard section HTML."""
    def score_bar(score, label):
        if score is None:
            return f"<p>{label}: N/A</p>"
        color = "#38a169" if score >= 70 else "#d69e2e" if score >= 50 else "#e53e3e"
        return f"""
        <p><strong>{label}:</strong> {score:.0f}/100</p>
        <div class="score-bar"><div class="score-fill" style="width: {score}%; background: {color};"></div></div>
        """

    fin_bar = score_bar(scorecard.get("financial_score"), "Financial")
    ops_bar = score_bar(scorecard.get("operational_score"), "Operational")
    qual_bar = score_bar(scorecard.get("quality_score"), "Quality")
    comp_bar = score_bar(scorecard.get("compliance_score"), "Compliance")
    overall = scorecard.get("overall_score", 0)

    return f"""
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
        <div>
            {fin_bar}
            {ops_bar}
            {qual_bar}
        </div>
        <div>
            {comp_bar}
            <div style="margin-top: 20px; padding: 15px; background: #edf2f7; border-radius: 8px;">
                <strong>Overall Score:</strong>
                <div style="font-size: 36px; font-weight: bold; color: #1a365d;">{overall:.0f}</div>
            </div>
        </div>
    </div>
    """


def generate_ic_memo_html(db: Session, deal_id: int) -> str:
    """
    Generate IC memo as HTML document.
    """
    memo = generate_ic_memo(db, deal_id)
    deal = memo["deal"]
    summary = memo["executive_summary"]
    portfolio = memo["portfolio_summary"]
    financial = memo["financial_analysis"]
    scorecard = memo.get("scorecard", {})
    risks = memo["risk_assessment"]

    # Pre-render dynamic sections
    property_rows = _render_property_rows(portfolio["properties"], _fmt_pct)
    scenario_section = ""
    if financial["scenarios"]:
        scenario_rows = _render_scenario_rows(financial["scenarios"], _fmt_currency, _fmt_pct)
        scenario_section = f"""
    <h3>Scenario Analysis</h3>
    <table>
        <tr><th>Scenario</th><th>EBITDAR</th><th>Cap Rate</th><th>Implied Value</th><th>Price/Bed</th></tr>
        {scenario_rows}
    </table>"""

    high_risks_html = _render_high_risks(risks["high_risks"])
    medium_risks_html = _render_medium_risks(risks["medium_risks"])
    strengths_html = _render_strengths(risks.get("key_strengths", []))
    scorecard_html = _generate_scorecard_html(scorecard) if scorecard else "<p>Scorecard not yet calculated.</p>"

    states_str = ", ".join(portfolio["states"]) if portfolio["states"] else "N/A"
    rec_class = summary.get("recommendation", "")
    rec_text = _format_recommendation(summary.get("recommendation"))
    rec_summary = summary.get("recommendation_summary", "")

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>IC Memo - {deal['name']}</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #1a365d; border-bottom: 2px solid #1a365d; padding-bottom: 10px; }}
        h2 {{ color: #2c5282; margin-top: 30px; }}
        h3 {{ color: #4a5568; }}
        .metric-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin: 20px 0; }}
        .metric-box {{ background: #f7fafc; padding: 15px; border-radius: 8px; text-align: center; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #1a365d; }}
        .metric-label {{ font-size: 12px; color: #718096; margin-top: 5px; }}
        .recommendation {{ padding: 15px; border-radius: 8px; margin: 20px 0; }}
        .recommendation.strong_proceed {{ background: #c6f6d5; border: 1px solid #38a169; }}
        .recommendation.proceed_with_caution {{ background: #fefcbf; border: 1px solid #d69e2e; }}
        .recommendation.needs_further_review {{ background: #fed7aa; border: 1px solid #dd6b20; }}
        .recommendation.not_recommended, .recommendation.pass {{ background: #fed7d7; border: 1px solid #e53e3e; }}
        .risk-item {{ padding: 10px; margin: 10px 0; border-left: 4px solid; }}
        .risk-item.high {{ border-color: #e53e3e; background: #fff5f5; }}
        .risk-item.medium {{ border-color: #dd6b20; background: #fffaf0; }}
        table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #e2e8f0; }}
        th {{ background: #edf2f7; font-weight: 600; }}
        .score-bar {{ height: 8px; background: #e2e8f0; border-radius: 4px; overflow: hidden; }}
        .score-fill {{ height: 100%; border-radius: 4px; }}
        .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #e2e8f0; font-size: 12px; color: #718096; }}
    </style>
</head>
<body>
    <h1>Investment Committee Memo</h1>
    <h2>{deal['name']}</h2>
    <p><strong>Date:</strong> {datetime.utcnow().strftime('%B %d, %Y')}</p>

    <h2>Executive Summary</h2>
    <div class="recommendation {rec_class}">
        <strong>Recommendation:</strong> {rec_text}
        <p>{rec_summary}</p>
    </div>

    <div class="metric-grid">
        <div class="metric-box">
            <div class="metric-value">{_fmt_currency(summary['key_metrics'].get('asking_price'))}</div>
            <div class="metric-label">Asking Price</div>
        </div>
        <div class="metric-box">
            <div class="metric-value">{_fmt_currency(summary['key_metrics'].get('ebitdar'))}</div>
            <div class="metric-label">EBITDAR</div>
        </div>
        <div class="metric-box">
            <div class="metric-value">{_fmt_pct(summary['key_metrics'].get('cap_rate'))}</div>
            <div class="metric-label">Cap Rate</div>
        </div>
        <div class="metric-box">
            <div class="metric-value">{summary['key_metrics'].get('total_beds') or 'N/A'}</div>
            <div class="metric-label">Total Beds</div>
        </div>
        <div class="metric-box">
            <div class="metric-value">{_fmt_currency(summary['key_metrics'].get('price_per_bed'))}</div>
            <div class="metric-label">Price/Bed</div>
        </div>
        <div class="metric-box">
            <div class="metric-value">{_fmt_pct(summary['key_metrics'].get('occupancy'))}</div>
            <div class="metric-label">Occupancy</div>
        </div>
    </div>

    <h2>Portfolio Overview</h2>
    <p><strong>{portfolio['property_count']}</strong> properties with <strong>{portfolio['total_beds']}</strong> total beds
    in {states_str}</p>

    <table>
        <tr>
            <th>Property</th>
            <th>Location</th>
            <th>Beds</th>
            <th>Star Rating</th>
            <th>Occupancy</th>
        </tr>
        {property_rows}
    </table>

    <h2>Financial Analysis</h2>
    <div class="metric-grid">
        <div class="metric-box">
            <div class="metric-value">{_fmt_currency(financial['metrics'].get('total_revenue'))}</div>
            <div class="metric-label">Total Revenue</div>
        </div>
        <div class="metric-box">
            <div class="metric-value">{_fmt_pct(financial['metrics'].get('ebitdar_margin'))}</div>
            <div class="metric-label">EBITDAR Margin</div>
        </div>
        <div class="metric-box">
            <div class="metric-value">{_fmt_pct(financial['metrics'].get('labor_ratio'))}</div>
            <div class="metric-label">Labor Ratio</div>
        </div>
    </div>

    {scenario_section}

    <h2>Scorecard</h2>
    {scorecard_html}

    <h2>Risk Assessment</h2>
    <h3>High Priority Risks</h3>
    {high_risks_html}

    <h3>Medium Priority Risks</h3>
    {medium_risks_html}

    {strengths_html}

    <h2>Investment Thesis</h2>
    <p>{deal.get('investment_thesis') or 'No investment thesis provided.'}</p>

    <h2>Additional Notes</h2>
    <p>{memo.get('notes') or 'No additional notes.'}</p>

    <div class="footer">
        <p>Generated by SNFalyze on {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</p>
        <p>This memo is for internal use only. All figures should be independently verified.</p>
    </div>
</body>
</html>
"""
    return html


# ============================================================================
# OM SCRUB REPORT EXPORT
# ============================================================================

def _render_variance_rows(variances):
    """Render variance table rows."""
    if not variances:
        return '<tr><td colspan="5">No variances detected.</td></tr>'

    def severity_color(sev):
        return {"high": "#e53e3e", "medium": "#dd6b20", "low": "#38a169"}.get(sev, "#718096")

    rows = []
    for v in variances:
        color = severity_color(v.severity)
        row = f"""
        <tr class="variance-{v.severity}">
            <td>{v.claim_type}</td>
            <td>{v.om_value}</td>
            <td>{v.evidence_value}</td>
            <td>{v.variance} ({v.variance_pct:+.1f}%)</td>
            <td style="color: {color}; font-weight: bold;">{v.severity.upper()}</td>
        </tr>"""
        rows.append(row)
    return "".join(rows)


def _render_claims_rows(claims):
    """Render claims table rows."""
    rows = []
    for c in claims:
        row = f"""
        <tr>
            <td>{c.category}</td>
            <td>{c.type}</td>
            <td>{c.claimed_value or 'N/A'}</td>
            <td>{c.status}</td>
            <td>{c.confidence*100:.0f}%</td>
        </tr>"""
        rows.append(row)
    return "".join(rows)


def _render_questions(questions):
    """Render diligence questions."""
    return "".join(f'<div class="question">{q}</div>' for q in questions)


def _render_red_flags(flags):
    """Render red flags."""
    if not flags:
        return "<p>No red flags identified.</p>"
    return "".join(f'<div class="red-flag">{flag}</div>' for flag in flags)


def export_om_scrub_report_html(db: Session, document_id: int) -> str:
    """
    Export OM scrub report as HTML.
    """
    report = om_scrubber.generate_om_scrub_report(db, document_id)

    variance_rows = _render_variance_rows(report.variances)
    claims_rows = _render_claims_rows(report.claims_summary)
    questions_html = _render_questions(report.diligence_questions)
    red_flags_html = _render_red_flags(report.red_flags)

    verified_count = len([c for c in report.claims_summary if c.status == "verified"])
    total_count = len(report.claims_summary)

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>OM Scrub Report - {report.document_name}</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #1a365d; }}
        h2 {{ color: #2c5282; margin-top: 30px; border-bottom: 1px solid #e2e8f0; padding-bottom: 10px; }}
        .summary-box {{ background: #f7fafc; padding: 20px; border-radius: 8px; margin: 20px 0; }}
        .confidence {{ font-size: 48px; font-weight: bold; color: #1a365d; }}
        table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #e2e8f0; }}
        th {{ background: #edf2f7; }}
        .red-flag {{ background: #fff5f5; padding: 10px; margin: 10px 0; border-left: 4px solid #e53e3e; }}
        .variance-high {{ background: #fff5f5; }}
        .variance-medium {{ background: #fffaf0; }}
        .variance-low {{ background: #f0fff4; }}
        .question {{ padding: 10px; margin: 5px 0; background: #ebf8ff; border-radius: 4px; }}
    </style>
</head>
<body>
    <h1>OM Scrub Report</h1>
    <p><strong>Document:</strong> {report.document_name}</p>
    <p><strong>Generated:</strong> {report.generated_at.strftime('%B %d, %Y at %H:%M UTC')}</p>

    <div class="summary-box">
        <div class="confidence">{report.overall_confidence*100:.0f}%</div>
        <p>Overall Verification Confidence</p>
        <p>{verified_count} of {total_count} claims verified</p>
    </div>

    <h2>Red Flags</h2>
    {red_flags_html}

    <h2>Variances Detected</h2>
    <table>
        <tr><th>Claim Type</th><th>OM Value</th><th>Evidence Value</th><th>Variance</th><th>Severity</th></tr>
        {variance_rows}
    </table>

    <h2>Claims Summary</h2>
    <table>
        <tr><th>Category</th><th>Type</th><th>Claimed Value</th><th>Status</th><th>Confidence</th></tr>
        {claims_rows}
    </table>

    <h2>Diligence Questions</h2>
    {questions_html}

    <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #e2e8f0; font-size: 12px; color: #718096;">
        <p>Generated by SNFalyze OM Scrubber</p>
    </div>
</body>
</html>
"""
    return html


# ============================================================================
# DATA EXPORTS
# ============================================================================

def export_deal_data_json(db: Session, deal_id: int) -> Dict[str, Any]:
    """
    Export all deal data as JSON for external analysis.
    """
    deal = db.query(models.Deal).filter(models.Deal.id == deal_id).first()
    if not deal:
        raise ValueError(f"Deal {deal_id} not found")

    # Get all related data
    properties = db.query(models.Property).filter(models.Property.deal_id == deal_id).all()
    documents = db.query(models.Document).filter(models.Document.deal_id == deal_id).all()
    claims = db.query(models.Claim).filter(models.Claim.deal_id == deal_id).all()
    extracted_fields = db.query(models.ExtractedField).filter(models.ExtractedField.deal_id == deal_id).all()
    financial_items = db.query(models.FinancialLineItem).filter(models.FinancialLineItem.deal_id == deal_id).all()
    coa_mappings = db.query(models.COAMapping).filter(models.COAMapping.deal_id == deal_id).all()
    risk_flags = db.query(models.RiskFlag).filter(models.RiskFlag.deal_id == deal_id).all()
    scenarios = db.query(models.Scenario).filter(models.Scenario.deal_id == deal_id).all()
    scorecard = db.query(models.DealScorecard).filter(models.DealScorecard.deal_id == deal_id).first()
    overrides = db.query(models.FieldOverride).filter(models.FieldOverride.deal_id == deal_id).all()

    return {
        "export_date": datetime.utcnow().isoformat(),
        "deal": {
            "id": deal.id,
            "name": deal.name,
            "status": deal.status,
            "deal_type": deal.deal_type,
            "priority": deal.priority,
            "asking_price": deal.asking_price,
            "ebitdar": deal.ebitdar,
            "cap_rate": deal.cap_rate,
            "total_beds": deal.total_beds,
            "price_per_bed": deal.price_per_bed,
            "broker_name": deal.broker_name,
            "broker_company": deal.broker_company,
            "seller_name": deal.seller_name,
            "source": deal.source,
            "notes": deal.notes,
            "investment_thesis": deal.investment_thesis,
            "created_at": deal.created_at.isoformat() if deal.created_at else None,
        },
        "properties": [
            {
                "id": p.id,
                "name": p.name,
                "property_type": p.property_type,
                "address": p.address,
                "city": p.city,
                "state": p.state,
                "licensed_beds": p.licensed_beds,
                "star_rating": p.star_rating,
                "current_occupancy": p.current_occupancy,
                "ebitdar": p.ebitdar,
                "latitude": p.latitude,
                "longitude": p.longitude,
            }
            for p in properties
        ],
        "documents": [
            {
                "id": d.id,
                "filename": d.original_filename,
                "file_type": d.file_type,
                "category": d.category,
                "doc_type": d.doc_type,
                "analyzed": d.analyzed,
                "parsing_status": d.parsing_status,
                "uploaded_at": d.uploaded_at.isoformat() if d.uploaded_at else None,
            }
            for d in documents
        ],
        "claims": [
            {
                "id": c.id,
                "document_id": c.document_id,
                "category": c.claim_category,
                "type": c.claim_type,
                "claim_text": c.claim_text,
                "claimed_value": c.claimed_value,
                "numeric_value": c.numeric_value,
                "verified_value": c.verified_value,
                "variance": c.variance,
                "variance_pct": c.variance_pct,
                "verification_status": c.verification_status,
                "is_red_flag": c.is_red_flag,
                "confidence": c.confidence,
            }
            for c in claims
        ],
        "extracted_fields": [
            {
                "id": f.id,
                "document_id": f.document_id,
                "field_key": f.field_key,
                "field_value": f.field_value,
                "numeric_value": f.numeric_value,
                "units": f.units,
                "confidence": f.confidence,
                "is_verified": f.is_verified,
                "extraction_method": f.extraction_method,
            }
            for f in extracted_fields
        ],
        "financial_line_items": [
            {
                "id": i.id,
                "document_id": i.document_id,
                "standard_account_code": i.standard_account_code,
                "period_type": i.period_type,
                "period_label": i.period_label,
                "amount": i.amount,
                "is_annualized": i.is_annualized,
                "is_adjusted": i.is_adjusted,
            }
            for i in financial_items
        ],
        "coa_mappings": [
            {
                "id": m.id,
                "seller_account_name": m.seller_account_name,
                "seller_account_number": m.seller_account_number,
                "standard_account_code": m.standard_account_code,
                "confidence": m.confidence,
                "mapping_status": m.mapping_status,
            }
            for m in coa_mappings
        ],
        "risk_flags": [
            {
                "id": r.id,
                "category": r.risk_category,
                "type": r.risk_type,
                "severity": r.severity,
                "title": r.title,
                "description": r.description,
                "recommendation": r.recommendation,
                "status": r.status,
            }
            for r in risk_flags
        ],
        "scenarios": [
            {
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "is_base_case": s.is_base_case,
                "assumptions": s.assumptions,
                "outputs": s.outputs,
                "ebitdar": s.ebitdar,
                "noi": s.noi,
                "cap_rate": s.cap_rate,
                "implied_value": s.implied_value,
                "price_per_bed": s.price_per_bed,
            }
            for s in scenarios
        ],
        "scorecard": {
            "financial_score": scorecard.financial_score,
            "operational_score": scorecard.operational_score,
            "quality_score": scorecard.quality_score,
            "compliance_score": scorecard.compliance_score,
            "market_score": scorecard.market_score,
            "overall_score": scorecard.overall_score,
            "recommendation": scorecard.recommendation,
            "recommendation_summary": scorecard.recommendation_summary,
            "key_risks": scorecard.key_risks,
            "key_strengths": scorecard.key_strengths,
        } if scorecard else None,
        "field_overrides": [
            {
                "id": o.id,
                "entity_type": o.entity_type,
                "entity_id": o.entity_id,
                "field_name": o.field_name,
                "old_value": o.old_value,
                "new_value": o.new_value,
                "reason": o.reason,
                "overridden_by": o.overridden_by,
                "created_at": o.created_at.isoformat() if o.created_at else None,
            }
            for o in overrides
        ],
    }


def export_financial_summary_csv(db: Session, deal_id: int) -> str:
    """
    Export financial line items as CSV.
    """
    items = db.query(models.FinancialLineItem).filter(
        models.FinancialLineItem.deal_id == deal_id
    ).order_by(
        models.FinancialLineItem.standard_account_code,
        models.FinancialLineItem.period_label
    ).all()

    # Get standard accounts for names
    accounts = {a.code: a.name for a in db.query(models.StandardAccount).all()}

    output = io.StringIO()
    output.write("Account Code,Account Name,Period,Amount,Is Annualized\n")

    for item in items:
        account_name = accounts.get(item.standard_account_code, item.standard_account_code or "Unmapped")
        output.write(f'"{item.standard_account_code or ""}","{account_name}","{item.period_label or ""}",{item.amount},{item.is_annualized}\n')

    return output.getvalue()
