"""
Deep Financial Analysis Module

Comprehensive financial analysis with trend analysis, benchmarking,
normalization, and pro forma export capabilities.
"""
import io
import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session

from . import models


# ============================================================================
# INDUSTRY BENCHMARKS
# ============================================================================

INDUSTRY_BENCHMARKS = {
    "revenue_ppd": {
        "medicaid": {"low": 180, "median": 220, "high": 280},
        "medicare": {"low": 450, "median": 550, "high": 700},
        "private_pay": {"low": 280, "median": 350, "high": 450},
        "blended": {"low": 250, "median": 320, "high": 420}
    },
    "expense_ratios": {
        "labor_to_revenue": {"excellent": 0.50, "good": 0.55, "average": 0.60, "poor": 0.65},
        "nursing_to_revenue": {"excellent": 0.35, "good": 0.40, "average": 0.45, "poor": 0.50},
        "therapy_to_revenue": {"excellent": 0.08, "good": 0.10, "average": 0.12, "poor": 0.15},
        "dietary_to_revenue": {"excellent": 0.05, "good": 0.06, "average": 0.07, "poor": 0.08},
        "admin_to_revenue": {"excellent": 0.08, "good": 0.10, "average": 0.12, "poor": 0.15},
    },
    "margins": {
        "ebitdar": {"excellent": 0.25, "good": 0.20, "average": 0.15, "poor": 0.10},
        "ebitda": {"excellent": 0.18, "good": 0.14, "average": 0.10, "poor": 0.06},
        "noi": {"excellent": 0.15, "good": 0.12, "average": 0.08, "poor": 0.04},
    },
    "staffing_hprd": {
        "rn": {"minimum": 0.5, "average": 0.75, "good": 1.0, "excellent": 1.25},
        "total_nursing": {"minimum": 3.5, "average": 4.0, "good": 4.5, "excellent": 5.0},
    },
    "occupancy": {
        "excellent": 0.92,
        "good": 0.88,
        "average": 0.82,
        "poor": 0.75,
        "breakeven_typical": 0.70
    }
}


def get_benchmark_rating(value: float, benchmark_category: str, metric: str) -> str:
    """
    Get a rating based on benchmark comparison.
    """
    benchmarks = INDUSTRY_BENCHMARKS.get(benchmark_category, {}).get(metric, {})
    if not benchmarks:
        return "unknown"

    if "excellent" in benchmarks:
        # Lower is better (for ratios)
        if benchmark_category == "expense_ratios":
            if value <= benchmarks.get("excellent", 0):
                return "excellent"
            elif value <= benchmarks.get("good", 0):
                return "good"
            elif value <= benchmarks.get("average", 0):
                return "average"
            else:
                return "poor"
        # Higher is better (for margins, occupancy)
        else:
            if value >= benchmarks.get("excellent", 1):
                return "excellent"
            elif value >= benchmarks.get("good", 0):
                return "good"
            elif value >= benchmarks.get("average", 0):
                return "average"
            else:
                return "poor"

    return "unknown"


# ============================================================================
# FINANCIAL METRICS CALCULATION
# ============================================================================

def calculate_per_patient_day_metrics(
    financials: Dict[str, float],
    patient_days: int,
    beds: int = None,
    occupancy: float = None
) -> Dict[str, Any]:
    """
    Calculate per-patient-day (PPD) metrics.
    """
    if not patient_days or patient_days == 0:
        # Estimate patient days from beds and occupancy
        if beds and occupancy:
            patient_days = beds * 365 * (occupancy / 100)
        else:
            return {"error": "Cannot calculate PPD without patient days or beds/occupancy"}

    ppd = {}

    for key, value in financials.items():
        if value and isinstance(value, (int, float)):
            ppd[f"{key}_ppd"] = round(value / patient_days, 2)

    ppd["patient_days"] = patient_days
    ppd["beds"] = beds
    ppd["occupancy"] = occupancy

    return ppd


