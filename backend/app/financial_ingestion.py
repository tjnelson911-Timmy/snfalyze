"""
Financial Document Ingestion Module

Parses financial statements and maps to standard chart of accounts.
"""
import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session

from . import models, schemas, crud


# ============================================================================
# ACCOUNT MAPPING PATTERNS
# ============================================================================

# Patterns to identify account categories from seller's descriptions
ACCOUNT_CATEGORY_PATTERNS = {
    # Revenue patterns
    "revenue": {
        "patient_revenue": [
            r"(?:medicaid|title\s*19|state)\s*(?:revenue|income|receipts)",
            r"(?:medicare|title\s*18)\s*(?:part\s*[ab])?\s*(?:revenue|income)",
            r"(?:managed\s*care|hmo|mco)\s*(?:revenue|income)",
            r"(?:private\s*pay|private)\s*(?:revenue|income)",
            r"(?:va|veterans?|government)\s*(?:revenue|income)",
            r"(?:patient|resident)\s*(?:revenue|income|services)",
            r"room\s*(?:and|&)\s*board",
        ],
        "ancillary": [
            r"(?:therapy|rehab|pt|ot|st)\s*(?:revenue|income|services)",
            r"(?:pharmacy|drug|rx)\s*(?:revenue|income)",
            r"(?:lab|laboratory)\s*(?:revenue|income)",
            r"(?:hospice)\s*(?:revenue|income)",
            r"(?:ancillary|other)\s*(?:revenue|income|services)",
        ],
    },
    # Labor expense patterns
    "labor": {
        "nursing": [
            r"(?:nursing|nurse|rn|lpn|lvn|cna)\s*(?:wages?|salaries|payroll|labor)",
            r"(?:direct\s*care|patient\s*care)\s*(?:wages?|salaries)",
            r"(?:agency|contract|temp)\s*(?:nursing|nurse)",
            r"(?:nursing|nurse)\s*(?:benefits?|insurance)",
        ],
        "therapy": [
            r"(?:therapy|rehab|pt|ot|st)\s*(?:wages?|salaries|payroll|labor)",
            r"(?:therapy|rehab)\s*(?:contract|contractor)",
        ],
        "dietary": [
            r"(?:dietary|food\s*service|kitchen|culinary)\s*(?:wages?|salaries|labor)",
        ],
        "housekeeping": [
            r"(?:housekeeping|laundry|environmental)\s*(?:wages?|salaries|labor)",
        ],
        "maintenance": [
            r"(?:maintenance|plant|facilities|building)\s*(?:wages?|salaries|labor)",
        ],
        "admin": [
            r"(?:admin|administrative|office|clerical)\s*(?:wages?|salaries|labor)",
            r"(?:management|executive)\s*(?:wages?|salaries)",
            r"(?:hr|human\s*resources)\s*(?:wages?|salaries)",
        ],
        "benefits": [
            r"(?:employee|payroll)\s*(?:benefits?|taxes?)",
            r"(?:fica|futa|suta|workers?\s*comp)",
            r"(?:health|medical|dental)\s*(?:insurance|benefits)",
            r"(?:401k|retirement|pension)",
        ],
    },
    # Non-labor expense patterns
    "expense": {
        "supplies": [
            r"(?:medical|nursing)\s*(?:supplies|equipment)",
            r"(?:dietary|food)\s*(?:supplies|cost)",
            r"(?:housekeeping|laundry)\s*(?:supplies)",
            r"(?:pharmacy|drug|rx)\s*(?:expense|cost|supplies)",
        ],
        "occupancy": [
            r"(?:utilities?|electric|gas|water|sewer)",
            r"(?:property|real\s*estate)\s*(?:taxes?)",
            r"(?:property|building)\s*(?:insurance)",
            r"(?:repairs?|maintenance)\s*(?:expense|cost)",
            r"(?:rent|lease)\s*(?:expense)?",
        ],
        "professional": [
            r"(?:legal|attorney)\s*(?:fees?|expense)",
            r"(?:accounting|audit)\s*(?:fees?|expense)",
            r"(?:consulting)\s*(?:fees?|expense)",
            r"(?:professional)\s*(?:fees?|services)",
        ],
        "insurance": [
            r"(?:professional|malpractice|liability)\s*(?:insurance)",
            r"(?:general)\s*(?:insurance|liability)",
        ],
        "other": [
            r"(?:marketing|advertising)",
            r"(?:travel|entertainment)",
            r"(?:office)\s*(?:supplies|expense)",
            r"(?:it|technology|computer)",
            r"(?:bad\s*debt|uncollectible)",
            r"(?:management)\s*(?:fee)",
            r"(?:corporate|overhead)\s*(?:allocation|expense)",
        ],
    },
    # Fixed charges
    "fixed": {
        "rent": [
            r"(?:rent|lease)\s*(?:expense|payment)",
            r"(?:building|facility)\s*(?:rent|lease)",
        ],
        "depreciation": [
            r"depreciation",
            r"amortization",
        ],
        "interest": [
            r"(?:interest)\s*(?:expense|payment)",
            r"(?:debt)\s*(?:service|interest)",
        ],
    },
}


