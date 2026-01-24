"""
Market Analysis Module

Comprehensive market analysis including regulatory environment,
demographics, reimbursement, and competitive landscape.
"""
import re
import requests
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from . import models


# ============================================================================
# CMS DATA INTEGRATION
# ============================================================================

CMS_PROVIDER_API = "https://data.cms.gov/provider-data/api/1/datastore/query"

def search_cms_provider(facility_name: str, city: str = None, state: str = None) -> Optional[Dict]:
    """
    Search CMS Provider Data for a nursing home facility.
    Returns facility data including ratings, staffing, quality measures.
    """
    try:
        # CMS Nursing Home Compare dataset ID
        params = {
            "limit": 10,
            "offset": 0,
        }

        # Build search conditions
        conditions = []
        if facility_name:
            # Search by name (partial match)
            conditions.append({
                "resource": "provider_name",
                "expression": {
                    "operator": "LIKE",
                    "value": f"%{facility_name.upper()}%"
                }
            })
        if state:
            conditions.append({
                "resource": "state",
                "expression": {
                    "operator": "=",
                    "value": state.upper()
                }
            })

        # Try the CMS Nursing Home Compare API
        response = requests.get(
            "https://data.cms.gov/provider-data/api/1/datastore/query/4pq5-n9py",
            params={"limit": 10},
            headers={"Accept": "application/json"},
            timeout=10
        )

        if response.ok:
            data = response.json()
            results = data.get("results", [])

            # Find best match
            for result in results:
                name = result.get("provider_name", "").upper()
                prov_state = result.get("state", "").upper()

                if facility_name.upper() in name:
                    if state and prov_state != state.upper():
                        continue
                    return result

        return None
    except Exception as e:
        print(f"CMS API error: {e}")
        return None


def get_state_medicaid_rates(state: str) -> Dict[str, Any]:
    """
    Get Medicaid reimbursement information for a state.
    Returns rate structure and recent changes.
    """
    # State Medicaid rate information (simplified - in production would pull from APIs)
    state_info = {
        "TX": {
            "avg_daily_rate": 185.50,
            "rate_methodology": "Resource Utilization Group (RUG-IV)",
            "recent_changes": "3.2% rate increase effective Sept 2024",
            "quality_incentive": True,
            "bed_hold_days": 15
        },
        "FL": {
            "avg_daily_rate": 215.75,
            "rate_methodology": "Prospective Payment System",
            "recent_changes": "Legislature approved 2.8% increase for FY2025",
            "quality_incentive": True,
            "bed_hold_days": 14
        },
        "CA": {
            "avg_daily_rate": 265.00,
            "rate_methodology": "Facility-Specific Rate",
            "recent_changes": "AB 1629 wage pass-through adjustments ongoing",
            "quality_incentive": True,
            "bed_hold_days": 7
        },
        "NY": {
            "avg_daily_rate": 285.00,
            "rate_methodology": "Case Mix Adjusted",
            "recent_changes": "1.5% trend factor applied",
            "quality_incentive": True,
            "bed_hold_days": 14
        },
        "PA": {
            "avg_daily_rate": 225.00,
            "rate_methodology": "Case Mix Payment",
            "recent_changes": "County-based rate adjustments",
            "quality_incentive": False,
            "bed_hold_days": 15
        },
    }

    return state_info.get(state.upper(), {
        "avg_daily_rate": None,
        "rate_methodology": "Varies by state",
        "recent_changes": "Contact state Medicaid office",
        "quality_incentive": None,
        "bed_hold_days": None
    })


def get_medicare_rates() -> Dict[str, Any]:
    """
    Get current Medicare SNF PPS rate information.
    """
    return {
        "payment_system": "Patient Driven Payment Model (PDPM)",
        "effective_date": "October 1, 2024",
        "market_basket_update": "4.0%",
        "productivity_adjustment": "-0.3%",
        "net_increase": "3.7%",
        "urban_base_rate": 605.82,
        "rural_base_rate": 589.24,
        "pdpm_components": [
            "Physical Therapy",
            "Occupational Therapy",
            "Speech-Language Pathology",
            "Nursing",
            "Non-Therapy Ancillary"
        ],
        "value_based_purchasing": {
            "program": "SNF VBP",
            "measure": "Hospital Readmission",
            "withhold_percentage": 2.0,
            "performance_period": "FY2023"
        }
    }


# ============================================================================
# DEMOGRAPHIC ANALYSIS
# ============================================================================