def analyze_revenue_composition(
    revenue_items: List[Dict],
    total_revenue: float
) -> Dict[str, Any]:
    """
    Analyze revenue composition by payor and service type.
    """
    analysis = {
        "by_payor": {},
        "by_service": {},
        "concentration_risk": [],
        "recommendations": []
    }

    payor_mapping = {
        "REV-100": "medicaid",
        "REV-110": "medicare_a",
        "REV-120": "medicare_b",
        "REV-130": "managed_care",
        "REV-140": "private_pay",
        "REV-150": "other_government",
    }

    for item in revenue_items:
        code = item.get("standard_account_code", "")
        amount = item.get("amount", 0)

        if code in payor_mapping:
            payor = payor_mapping[code]
            if payor not in analysis["by_payor"]:
                analysis["by_payor"][payor] = 0
            analysis["by_payor"][payor] += amount

    # Calculate percentages and identify risks
    if total_revenue > 0:
        for payor, amount in analysis["by_payor"].items():
            pct = (amount / total_revenue) * 100
            analysis["by_payor"][payor] = {
                "amount": amount,
                "percentage": round(pct, 1)
            }

            # Check for concentration risk
            if pct > 60:
                analysis["concentration_risk"].append({
                    "payor": payor,
                    "percentage": pct,
                    "risk": "high",
                    "description": f"Over 60% revenue from {payor} creates significant payor risk"
                })
            elif pct > 45:
                analysis["concentration_risk"].append({
                    "payor": payor,
                    "percentage": pct,
                    "risk": "medium",
                    "description": f"Heavy reliance on {payor} ({pct:.0f}%)"
                })

        # Recommendations based on mix
        medicaid_pct = analysis["by_payor"].get("medicaid", {}).get("percentage", 0)
        medicare_pct = (
            analysis["by_payor"].get("medicare_a", {}).get("percentage", 0) +
            analysis["by_payor"].get("medicare_b", {}).get("percentage", 0)
        )
        private_pct = analysis["by_payor"].get("private_pay", {}).get("percentage", 0)

        if medicaid_pct > 70:
            analysis["recommendations"].append(
                "Consider strategies to increase Medicare and private pay census"
            )
        if medicare_pct < 15:
            analysis["recommendations"].append(
                "Medicare revenue below typical - evaluate therapy program and hospital relationships"
            )
        if private_pct < 5:
            analysis["recommendations"].append(
                "Private pay minimal - may indicate market positioning or quality perception issues"
            )

    return analysis


def analyze_expense_structure(
    expense_items: List[Dict],
    total_revenue: float,
    total_expenses: float,
    beds: int = None
) -> Dict[str, Any]:
    """
    Detailed expense structure analysis with benchmarking.
    """
    analysis = {
        "by_category": {},
        "labor_analysis": {},
        "non_labor_analysis": {},
        "benchmarks": {},
        "inefficiencies": [],
        "opportunities": []
    }

    # Categorize expenses
    category_mapping = {
        "nursing": ["EXP-100", "EXP-110", "EXP-120", "EXP-130", "EXP-140", "EXP-150"],
        "therapy": ["EXP-200", "EXP-210"],
        "dietary": ["EXP-300", "EXP-400"],
        "housekeeping": ["EXP-310", "EXP-430"],
        "maintenance": ["EXP-320", "EXP-530"],
        "admin": ["EXP-350", "EXP-820", "EXP-830"],
        "benefits": ["EXP-360"],
        "supplies": ["EXP-410", "EXP-420", "EXP-440"],
        "utilities": ["EXP-500"],
        "insurance": ["EXP-520", "EXP-600", "EXP-610"],
        "professional": ["EXP-700", "EXP-710", "EXP-720", "EXP-730"],
        "other": ["EXP-800", "EXP-810", "EXP-840", "EXP-850"],
        "management": ["EXP-900", "EXP-910"],
    }

    labor_categories = ["nursing", "therapy", "dietary", "housekeeping", "maintenance", "admin", "benefits"]

    for item in expense_items:
        code = item.get("standard_account_code", "")
        amount = item.get("amount", 0)

        for category, codes in category_mapping.items():
            if code in codes:
                if category not in analysis["by_category"]:
                    analysis["by_category"][category] = 0
                analysis["by_category"][category] += amount
                break

    # Calculate totals and ratios
    total_labor = sum(analysis["by_category"].get(cat, 0) for cat in labor_categories)
    total_non_labor = total_expenses - total_labor

    analysis["labor_analysis"] = {
        "total_labor": total_labor,
        "labor_to_revenue": round(total_labor / total_revenue, 3) if total_revenue else 0,
        "labor_to_expense": round(total_labor / total_expenses, 3) if total_expenses else 0,
    }

    analysis["non_labor_analysis"] = {
        "total_non_labor": total_non_labor,
        "non_labor_to_revenue": round(total_non_labor / total_revenue, 3) if total_revenue else 0,
    }

    # Benchmark comparisons
    if total_revenue > 0:
        for category, amount in analysis["by_category"].items():
            ratio = amount / total_revenue

            # Get benchmark if available
            benchmark_key = f"{category}_to_revenue"
            rating = get_benchmark_rating(ratio, "expense_ratios", benchmark_key)

            analysis["benchmarks"][category] = {
                "amount": amount,
                "percentage": round(ratio * 100, 1),
                "rating": rating
            }

            # Identify inefficiencies
            if rating == "poor":
                analysis["inefficiencies"].append({
                    "category": category,
                    "current_ratio": ratio,
                    "target_ratio": INDUSTRY_BENCHMARKS["expense_ratios"].get(benchmark_key, {}).get("average"),
                    "potential_savings": amount * 0.1 if amount else 0,  # Estimate 10% savings opportunity
                    "description": f"{category.title()} costs ({ratio*100:.1f}% of revenue) exceed industry benchmarks"
                })

        # Labor ratio analysis
        labor_ratio = analysis["labor_analysis"]["labor_to_revenue"]
        labor_rating = get_benchmark_rating(labor_ratio, "expense_ratios", "labor_to_revenue")
        analysis["labor_analysis"]["rating"] = labor_rating

        if labor_rating in ["poor", "average"]:
            target = INDUSTRY_BENCHMARKS["expense_ratios"]["labor_to_revenue"]["good"]
            savings = (labor_ratio - target) * total_revenue
            analysis["opportunities"].append({
                "type": "labor_optimization",
                "current": labor_ratio,
                "target": target,
                "potential_savings": savings,
                "description": f"Optimizing labor to {target*100:.0f}% of revenue could save ${savings:,.0f} annually"
            })

    return analysis