def match_account_to_standard(
    account_name: str,
    db: Session
) -> Tuple[Optional[str], float]:
    """
    Match a seller's account name to a standard account code.
    Returns (standard_account_code, confidence).
    """
    account_lower = account_name.lower()
    best_match = None
    best_confidence = 0.0

    # Direct keyword matching
    for category, subcategories in ACCOUNT_CATEGORY_PATTERNS.items():
        for subcategory, patterns in subcategories.items():
            for pattern in patterns:
                if re.search(pattern, account_lower, re.IGNORECASE):
                    # Find matching standard account
                    standard = find_standard_account(db, category, subcategory)
                    if standard:
                        confidence = 0.7  # Base confidence for pattern match
                        if best_confidence < confidence:
                            best_match = standard.code
                            best_confidence = confidence

    return best_match, best_confidence


def find_standard_account(
    db: Session,
    category: str,
    subcategory: str
) -> Optional[models.StandardAccount]:
    """
    Find standard account by category and subcategory hints.
    """
    # Map category/subcategory to standard account codes
    mapping = {
        ("revenue", "patient_revenue"): "REV-100",  # Start of patient revenue
        ("revenue", "ancillary"): "REV-200",
        ("labor", "nursing"): "EXP-100",
        ("labor", "therapy"): "EXP-200",
        ("labor", "dietary"): "EXP-300",
        ("labor", "housekeeping"): "EXP-310",
        ("labor", "maintenance"): "EXP-320",
        ("labor", "admin"): "EXP-350",
        ("labor", "benefits"): "EXP-360",
        ("expense", "supplies"): "EXP-400",
        ("expense", "occupancy"): "EXP-500",
        ("expense", "professional"): "EXP-700",
        ("expense", "insurance"): "EXP-600",
        ("expense", "other"): "EXP-850",
        ("fixed", "rent"): "FIX-100",
        ("fixed", "depreciation"): "FIX-200",
        ("fixed", "interest"): "FIX-400",
    }

    code = mapping.get((category, subcategory))
    if code:
        return db.query(models.StandardAccount).filter(
            models.StandardAccount.code == code
        ).first()

    return None


def suggest_coa_mappings(
    db: Session,
    deal_id: int,
    document_id: int,
    seller_accounts: List[Dict[str, Any]]
) -> List[models.COAMapping]:
    """
    Create suggested COA mappings for a list of seller accounts.
    """
    mappings = []

    for account in seller_accounts:
        account_name = account.get("name", "")
        account_number = account.get("number")

        # Try to match to standard
        standard_code, confidence = match_account_to_standard(account_name, db)

        mapping = models.COAMapping(
            deal_id=deal_id,
            document_id=document_id,
            seller_account_name=account_name,
            seller_account_number=account_number,
            standard_account_code=standard_code,
            confidence=confidence,
            mapping_status="suggested" if standard_code else "unmapped",
            suggested_by="system"
        )
        db.add(mapping)
        mappings.append(mapping)

    db.commit()
    return mappings