def get_demographic_data(city: str, state: str, county: str = None) -> Dict[str, Any]:
    """
    Get demographic data for market analysis.
    In production, would integrate with Census API.
    """
    # Simplified demographic profiles by state (would use Census API in production)
    return {
        "population_65_plus_pct": None,  # Would pull from Census
        "population_85_plus_pct": None,
        "population_growth_5yr": None,
        "median_household_income": None,
        "poverty_rate_65_plus": None,
        "data_source": "US Census Bureau ACS",
        "notes": "Detailed demographic data requires Census API integration"
    }


def estimate_market_demand(beds: int, state: str, occupancy: float = None) -> Dict[str, Any]:
    """
    Estimate market demand metrics.
    """
    # National benchmarks
    national_avg_occupancy = 75.8  # Post-COVID average
    state_benchmarks = {
        "TX": 70.5,
        "FL": 82.3,
        "CA": 78.1,
        "NY": 85.2,
        "PA": 81.5,
        "OH": 76.8,
        "IL": 74.2,
    }

    state_benchmark = state_benchmarks.get(state.upper(), national_avg_occupancy)
    current_occ = occupancy or state_benchmark

    return {
        "national_avg_occupancy": national_avg_occupancy,
        "state_avg_occupancy": state_benchmark,
        "facility_occupancy": current_occ,
        "occupancy_vs_state": round(current_occ - state_benchmark, 1),
        "occupancy_vs_national": round(current_occ - national_avg_occupancy, 1),
        "stabilized_occupancy_target": min(92, state_benchmark + 10),
        "beds_at_stabilization": round(beds * min(0.92, (state_benchmark + 10) / 100)),
    }


# ============================================================================
# REGULATORY ENVIRONMENT
# ============================================================================

def get_regulatory_environment(state: str) -> Dict[str, Any]:
    """
    Get regulatory environment information for a state.
    """
    # State regulatory profiles
    profiles = {
        "TX": {
            "regulatory_agency": "Texas Health and Human Services Commission",
            "licensure_requirements": "State license required, CON not required",
            "certificate_of_need": False,
            "staffing_requirements": {
                "rn_hours_minimum": 0.0,  # No state minimum
                "total_nursing_minimum": 2.0,  # per resident day
                "follows_federal": True
            },
            "survey_frequency": "Annual + complaint investigations",
            "recent_regulatory_changes": [
                "SB 796 - Staffing disclosure requirements (2023)",
                "Infection control standards updated post-COVID"
            ],
            "enforcement_trends": "Moderate - focused on infection control"
        },
        "FL": {
            "regulatory_agency": "Florida Agency for Health Care Administration",
            "licensure_requirements": "State license required, CON required for new beds",
            "certificate_of_need": True,
            "staffing_requirements": {
                "rn_hours_minimum": 0.5,
                "total_nursing_minimum": 3.6,
                "follows_federal": False
            },
            "survey_frequency": "Every 15 months + complaints",
            "recent_regulatory_changes": [
                "Emergency preparedness requirements enhanced",
                "Minimum staffing ratios increased"
            ],
            "enforcement_trends": "Strict - active enforcement"
        },
        "CA": {
            "regulatory_agency": "California Department of Public Health",
            "licensure_requirements": "State license required, CON not required",
            "certificate_of_need": False,
            "staffing_requirements": {
                "rn_hours_minimum": 0.5,
                "total_nursing_minimum": 3.5,
                "follows_federal": False
            },
            "survey_frequency": "Annual + complaints",
            "recent_regulatory_changes": [
                "AB 1502 - Ownership disclosure requirements",
                "Staffing ratio enforcement increased"
            ],
            "enforcement_trends": "Very strict - highest in nation"
        },
        "NY": {
            "regulatory_agency": "New York State Department of Health",
            "licensure_requirements": "State license + CON required",
            "certificate_of_need": True,
            "staffing_requirements": {
                "rn_hours_minimum": 0.0,
                "total_nursing_minimum": 3.5,
                "follows_federal": False
            },
            "survey_frequency": "Annual + focused surveys",
            "recent_regulatory_changes": [
                "Nursing home staffing law passed 2021",
                "70% revenue to direct care requirement"
            ],
            "enforcement_trends": "Strict - increasing oversight"
        },
    }

    return profiles.get(state.upper(), {
        "regulatory_agency": "State Health Department",
        "licensure_requirements": "Varies by state",
        "certificate_of_need": None,
        "staffing_requirements": {
            "follows_federal": True
        },
        "survey_frequency": "Typically annual",
        "recent_regulatory_changes": [],
        "enforcement_trends": "Contact state for details"
    })


