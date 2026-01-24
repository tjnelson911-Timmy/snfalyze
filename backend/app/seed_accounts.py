"""
Seed Standard Chart of Accounts for SNF/Healthcare facilities
Run with: python -m app.seed_accounts
"""
from .database import SessionLocal, engine
from . import models

# Create tables if they don't exist
models.Base.metadata.create_all(bind=engine)

STANDARD_ACCOUNTS = [
    # Revenue
    {"code": "REV-100", "name": "Medicaid Revenue", "category": "revenue", "subcategory": "patient_revenue", "display_order": 100},
    {"code": "REV-110", "name": "Medicare Part A Revenue", "category": "revenue", "subcategory": "patient_revenue", "display_order": 110},
    {"code": "REV-120", "name": "Medicare Part B Revenue", "category": "revenue", "subcategory": "patient_revenue", "display_order": 120},
    {"code": "REV-130", "name": "Managed Care Revenue", "category": "revenue", "subcategory": "patient_revenue", "display_order": 130},
    {"code": "REV-140", "name": "Private Pay Revenue", "category": "revenue", "subcategory": "patient_revenue", "display_order": 140},
    {"code": "REV-150", "name": "VA/Other Government Revenue", "category": "revenue", "subcategory": "patient_revenue", "display_order": 150},
    {"code": "REV-200", "name": "Ancillary Revenue - Therapy", "category": "revenue", "subcategory": "ancillary", "display_order": 200},
    {"code": "REV-210", "name": "Ancillary Revenue - Pharmacy", "category": "revenue", "subcategory": "ancillary", "display_order": 210},
    {"code": "REV-220", "name": "Ancillary Revenue - Other", "category": "revenue", "subcategory": "ancillary", "display_order": 220},
    {"code": "REV-300", "name": "Other Operating Revenue", "category": "revenue", "subcategory": "other", "display_order": 300},
    {"code": "REV-999", "name": "Total Revenue", "category": "revenue", "subcategory": "total", "display_order": 999},

    # Labor Expenses
    {"code": "EXP-100", "name": "Nursing Wages - RN", "category": "expense", "subcategory": "labor_nursing", "display_order": 1000},
    {"code": "EXP-110", "name": "Nursing Wages - LPN/LVN", "category": "expense", "subcategory": "labor_nursing", "display_order": 1010},
    {"code": "EXP-120", "name": "Nursing Wages - CNA", "category": "expense", "subcategory": "labor_nursing", "display_order": 1020},
    {"code": "EXP-130", "name": "Nursing Wages - Other", "category": "expense", "subcategory": "labor_nursing", "display_order": 1030},
    {"code": "EXP-140", "name": "Agency/Contract Labor - Nursing", "category": "expense", "subcategory": "labor_nursing", "display_order": 1040},
    {"code": "EXP-150", "name": "Nursing Benefits", "category": "expense", "subcategory": "labor_nursing", "display_order": 1050},
    {"code": "EXP-200", "name": "Therapy Wages", "category": "expense", "subcategory": "labor_therapy", "display_order": 1100},
    {"code": "EXP-210", "name": "Therapy Contract Services", "category": "expense", "subcategory": "labor_therapy", "display_order": 1110},
    {"code": "EXP-300", "name": "Dietary Wages", "category": "expense", "subcategory": "labor_other", "display_order": 1200},
    {"code": "EXP-310", "name": "Housekeeping/Laundry Wages", "category": "expense", "subcategory": "labor_other", "display_order": 1210},
    {"code": "EXP-320", "name": "Maintenance Wages", "category": "expense", "subcategory": "labor_other", "display_order": 1220},
    {"code": "EXP-330", "name": "Activities Wages", "category": "expense", "subcategory": "labor_other", "display_order": 1230},
    {"code": "EXP-340", "name": "Social Services Wages", "category": "expense", "subcategory": "labor_other", "display_order": 1240},
    {"code": "EXP-350", "name": "Administrative Wages", "category": "expense", "subcategory": "labor_admin", "display_order": 1250},
    {"code": "EXP-360", "name": "Employee Benefits - Non-Nursing", "category": "expense", "subcategory": "labor_other", "display_order": 1260},
    {"code": "EXP-399", "name": "Total Labor Expense", "category": "expense", "subcategory": "labor_total", "display_order": 1399},

    # Non-Labor Operating Expenses
    {"code": "EXP-400", "name": "Dietary/Food Supplies", "category": "expense", "subcategory": "supplies", "display_order": 1400},
    {"code": "EXP-410", "name": "Medical Supplies", "category": "expense", "subcategory": "supplies", "display_order": 1410},
    {"code": "EXP-420", "name": "Pharmacy/Drugs", "category": "expense", "subcategory": "supplies", "display_order": 1420},
    {"code": "EXP-430", "name": "Housekeeping Supplies", "category": "expense", "subcategory": "supplies", "display_order": 1430},
    {"code": "EXP-440", "name": "Other Supplies", "category": "expense", "subcategory": "supplies", "display_order": 1440},
    {"code": "EXP-500", "name": "Utilities", "category": "expense", "subcategory": "occupancy", "display_order": 1500},
    {"code": "EXP-510", "name": "Property Taxes", "category": "expense", "subcategory": "occupancy", "display_order": 1510},
    {"code": "EXP-520", "name": "Property Insurance", "category": "expense", "subcategory": "occupancy", "display_order": 1520},
    {"code": "EXP-530", "name": "Repairs & Maintenance", "category": "expense", "subcategory": "occupancy", "display_order": 1530},
    {"code": "EXP-600", "name": "Professional Liability Insurance", "category": "expense", "subcategory": "insurance", "display_order": 1600},
    {"code": "EXP-610", "name": "Other Insurance", "category": "expense", "subcategory": "insurance", "display_order": 1610},
    {"code": "EXP-700", "name": "Professional Fees - Legal", "category": "expense", "subcategory": "professional", "display_order": 1700},
    {"code": "EXP-710", "name": "Professional Fees - Accounting", "category": "expense", "subcategory": "professional", "display_order": 1710},
    {"code": "EXP-720", "name": "Professional Fees - Consulting", "category": "expense", "subcategory": "professional", "display_order": 1720},
    {"code": "EXP-730", "name": "Professional Fees - Other", "category": "expense", "subcategory": "professional", "display_order": 1730},
    {"code": "EXP-800", "name": "Marketing/Advertising", "category": "expense", "subcategory": "other_opex", "display_order": 1800},
    {"code": "EXP-810", "name": "Travel & Entertainment", "category": "expense", "subcategory": "other_opex", "display_order": 1810},
    {"code": "EXP-820", "name": "Office Supplies & Expenses", "category": "expense", "subcategory": "other_opex", "display_order": 1820},
    {"code": "EXP-830", "name": "IT/Technology", "category": "expense", "subcategory": "other_opex", "display_order": 1830},
    {"code": "EXP-840", "name": "Bad Debt Expense", "category": "expense", "subcategory": "other_opex", "display_order": 1840},
    {"code": "EXP-850", "name": "Other Operating Expenses", "category": "expense", "subcategory": "other_opex", "display_order": 1850},
    {"code": "EXP-899", "name": "Total Operating Expenses", "category": "expense", "subcategory": "opex_total", "display_order": 1899},

    # Management & Corporate
    {"code": "EXP-900", "name": "Management Fee", "category": "expense", "subcategory": "management", "display_order": 1900},
    {"code": "EXP-910", "name": "Corporate Allocation", "category": "expense", "subcategory": "management", "display_order": 1910},

    # Fixed Charges (below EBITDAR)
    {"code": "FIX-100", "name": "Rent/Lease Expense", "category": "fixed_charge", "subcategory": "rent", "display_order": 2000},
    {"code": "FIX-200", "name": "Depreciation", "category": "fixed_charge", "subcategory": "depreciation", "display_order": 2100},
    {"code": "FIX-300", "name": "Amortization", "category": "fixed_charge", "subcategory": "amortization", "display_order": 2200},
    {"code": "FIX-400", "name": "Interest Expense", "category": "fixed_charge", "subcategory": "interest", "display_order": 2300},

    # Summary Lines
    {"code": "SUM-100", "name": "EBITDAR", "category": "summary", "subcategory": "ebitdar", "display_order": 3000},
    {"code": "SUM-110", "name": "EBITDA", "category": "summary", "subcategory": "ebitda", "display_order": 3010},
    {"code": "SUM-120", "name": "EBIT", "category": "summary", "subcategory": "ebit", "display_order": 3020},
    {"code": "SUM-130", "name": "Net Operating Income (NOI)", "category": "summary", "subcategory": "noi", "display_order": 3030},
    {"code": "SUM-140", "name": "Net Income", "category": "summary", "subcategory": "net_income", "display_order": 3040},
]


def seed_standard_accounts():
    """Seed the standard accounts table"""
    db = SessionLocal()
    try:
        # Check if already seeded
        existing = db.query(models.StandardAccount).first()
        if existing:
            print("Standard accounts already seeded")
            return

        for account in STANDARD_ACCOUNTS:
            db_account = models.StandardAccount(**account)
            db.add(db_account)

        db.commit()
        print(f"Seeded {len(STANDARD_ACCOUNTS)} standard accounts")
    except Exception as e:
        print(f"Error seeding accounts: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_standard_accounts()