def parse_financial_table(
    table_data: Dict[str, Any],
    deal_id: int,
    document_id: int,
    db: Session
) -> Tuple[List[Dict], List[Dict]]:
    """
    Parse a financial table and extract line items.
    Returns (line_items, seller_accounts).
    """
    line_items = []
    seller_accounts = []

    headers = table_data.get("headers", [])
    rows = table_data.get("rows", [])

    if not headers or not rows:
        return [], []

    # Detect account column and period columns
    account_col = None
    period_cols = []

    for i, header in enumerate(headers):
        header_lower = header.lower() if header else ""

        # Account name column
        if any(kw in header_lower for kw in ["account", "description", "line item", "category"]):
            account_col = header
        # Period columns (dates, months, years)
        elif re.search(r"\d{4}|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|q[1-4]|ytd|ttm", header_lower):
            period_cols.append(header)

    # If no account column found, assume first column
    if account_col is None and headers:
        account_col = headers[0]

    # If no period columns found, look for numeric columns
    if not period_cols and len(headers) > 1:
        period_cols = headers[1:]

    # Process rows
    for row in rows:
        account_name = row.get(account_col, "")
        if not account_name or not isinstance(account_name, str):
            continue

        # Skip total/summary rows
        if any(kw in account_name.lower() for kw in ["total", "subtotal", "net income", "gross profit"]):
            continue

        # Track seller account
        seller_accounts.append({
            "name": account_name.strip(),
            "number": None  # Could extract if available
        })

        # Extract amounts for each period
        for period_col in period_cols:
            value = row.get(period_col)
            if value is None:
                continue

            # Parse numeric value
            amount = parse_currency_value(value)
            if amount is None:
                continue

            line_items.append({
                "account_name": account_name.strip(),
                "period_label": period_col,
                "amount": amount,
                "period_type": detect_period_type(period_col)
            })

    return line_items, seller_accounts


def parse_currency_value(value: Any) -> Optional[float]:
    """
    Parse a currency value from various formats.
    """
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):
        # Remove currency symbols, commas, spaces
        cleaned = re.sub(r'[$,\s]', '', value)

        # Handle parentheses for negatives
        is_negative = '(' in value and ')' in value
        cleaned = cleaned.replace('(', '').replace(')', '')

        # Handle trailing minus
        if cleaned.endswith('-'):
            is_negative = True
            cleaned = cleaned[:-1]

        try:
            amount = float(cleaned)
            return -amount if is_negative else amount
        except ValueError:
            return None

    return None


def detect_period_type(period_label: str) -> str:
    """
    Detect the period type from a column label.
    """
    label_lower = period_label.lower()

    if any(kw in label_lower for kw in ["ytd", "year to date"]):
        return "ytd"
    elif any(kw in label_lower for kw in ["ttm", "trailing", "t-12", "t12"]):
        return "ttm"
    elif re.search(r"q[1-4]", label_lower):
        return "quarterly"
    elif any(kw in label_lower for kw in ["annual", "year", "fy"]):
        return "annual"
    elif re.search(r"jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec", label_lower):
        return "monthly"
    else:
        return "unknown"


def ingest_financial_document(
    db: Session,
    document_id: int
) -> Dict[str, Any]:
    """
    Main function to ingest a financial document.
    Parses tables, creates mappings, and stores line items.
    """
    doc = db.query(models.Document).filter(models.Document.id == document_id).first()
    if not doc:
        raise ValueError(f"Document {document_id} not found")

    # Get parsed artifacts (tables)
    artifacts = db.query(models.ParsedArtifact).filter(
        models.ParsedArtifact.document_id == document_id,
        models.ParsedArtifact.artifact_type == "table"
    ).all()

    all_line_items = []
    all_seller_accounts = []

    for artifact in artifacts:
        if not artifact.content_json:
            continue

        line_items, seller_accounts = parse_financial_table(
            artifact.content_json,
            doc.deal_id,
            document_id,
            db
        )

        all_line_items.extend(line_items)
        all_seller_accounts.extend(seller_accounts)

    # Create COA mapping suggestions
    unique_accounts = {a["name"]: a for a in all_seller_accounts}.values()
    mappings = suggest_coa_mappings(db, doc.deal_id, document_id, list(unique_accounts))

    # Create mapping lookup
    mapping_lookup = {m.seller_account_name: m for m in mappings}

    # Store line items with mapped accounts
    stored_items = []
    for item in all_line_items:
        mapping = mapping_lookup.get(item["account_name"])
        standard_code = mapping.standard_account_code if mapping else None

        line_item = models.FinancialLineItem(
            deal_id=doc.deal_id,
            document_id=document_id,
            standard_account_code=standard_code,
            period_type=item["period_type"],
            period_label=item["period_label"],
            amount=item["amount"],
            is_annualized=item["period_type"] in ["annual", "ttm"],
            is_adjusted=False
        )
        db.add(line_item)
        stored_items.append(line_item)

    db.commit()

    return {
        "document_id": document_id,
        "line_items_created": len(stored_items),
        "mappings_created": len(mappings),
        "unmapped_accounts": len([m for m in mappings if m.mapping_status == "unmapped"])
    }