def calculate_breakeven_analysis(
    total_revenue: float,
    fixed_costs: float,
    variable_costs: float,
    beds: int,
    current_occupancy: float,
    revenue_per_patient_day: float
) -> Dict[str, Any]:
    """
    Calculate breakeven occupancy and scenario analysis.
    """
    if not all([total_revenue, beds, revenue_per_patient_day]):
        return {"error": "Insufficient data for breakeven analysis"}

    total_patient_days = beds * 365
    current_patient_days = total_patient_days * (current_occupancy / 100) if current_occupancy else 0

    # Estimate variable cost per patient day
    variable_cost_ppd = variable_costs / current_patient_days if current_patient_days else 0

    # Contribution margin per patient day
    contribution_margin_ppd = revenue_per_patient_day - variable_cost_ppd

    # Breakeven patient days
    if contribution_margin_ppd > 0:
        breakeven_patient_days = fixed_costs / contribution_margin_ppd
        breakeven_occupancy = (breakeven_patient_days / total_patient_days) * 100
    else:
        breakeven_patient_days = None
        breakeven_occupancy = None

    # Sensitivity analysis
    scenarios = []
    for occ_change in [-10, -5, 0, 5, 10]:
        scenario_occ = (current_occupancy or 80) + occ_change
        scenario_pd = total_patient_days * (scenario_occ / 100)
        scenario_revenue = scenario_pd * revenue_per_patient_day
        scenario_var_cost = scenario_pd * variable_cost_ppd
        scenario_margin = scenario_revenue - fixed_costs - scenario_var_cost

        scenarios.append({
            "occupancy": scenario_occ,
            "patient_days": round(scenario_pd),
            "revenue": round(scenario_revenue),
            "variable_costs": round(scenario_var_cost),
            "margin": round(scenario_margin),
            "margin_change_from_current": round(scenario_margin - (total_revenue - fixed_costs - variable_costs)) if current_occupancy else None
        })

    return {
        "current_occupancy": current_occupancy,
        "breakeven_occupancy": round(breakeven_occupancy, 1) if breakeven_occupancy else None,
        "cushion_above_breakeven": round(current_occupancy - breakeven_occupancy, 1) if breakeven_occupancy and current_occupancy else None,
        "revenue_per_patient_day": revenue_per_patient_day,
        "variable_cost_per_patient_day": round(variable_cost_ppd, 2),
        "contribution_margin_per_patient_day": round(contribution_margin_ppd, 2),
        "scenarios": scenarios
    }


