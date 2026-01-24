"""
Property Research Module

Automated research on facility history, inspections, news, and public records.
"""
import re
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from . import models


# ============================================================================
# CMS CARE COMPARE DATA
# ============================================================================

def fetch_cms_nursing_home_data(provider_id: str = None, facility_name: str = None,
                                 state: str = None, city: str = None) -> Dict[str, Any]:
    """
    Fetch detailed nursing home data from CMS Care Compare.
    """
    result = {
        "found": False,
        "provider_info": None,
        "ratings": None,
        "staffing": None,
        "quality_measures": None,
        "health_inspections": None,
        "penalties": None
    }

    try:
        # CMS Nursing Home Compare API endpoints
        base_url = "https://data.cms.gov/provider-data/api/1/datastore/query"

        # Provider Info dataset
        provider_query = {
            "offset": 0,
            "limit": 5,
        }

        # Search by name and location
        search_response = requests.get(
            f"{base_url}/4pq5-n9py",  # NH Provider Info dataset
            params=provider_query,
            timeout=10
        )

        if search_response.ok:
            data = search_response.json()
            providers = data.get("results", [])

            # Find matching facility
            for prov in providers:
                prov_name = prov.get("provider_name", "").upper()
                prov_state = prov.get("provider_state", "").upper()
                prov_city = prov.get("provider_city", "").upper()

                name_match = facility_name and facility_name.upper() in prov_name
                state_match = not state or state.upper() == prov_state
                city_match = not city or city.upper() in prov_city

                if name_match and state_match and city_match:
                    result["found"] = True
                    result["provider_info"] = {
                        "provider_id": prov.get("federal_provider_number"),
                        "name": prov.get("provider_name"),
                        "address": prov.get("provider_address"),
                        "city": prov.get("provider_city"),
                        "state": prov.get("provider_state"),
                        "zip": prov.get("provider_zip_code"),
                        "phone": prov.get("provider_phone_number"),
                        "ownership_type": prov.get("ownership_type"),
                        "provider_type": prov.get("provider_type"),
                        "beds": prov.get("number_of_certified_beds"),
                        "residents": prov.get("average_number_of_residents_per_day"),
                        "in_hospital": prov.get("provider_resides_in_hospital"),
                        "continuing_care": prov.get("continuing_care_retirement_community"),
                        "special_focus": prov.get("special_focus_status"),
                        "abuse_icon": prov.get("abuse_icon"),
                    }

                    result["ratings"] = {
                        "overall": prov.get("overall_rating"),
                        "health_inspection": prov.get("health_inspection_rating"),
                        "staffing": prov.get("staffing_rating"),
                        "quality": prov.get("qm_rating"),
                        "long_stay_quality": prov.get("long_stay_qm_rating"),
                        "short_stay_quality": prov.get("short_stay_qm_rating"),
                    }

                    result["staffing"] = {
                        "rn_hours_per_resident_day": prov.get("reported_rn_staffing_hours_per_resident_per_day"),
                        "lpn_hours_per_resident_day": prov.get("reported_lpn_staffing_hours_per_resident_per_day"),
                        "cna_hours_per_resident_day": prov.get("reported_cna_staffing_hours_per_resident_per_day"),
                        "total_hours_per_resident_day": prov.get("reported_total_nurse_staffing_hours_per_resident_per_day"),
                        "physical_therapy_hours": prov.get("reported_physical_therapist_staffing_hours_per_resident_per_day"),
                    }

                    result["health_inspections"] = {
                        "total_deficiencies": prov.get("total_number_of_health_deficiencies"),
                        "fire_safety_deficiencies": prov.get("total_number_of_fire_safety_deficiencies"),
                        "complaint_deficiencies": prov.get("number_of_facility_reported_incidents"),
                        "inspection_date": prov.get("date_of_most_recent_health_inspection"),
                    }

                    result["penalties"] = {
                        "fines_total": prov.get("total_amount_of_fines_in_dollars"),
                        "payment_denials": prov.get("number_of_payment_denials"),
                        "fine_count": prov.get("total_number_of_penalties"),
                    }

                    break

    except Exception as e:
        result["error"] = str(e)

    return result


def get_facility_inspection_history(provider_id: str) -> List[Dict]:
    """
    Get detailed inspection/survey history for a facility.
    """
    inspections = []

    try:
        # CMS Health Deficiencies dataset
        response = requests.get(
            "https://data.cms.gov/provider-data/api/1/datastore/query/r5ix-sfxw",
            params={"offset": 0, "limit": 50},
            timeout=10
        )

        if response.ok:
            data = response.json()
            for deficiency in data.get("results", []):
                if deficiency.get("federal_provider_number") == provider_id:
                    inspections.append({
                        "survey_date": deficiency.get("survey_date"),
                        "deficiency_tag": deficiency.get("deficiency_tag_number"),
                        "deficiency_description": deficiency.get("deficiency_description"),
                        "scope_severity": deficiency.get("scope_severity_code"),
                        "category": deficiency.get("deficiency_category"),
                        "correction_date": deficiency.get("correction_date"),
                    })
    except Exception as e:
        pass

    return inspections