# ============================================================================
# COMPETITIVE ANALYSIS
# ============================================================================

def analyze_competitive_landscape(city: str, state: str, beds: int) -> Dict[str, Any]:
    """
    Analyze competitive landscape.
    In production, would search CMS data for nearby facilities.
    """
    return {
        "analysis_type": "Local Market",
        "search_radius_miles": 10,
        "competitor_count": None,  # Would search CMS data
        "total_market_beds": None,
        "market_occupancy": None,
        "facility_market_share": None,
        "competitive_positioning": {
            "factors": [
                "Star ratings vs competitors",
                "Specialty services offered",
                "Payor mix comparison",
                "Staffing levels"
            ],
            "notes": "Detailed competitive analysis requires CMS Provider Data API integration"
        }
    }


# ============================================================================
# MAIN MARKET ANALYSIS FUNCTION
# ============================================================================

def generate_market_analysis(
    db: Session,
    deal_id: int
) -> Dict[str, Any]:
    """
    Generate comprehensive market analysis for a deal.
    """
    deal = db.query(models.Deal).filter(models.Deal.id == deal_id).first()
    if not deal:
        raise ValueError(f"Deal {deal_id} not found")

    properties = db.query(models.Property).filter(models.Property.deal_id == deal_id).all()

    # Aggregate property data
    states = list(set(p.state for p in properties if p.state))
    cities = list(set(p.city for p in properties if p.city))
    total_beds = sum(p.licensed_beds or 0 for p in properties)
    avg_occupancy = None
    occupancies = [p.current_occupancy for p in properties if p.current_occupancy]
    if occupancies:
        avg_occupancy = sum(occupancies) / len(occupancies)

    # Primary state for analysis (if multi-state, use first)
    primary_state = states[0] if states else None
    primary_city = cities[0] if cities else None

    analysis = {
        "generated_at": datetime.utcnow().isoformat(),
        "deal_id": deal_id,
        "deal_name": deal.name,
        "portfolio_summary": {
            "property_count": len(properties),
            "total_beds": total_beds,
            "states": states,
            "cities": cities,
            "avg_occupancy": avg_occupancy
        },
        "regulatory_environment": {},
        "reimbursement_analysis": {},
        "demographic_analysis": {},
        "market_demand": {},
        "competitive_landscape": {},
        "facility_cms_data": []
    }

    # Get regulatory environment
    if primary_state:
        analysis["regulatory_environment"] = get_regulatory_environment(primary_state)

    # Get reimbursement data
    if primary_state:
        analysis["reimbursement_analysis"] = {
            "medicaid": get_state_medicaid_rates(primary_state),
            "medicare": get_medicare_rates()
        }

    # Get demographic data
    if primary_city and primary_state:
        analysis["demographic_analysis"] = get_demographic_data(primary_city, primary_state)

    # Get market demand metrics
    if total_beds and primary_state:
        analysis["market_demand"] = estimate_market_demand(total_beds, primary_state, avg_occupancy)

    # Get competitive landscape
    if primary_city and primary_state:
        analysis["competitive_landscape"] = analyze_competitive_landscape(
            primary_city, primary_state, total_beds
        )

    # Look up each facility in CMS data
    for prop in properties:
        cms_data = search_cms_provider(prop.name, prop.city, prop.state)
        if cms_data:
            analysis["facility_cms_data"].append({
                "property_id": prop.id,
                "property_name": prop.name,
                "cms_data": cms_data
            })

    return analysis


def store_market_analysis(db: Session, deal_id: int, analysis: Dict) -> models.ExtractedField:
    """
    Store market analysis as an extracted field for the deal.
    """
    # Check if exists
    existing = db.query(models.ExtractedField).filter(
        models.ExtractedField.deal_id == deal_id,
        models.ExtractedField.field_key == "market_analysis"
    ).first()

    import json

    if existing:
        existing.field_value = json.dumps(analysis)
        existing.updated_at = datetime.utcnow()
        db.commit()
        return existing

    field = models.ExtractedField(
        deal_id=deal_id,
        document_id=None,
        field_key="market_analysis",
        field_value=json.dumps(analysis),
        field_type="market_analysis",
        confidence=1.0,
        extraction_method="market_analysis_module",
        created_by="system"
    )
    db.add(field)
    db.commit()
    db.refresh(field)
    return field