def analyze_trends(
    line_items: List[Dict],
    periods: List[str]
) -> Dict[str, Any]:
    """
    Analyze financial trends across multiple periods.
    """
    trends = {
        "revenue_trend": [],
        "expense_trend": [],
        "margin_trend": [],
        "growth_rates": {},
        "volatility": {},
        "concerns": [],
        "positives": []
    }

    # Group by period
    by_period = {}
    for item in line_items:
        period = item.get("period_label", "Unknown")
        if period not in by_period:
            by_period[period] = {"revenue": 0, "expenses": 0}

        code = item.get("standard_account_code", "")
        amount = item.get("amount", 0)

        if code and code.startswith("REV-"):
            by_period[period]["revenue"] += amount
        elif code and code.startswith("EXP-"):
            by_period[period]["expenses"] += amount

    # Calculate trends
    sorted_periods = sorted(by_period.keys())
    for period in sorted_periods:
        data = by_period[period]
        margin = data["revenue"] - data["expenses"]
        margin_pct = (margin / data["revenue"] * 100) if data["revenue"] else 0

        trends["revenue_trend"].append({"period": period, "value": data["revenue"]})
        trends["expense_trend"].append({"period": period, "value": data["expenses"]})
        trends["margin_trend"].append({
            "period": period,
            "value": margin,
            "percentage": round(margin_pct, 1)
        })

    # Calculate growth rates
    if len(sorted_periods) >= 2:
        first_rev = by_period[sorted_periods[0]]["revenue"]
        last_rev = by_period[sorted_periods[-1]]["revenue"]
        if first_rev > 0:
            trends["growth_rates"]["revenue"] = round((last_rev - first_rev) / first_rev * 100, 1)

        first_exp = by_period[sorted_periods[0]]["expenses"]
        last_exp = by_period[sorted_periods[-1]]["expenses"]
        if first_exp > 0:
            trends["growth_rates"]["expenses"] = round((last_exp - first_exp) / first_exp * 100, 1)

        # Identify concerns
        if trends["growth_rates"].get("expenses", 0) > trends["growth_rates"].get("revenue", 0):
            trends["concerns"].append(
                "Expenses growing faster than revenue - margin compression risk"
            )

        # Check for declining revenue
        if trends["growth_rates"].get("revenue", 0) < 0:
            trends["concerns"].append(
                f"Revenue declining ({trends['growth_rates']['revenue']}%) - investigate census and rate changes"
            )

        # Check for positive trends
        if trends["growth_rates"].get("revenue", 0) > 5:
            trends["positives"].append(
                f"Strong revenue growth ({trends['growth_rates']['revenue']}%)"
            )

    return trends


# ============================================================================
# PRO FORMA EXPORT
# ============================================================================