def get_facility_complaints(provider_id: str) -> List[Dict]:
    """
    Get complaint investigation history.
    """
    complaints = []
    # Would integrate with state-specific complaint databases
    return complaints


# ============================================================================
# NEWS AND PUBLIC RECORDS SEARCH
# ============================================================================

def search_facility_news(facility_name: str, city: str = None, state: str = None) -> List[Dict]:
    """
    Search for news articles about a facility.
    Note: In production, would integrate with news APIs.
    """
    search_results = []

    # Build search query
    query_parts = [f'"{facility_name}"']
    if city:
        query_parts.append(city)
    if state:
        query_parts.append(state)
    query_parts.extend(["nursing home", "skilled nursing"])

    # This would integrate with Google News API, NewsAPI, or similar
    # For now, return structure for future implementation
    return {
        "search_query": " ".join(query_parts),
        "results": [],
        "note": "News search requires API integration (NewsAPI, Google News, etc.)"
    }


def search_legal_records(facility_name: str, state: str = None) -> List[Dict]:
    """
    Search for legal/court records involving the facility.
    Note: Would integrate with PACER, state court records, etc.
    """
    return {
        "search_query": facility_name,
        "results": [],
        "note": "Legal records search requires court database integration"
    }


def search_ownership_history(facility_name: str, state: str = None) -> Dict[str, Any]:
    """
    Research ownership history and changes.
    """
    # Would integrate with state licensure databases, ProPublica's Nursing Home Inspect
    return {
        "current_owner": None,
        "ownership_changes": [],
        "note": "Ownership history requires state licensure database integration"
    }


# ============================================================================
# STATE HEALTH DEPARTMENT DATA
# ============================================================================

def get_state_survey_data(facility_name: str, state: str) -> Dict[str, Any]:
    """
    Get state-specific survey and inspection data.
    Each state has different data systems.
    """
    state_systems = {
        "TX": {
            "agency": "Texas HHS",
            "search_url": "https://www.hhs.texas.gov/providers/long-term-care-providers",
            "data_available": ["Inspection reports", "Enforcement actions", "Staffing data"]
        },
        "FL": {
            "agency": "AHCA",
            "search_url": "https://www.floridahealthfinder.gov/",
            "data_available": ["Inspection reports", "Quality measures", "Complaints"]
        },
        "CA": {
            "agency": "CDPH",
            "search_url": "https://www.cdph.ca.gov/Programs/CHCQ/LCP/Pages/LongTermCareHealthFacilities.aspx",
            "data_available": ["Citations", "Penalties", "Class AA/A/B violations"]
        },
        "NY": {
            "agency": "DOH",
            "search_url": "https://profiles.health.ny.gov/nursing_home/",
            "data_available": ["Inspection reports", "Staffing", "Quality indicators"]
        },
    }

    return state_systems.get(state.upper(), {
        "agency": "State Health Department",
        "search_url": None,
        "data_available": ["Varies by state"]
    })


# ============================================================================
# COMPREHENSIVE PROPERTY RESEARCH
# ============================================================================

def research_property(
    db: Session,
    property_id: int
) -> Dict[str, Any]:
    """
    Conduct comprehensive research on a single property.
    """
    prop = db.query(models.Property).filter(models.Property.id == property_id).first()
    if not prop:
        raise ValueError(f"Property {property_id} not found")

    research = {
        "property_id": property_id,
        "property_name": prop.name,
        "address": prop.address,
        "city": prop.city,
        "state": prop.state,
        "researched_at": datetime.utcnow().isoformat(),
        "cms_data": {},
        "inspection_history": [],
        "state_data": {},
        "news_search": {},
        "ownership_history": {},
        "risk_indicators": []
    }

    # 1. CMS Care Compare data
    cms_data = fetch_cms_nursing_home_data(
        facility_name=prop.name,
        state=prop.state,
        city=prop.city
    )
    research["cms_data"] = cms_data

    # Extract risk indicators from CMS data
    if cms_data.get("found"):
        provider_info = cms_data.get("provider_info", {})
        ratings = cms_data.get("ratings", {})
        penalties = cms_data.get("penalties", {})
        inspections = cms_data.get("health_inspections", {})

        # Check for Special Focus Facility status
        if provider_info.get("special_focus"):
            research["risk_indicators"].append({
                "type": "regulatory",
                "severity": "high",
                "indicator": "Special Focus Facility",
                "description": "CMS has designated this facility for enhanced oversight due to persistent quality issues"
            })

        # Check for abuse icon
        if provider_info.get("abuse_icon"):
            research["risk_indicators"].append({
                "type": "quality",
                "severity": "high",
                "indicator": "Abuse Citation",
                "description": "Facility has received citation for abuse, neglect, or exploitation"
            })

        # Check star ratings
        overall_rating = ratings.get("overall")
        if overall_rating and int(overall_rating) <= 2:
            research["risk_indicators"].append({
                "type": "quality",
                "severity": "high" if int(overall_rating) == 1 else "medium",
                "indicator": f"{overall_rating}-Star Overall Rating",
                "description": "Below average CMS quality rating indicates quality concerns"
            })

        # Check for significant penalties
        fines = penalties.get("fines_total")
        if fines and float(fines) > 50000:
            research["risk_indicators"].append({
                "type": "regulatory",
                "severity": "high" if float(fines) > 100000 else "medium",
                "indicator": f"Significant Fines: ${float(fines):,.0f}",
                "description": "Facility has incurred substantial CMS penalties"
            })

        # Check deficiency count
        deficiencies = inspections.get("total_deficiencies")
        if deficiencies and int(deficiencies) > 15:
            research["risk_indicators"].append({
                "type": "regulatory",
                "severity": "medium",
                "indicator": f"{deficiencies} Health Deficiencies",
                "description": "Above average number of health deficiencies on most recent survey"
            })

        # Get detailed inspection history
        if provider_info.get("provider_id"):
            research["inspection_history"] = get_facility_inspection_history(
                provider_info["provider_id"]
            )

    # 2. State-specific data
    if prop.state:
        research["state_data"] = get_state_survey_data(prop.name, prop.state)

    # 3. News search
    research["news_search"] = search_facility_news(prop.name, prop.city, prop.state)

    # 4. Ownership history
    research["ownership_history"] = search_ownership_history(prop.name, prop.state)

    return research