def calculate_summary_metrics(
    db: Session,
    deal_id: int,
    period_type: str = "ttm"
) -> Dict[str, float]:
    """
    Calculate summary financial metrics from stored line items.
    """
    # Get all line items for the period
    items = db.query(models.FinancialLineItem).filter(
        models.FinancialLineItem.deal_id == deal_id,
        models.FinancialLineItem.period_type == period_type
    ).all()

    # Group by standard account code
    by_account = {}
    for item in items:
        code = item.standard_account_code or "UNMAPPED"
        if code not in by_account:
            by_account[code] = 0
        by_account[code] += item.amount

    # Calculate metrics
    metrics = {}

    # Total Revenue (REV-999 or sum of REV-*)
    revenue_codes = [k for k in by_account.keys() if k.startswith("REV-")]
    metrics["total_revenue"] = sum(by_account.get(c, 0) for c in revenue_codes)

    # Total Labor (sum of labor expenses)
    labor_codes = ["EXP-100", "EXP-110", "EXP-120", "EXP-130", "EXP-140", "EXP-150",
                   "EXP-200", "EXP-210", "EXP-300", "EXP-310", "EXP-320", "EXP-330",
                   "EXP-340", "EXP-350", "EXP-360"]
    metrics["total_labor"] = sum(by_account.get(c, 0) for c in labor_codes)

    # Total Operating Expenses
    opex_codes = [k for k in by_account.keys() if k.startswith("EXP-")]
    metrics["total_opex"] = sum(by_account.get(c, 0) for c in opex_codes)

    # EBITDAR
    metrics["ebitdar"] = metrics["total_revenue"] - metrics["total_opex"]

    # Rent
    metrics["rent"] = by_account.get("FIX-100", 0)

    # EBITDA
    metrics["ebitda"] = metrics["ebitdar"] - metrics["rent"]

    # Depreciation & Amortization
    metrics["d_and_a"] = by_account.get("FIX-200", 0) + by_account.get("FIX-300", 0)

    # EBIT
    metrics["ebit"] = metrics["ebitda"] - metrics["d_and_a"]

    # Interest
    metrics["interest"] = by_account.get("FIX-400", 0)

    # Net Income (approximation)
    metrics["net_income"] = metrics["ebit"] - metrics["interest"]

    # Margins
    if metrics["total_revenue"] > 0:
        metrics["ebitdar_margin"] = metrics["ebitdar"] / metrics["total_revenue"] * 100
        metrics["ebitda_margin"] = metrics["ebitda"] / metrics["total_revenue"] * 100
        metrics["labor_ratio"] = metrics["total_labor"] / metrics["total_revenue"] * 100
    else:
        metrics["ebitdar_margin"] = 0
        metrics["ebitda_margin"] = 0
        metrics["labor_ratio"] = 0

    return metrics


def update_scenario_from_financials(
    db: Session,
    scenario_id: int
) -> models.Scenario:
    """
    Update a scenario with calculated financial metrics.
    """
    scenario = db.query(models.Scenario).filter(models.Scenario.id == scenario_id).first()
    if not scenario:
        raise ValueError(f"Scenario {scenario_id} not found")

    metrics = calculate_summary_metrics(db, scenario.deal_id)

    # Update scenario
    scenario.ebitdar = metrics.get("ebitdar")
    scenario.noi = metrics.get("ebitdar")  # Using EBITDAR as proxy for NOI

    # Calculate implied value if cap rate is set
    assumptions = scenario.assumptions or {}
    cap_rate = assumptions.get("cap_rate")
    if cap_rate and scenario.noi:
        scenario.implied_value = scenario.noi / (cap_rate / 100)

        # Get bed count from deal
        deal = db.query(models.Deal).filter(models.Deal.id == scenario.deal_id).first()
        if deal and deal.total_beds:
            scenario.price_per_bed = scenario.implied_value / deal.total_beds

    scenario.outputs = metrics
    scenario.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(scenario)
    return scenario