def generate_proforma_template(
    db: Session,
    deal_id: int
) -> str:
    """
    Generate a pro forma template in CSV format ready for Excel.
    """
    # Get standard accounts
    accounts = db.query(models.StandardAccount).order_by(
        models.StandardAccount.display_order
    ).all()

    # Get existing financial data
    line_items = db.query(models.FinancialLineItem).filter(
        models.FinancialLineItem.deal_id == deal_id
    ).all()

    # Get deal info
    deal = db.query(models.Deal).filter(models.Deal.id == deal_id).first()

    # Build lookup of existing data
    existing_data = {}
    for item in line_items:
        key = (item.standard_account_code, item.period_label)
        existing_data[key] = item.amount

    # Generate CSV
    output = io.StringIO()

    # Header
    output.write("PRO FORMA FINANCIAL ANALYSIS\n")
    output.write(f"Deal: {deal.name if deal else 'Unknown'}\n")
    output.write(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d')}\n")
    output.write("\n")

    # Column headers
    periods = ["Historical T-12", "Year 1", "Year 2", "Year 3", "Year 4", "Year 5"]
    output.write(f"Account Code,Account Name,Category,{','.join(periods)},Notes\n")

    # Write each account
    current_category = None
    for account in accounts:
        # Add category header
        if account.category != current_category:
            current_category = account.category
            output.write(f"\n{current_category.upper()}\n")

        # Get historical value
        historical = existing_data.get((account.code, "TTM"), "")
        if not historical:
            historical = existing_data.get((account.code, "Annual"), "")

        # Write row with placeholders for projections
        output.write(f'"{account.code}","{account.name}","{account.subcategory or ""}",')
        output.write(f'{historical},,,,,,\n')

    # Add summary section
    output.write("\n\nSUMMARY METRICS\n")
    output.write(f"Metric,Formula,{','.join(periods)}\n")

    summary_rows = [
        ("Total Revenue", "SUM(Revenue)", "=SUM(B:B)", "", "", "", "", ""),
        ("Total Operating Expenses", "SUM(Expenses)", "=SUM(C:C)", "", "", "", "", ""),
        ("EBITDAR", "Revenue - OpEx", "=B1-C1", "", "", "", "", ""),
        ("EBITDAR Margin", "EBITDAR / Revenue", "=D1/B1", "", "", "", "", ""),
        ("Rent", "Fixed Charge", "", "", "", "", "", ""),
        ("EBITDA", "EBITDAR - Rent", "=D1-E1", "", "", "", "", ""),
        ("EBITDA Margin", "EBITDA / Revenue", "=F1/B1", "", "", "", "", ""),
    ]

    for row in summary_rows:
        output.write(",".join(str(x) for x in row) + "\n")

    # Add assumptions section
    output.write("\n\nASSUMPTIONS\n")
    output.write("Assumption,Value,Notes\n")
    assumptions = [
        ("Revenue Growth Rate", "3%", "Annual revenue growth assumption"),
        ("Expense Inflation", "2.5%", "Annual expense inflation"),
        ("Occupancy Target", "90%", "Stabilized occupancy target"),
        ("Cap Rate", "8%", "Exit cap rate assumption"),
        ("Discount Rate", "12%", "For DCF analysis"),
    ]
    for assumption in assumptions:
        output.write(f'"{assumption[0]}","{assumption[1]}","{assumption[2]}"\n')

    return output.getvalue()


# ============================================================================
# COMPREHENSIVE FINANCIAL ANALYSIS
# ============================================================================

def generate_deep_financial_analysis(
    db: Session,
    deal_id: int
) -> Dict[str, Any]:
    """
    Generate comprehensive financial analysis for a deal.
    """
    deal = db.query(models.Deal).filter(models.Deal.id == deal_id).first()
    if not deal:
        raise ValueError(f"Deal {deal_id} not found")

    properties = db.query(models.Property).filter(models.Property.deal_id == deal_id).all()
    line_items = db.query(models.FinancialLineItem).filter(
        models.FinancialLineItem.deal_id == deal_id
    ).all()

    # Calculate basic aggregates
    total_beds = sum(p.licensed_beds or 0 for p in properties)
    avg_occupancy = None
    occupancies = [p.current_occupancy for p in properties if p.current_occupancy]
    if occupancies:
        avg_occupancy = sum(occupancies) / len(occupancies)

    # Group line items
    revenue_items = [i for i in line_items if i.standard_account_code and i.standard_account_code.startswith("REV-")]
    expense_items = [i for i in line_items if i.standard_account_code and i.standard_account_code.startswith("EXP-")]
    fixed_items = [i for i in line_items if i.standard_account_code and i.standard_account_code.startswith("FIX-")]

    total_revenue = sum(i.amount for i in revenue_items)
    total_expenses = sum(i.amount for i in expense_items)
    total_fixed = sum(i.amount for i in fixed_items)

    # Calculate key metrics
    ebitdar = total_revenue - total_expenses
    rent = sum(i.amount for i in fixed_items if i.standard_account_code == "FIX-100")
    ebitda = ebitdar - rent
    depreciation = sum(i.amount for i in fixed_items if i.standard_account_code in ["FIX-200", "FIX-300"])
    interest = sum(i.amount for i in fixed_items if i.standard_account_code == "FIX-400")

    # Build analysis
    analysis = {
        "generated_at": datetime.utcnow().isoformat(),
        "deal_id": deal_id,
        "deal_name": deal.name,
        "summary": {
            "total_beds": total_beds,
            "occupancy": avg_occupancy,
            "total_revenue": total_revenue,
            "total_expenses": total_expenses,
            "ebitdar": ebitdar,
            "ebitdar_margin": round(ebitdar / total_revenue * 100, 1) if total_revenue else 0,
            "ebitda": ebitda,
            "ebitda_margin": round(ebitda / total_revenue * 100, 1) if total_revenue else 0,
            "rent": rent,
            "rent_coverage": round(ebitdar / rent, 2) if rent else None,
        },
        "benchmarks": {},
        "revenue_analysis": {},
        "expense_analysis": {},
        "ppd_metrics": {},
        "breakeven": {},
        "trends": {},
        "key_findings": [],
        "opportunities": [],
        "risks": []
    }

    # Benchmark analysis
    ebitdar_margin = analysis["summary"]["ebitdar_margin"] / 100
    analysis["benchmarks"]["ebitdar_margin"] = {
        "value": ebitdar_margin,
        "rating": get_benchmark_rating(ebitdar_margin, "margins", "ebitdar"),
        "benchmark_good": INDUSTRY_BENCHMARKS["margins"]["ebitdar"]["good"],
        "benchmark_excellent": INDUSTRY_BENCHMARKS["margins"]["ebitdar"]["excellent"],
    }

    if avg_occupancy:
        analysis["benchmarks"]["occupancy"] = {
            "value": avg_occupancy / 100,
            "rating": get_benchmark_rating(avg_occupancy / 100, "occupancy", "occupancy"),
            "benchmark_good": INDUSTRY_BENCHMARKS["occupancy"]["good"],
            "benchmark_excellent": INDUSTRY_BENCHMARKS["occupancy"]["excellent"],
        }

    # Revenue analysis
    analysis["revenue_analysis"] = analyze_revenue_composition(
        [{"standard_account_code": i.standard_account_code, "amount": i.amount} for i in revenue_items],
        total_revenue
    )

    # Expense analysis
    analysis["expense_analysis"] = analyze_expense_structure(
        [{"standard_account_code": i.standard_account_code, "amount": i.amount} for i in expense_items],
        total_revenue,
        total_expenses,
        total_beds
    )

    # PPD metrics
    if total_beds and avg_occupancy:
        patient_days = total_beds * 365 * (avg_occupancy / 100)
        analysis["ppd_metrics"] = calculate_per_patient_day_metrics(
            {
                "revenue": total_revenue,
                "expenses": total_expenses,
                "ebitdar": ebitdar,
                "nursing_expense": analysis["expense_analysis"]["by_category"].get("nursing", 0),
            },
            patient_days,
            total_beds,
            avg_occupancy
        )

    # Breakeven analysis
    if total_revenue and total_beds:
        # Estimate fixed vs variable (rough split)
        estimated_fixed = rent + depreciation + interest + (total_expenses * 0.3)  # 30% of OpEx assumed fixed
        estimated_variable = total_expenses * 0.7

        revenue_ppd = analysis["ppd_metrics"].get("revenue_ppd", 300)
        analysis["breakeven"] = calculate_breakeven_analysis(
            total_revenue,
            estimated_fixed,
            estimated_variable,
            total_beds,
            avg_occupancy or 80,
            revenue_ppd
        )

    # Trend analysis
    analysis["trends"] = analyze_trends(
        [{"standard_account_code": i.standard_account_code, "amount": i.amount, "period_label": i.period_label}
         for i in line_items],
        list(set(i.period_label for i in line_items if i.period_label))
    )

    # Generate key findings
    margin_rating = analysis["benchmarks"]["ebitdar_margin"]["rating"]
    if margin_rating == "poor":
        analysis["key_findings"].append({
            "type": "concern",
            "category": "profitability",
            "finding": f"EBITDAR margin of {ebitdar_margin*100:.1f}% is below industry benchmarks",
            "implication": "Facility may struggle to service debt or fund capital improvements",
            "action": "Deep dive into expense structure and revenue optimization opportunities"
        })
    elif margin_rating == "excellent":
        analysis["key_findings"].append({
            "type": "strength",
            "category": "profitability",
            "finding": f"Strong EBITDAR margin of {ebitdar_margin*100:.1f}%",
            "implication": "Healthy cash flow generation capacity",
            "action": "Validate sustainability of margins"
        })

    # Add opportunities from expense analysis
    for opp in analysis["expense_analysis"].get("opportunities", []):
        analysis["opportunities"].append(opp)

    # Add risks from revenue analysis
    for risk in analysis["revenue_analysis"].get("concentration_risk", []):
        analysis["risks"].append({
            "category": "revenue",
            "risk": risk["description"],
            "severity": risk["risk"]
        })

    return analysis


def store_financial_analysis(db: Session, deal_id: int, analysis: Dict) -> models.ExtractedField:
    """
    Store deep financial analysis as an extracted field.
    """
    existing = db.query(models.ExtractedField).filter(
        models.ExtractedField.deal_id == deal_id,
        models.ExtractedField.field_key == "deep_financial_analysis"
    ).first()

    if existing:
        existing.field_value = json.dumps(analysis)
        existing.updated_at = datetime.utcnow()
        db.commit()
        return existing

    field = models.ExtractedField(
        deal_id=deal_id,
        document_id=None,
        field_key="deep_financial_analysis",
        field_value=json.dumps(analysis),
        field_type="financial_analysis",
        confidence=1.0,
        extraction_method="deep_financial_analysis_module",
        created_by="system"
    )
    db.add(field)
    db.commit()
    db.refresh(field)
    return field