def research_deal_properties(
    db: Session,
    deal_id: int
) -> Dict[str, Any]:
    """
    Conduct comprehensive research on all properties in a deal.
    """
    deal = db.query(models.Deal).filter(models.Deal.id == deal_id).first()
    if not deal:
        raise ValueError(f"Deal {deal_id} not found")

    properties = db.query(models.Property).filter(models.Property.deal_id == deal_id).all()

    research = {
        "deal_id": deal_id,
        "deal_name": deal.name,
        "researched_at": datetime.utcnow().isoformat(),
        "property_count": len(properties),
        "properties": [],
        "aggregate_risk_indicators": [],
        "summary": {}
    }

    total_deficiencies = 0
    total_fines = 0
    ratings = []
    high_risk_count = 0

    for prop in properties:
        prop_research = research_property(db, prop.id)
        research["properties"].append(prop_research)

        # Aggregate data
        cms = prop_research.get("cms_data", {})
        if cms.get("found"):
            ratings_data = cms.get("ratings", {})
            if ratings_data.get("overall"):
                ratings.append(int(ratings_data["overall"]))

            inspections = cms.get("health_inspections", {})
            if inspections.get("total_deficiencies"):
                total_deficiencies += int(inspections["total_deficiencies"])

            penalties = cms.get("penalties", {})
            if penalties.get("fines_total"):
                total_fines += float(penalties["fines_total"])

        # Count high-risk properties
        high_risk = any(r["severity"] == "high" for r in prop_research.get("risk_indicators", []))
        if high_risk:
            high_risk_count += 1

    # Build summary
    research["summary"] = {
        "properties_found_in_cms": len([p for p in research["properties"] if p["cms_data"].get("found")]),
        "average_star_rating": round(sum(ratings) / len(ratings), 1) if ratings else None,
        "total_deficiencies": total_deficiencies,
        "total_fines": total_fines,
        "high_risk_properties": high_risk_count,
        "properties_below_3_star": len([r for r in ratings if r < 3])
    }

    # Aggregate risk indicators
    if high_risk_count > 0:
        research["aggregate_risk_indicators"].append({
            "type": "portfolio",
            "severity": "high" if high_risk_count > len(properties) / 2 else "medium",
            "indicator": f"{high_risk_count} High-Risk Properties",
            "description": f"{high_risk_count} of {len(properties)} properties have high-severity risk indicators"
        })

    if total_fines > 100000:
        research["aggregate_risk_indicators"].append({
            "type": "regulatory",
            "severity": "high",
            "indicator": f"Portfolio Fines: ${total_fines:,.0f}",
            "description": "Significant aggregate penalties across portfolio"
        })

    avg_rating = research["summary"].get("average_star_rating")
    if avg_rating and avg_rating < 3:
        research["aggregate_risk_indicators"].append({
            "type": "quality",
            "severity": "high" if avg_rating < 2 else "medium",
            "indicator": f"Average Rating: {avg_rating} Stars",
            "description": "Portfolio average star rating is below 3 stars"
        })

    return research


def store_property_research(db: Session, deal_id: int, research: Dict) -> models.ExtractedField:
    """
    Store property research as an extracted field.
    """
    import json

    existing = db.query(models.ExtractedField).filter(
        models.ExtractedField.deal_id == deal_id,
        models.ExtractedField.field_key == "property_research"
    ).first()

    if existing:
        existing.field_value = json.dumps(research)
        existing.updated_at = datetime.utcnow()
        db.commit()
        return existing

    field = models.ExtractedField(
        deal_id=deal_id,
        document_id=None,
        field_key="property_research",
        field_value=json.dumps(research),
        field_type="property_research",
        confidence=1.0,
        extraction_method="property_research_module",
        created_by="system"
    )
    db.add(field)
    db.commit()
    db.refresh(field)
    return field
