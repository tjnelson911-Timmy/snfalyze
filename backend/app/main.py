from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, Response
from sqlalchemy.orm import Session
from typing import List, Optional
import os, re, csv, io, time
from datetime import datetime
import openpyxl
import pdfplumber
from docx import Document as DocxDocument
import requests
from .database import get_db, engine
from . import models, schemas, crud
from . import services
from . import doc_utils
from . import analysis_pipeline
from . import om_scrubber
from . import financial_ingestion
from . import risk_scoring
from . import export_reports
from . import market_analysis
from . import property_research
from . import deep_financial_analysis
from . import slide_builder
from . import presentation_export

models.Base.metadata.create_all(bind=engine)
app = FastAPI(title="SNFalyze Deal Tracker")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Serve static frontend in production
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(STATIC_DIR, "assets")), name="assets")

@app.get("/api/health")
def health(): return {"status": "healthy"}

@app.get("/api/facilities/search")
def search_facilities(q: str, state: Optional[str] = None, limit: int = 20):
    """Search for SNF/ALF facilities by name using CMS Medicare data"""
    if not q or len(q) < 2:
        raise HTTPException(400, "Search query must be at least 2 characters")
    results = services.search_facilities(q, state, limit)
    return {"query": q, "count": len(results), "facilities": results}

@app.get("/api/deals", response_model=List[schemas.DealResponse])
def get_deals(status: Optional[str] = None, search: Optional[str] = None, db: Session = Depends(get_db)):
    return crud.get_deals(db, status, search)

@app.get("/api/deals/stats")
def get_stats(db: Session = Depends(get_db)):
    return crud.get_deal_stats(db)

@app.get("/api/deals/map")
def get_deals_for_map(db: Session = Depends(get_db)):
    """Get all deals with their properties for map display"""
    deals = db.query(models.Deal).all()
    result = []
    for deal in deals:
        props = []
        for p in deal.properties:
            if p.latitude and p.longitude:
                props.append({
                    "id": p.id,
                    "name": p.name,
                    "address": p.address,
                    "city": p.city,
                    "state": p.state,
                    "licensed_beds": p.licensed_beds,
                    "latitude": p.latitude,
                    "longitude": p.longitude
                })
        if props:  # Only include deals that have geocoded properties
            result.append({
                "id": deal.id,
                "name": deal.name,
                "status": deal.status,
                "properties": props
            })
    return result

@app.get("/api/deals/{deal_id}", response_model=schemas.DealDetailResponse)
def get_deal(deal_id: int, db: Session = Depends(get_db)):
    deal = crud.get_deal(db, deal_id)
    if not deal: raise HTTPException(404, "Not found")
    return deal

@app.post("/api/deals", response_model=schemas.DealResponse)
def create_deal(deal: schemas.DealCreate, db: Session = Depends(get_db)):
    return crud.create_deal(db, deal)

@app.put("/api/deals/{deal_id}", response_model=schemas.DealResponse)
def update_deal(deal_id: int, deal: schemas.DealUpdate, db: Session = Depends(get_db)):
    d = crud.update_deal(db, deal_id, deal)
    if not d: raise HTTPException(404, "Not found")
    return d

@app.delete("/api/deals/{deal_id}")
def delete_deal(deal_id: int, db: Session = Depends(get_db)):
    if not crud.delete_deal(db, deal_id): raise HTTPException(404, "Not found")
    return {"message": "Deleted"}

@app.put("/api/deals/{deal_id}/status")
def update_status(deal_id: int, status: schemas.StatusUpdate, db: Session = Depends(get_db)):
    d = crud.update_deal_status(db, deal_id, status.status)
    if not d: raise HTTPException(404, "Not found")
    return d

@app.get("/api/deals/{deal_id}/properties", response_model=List[schemas.PropertyResponse])
def get_props(deal_id: int, db: Session = Depends(get_db)):
    return db.query(models.Property).filter(models.Property.deal_id == deal_id).all()

@app.post("/api/deals/{deal_id}/properties", response_model=schemas.PropertyResponse)
def create_prop(deal_id: int, prop: schemas.PropertyCreate, db: Session = Depends(get_db)):
    return crud.create_property(db, deal_id, prop)

@app.delete("/api/properties/{prop_id}")
def delete_prop(prop_id: int, db: Session = Depends(get_db)):
    if not crud.delete_property(db, prop_id): raise HTTPException(404, "Not found")
    return {"message": "Deleted"}

@app.get("/api/deals/{deal_id}/documents", response_model=List[schemas.DocumentResponse])
def get_docs(deal_id: int, db: Session = Depends(get_db)):
    return crud.get_documents(db, deal_id)

@app.post("/api/deals/{deal_id}/documents")
async def upload_doc(
    deal_id: int,
    file: UploadFile = File(...),
    category: str = Form("other"),
    property_id: Optional[int] = Form(None),
    skip_duplicate_check: bool = Form(False),
    db: Session = Depends(get_db)
):
    """
    Upload a document to a deal with automatic classification and duplicate detection.

    - Calculates SHA-256 checksum for duplicate detection
    - Auto-classifies document type based on filename and content
    - Optionally associates with a specific property
    """
    ext = file.filename.split(".")[-1].lower()
    if ext not in {"pdf", "docx", "xlsx", "csv", "png", "jpg", "jpeg"}:
        raise HTTPException(400, "Invalid file type. Supported: pdf, docx, xlsx, csv, png, jpg")

    # Read file content
    content = await file.read()

    # Calculate checksum
    checksum = doc_utils.calculate_checksum(content)

    # Check for duplicates within this deal
    if not skip_duplicate_check:
        existing = db.query(models.Document).filter(
            models.Document.deal_id == deal_id,
            models.Document.checksum == checksum
        ).first()
        if existing:
            return {
                "message": "Duplicate detected",
                "duplicate": True,
                "existing_document": {
                    "id": existing.id,
                    "filename": existing.original_filename,
                    "uploaded_at": existing.uploaded_at.isoformat() if existing.uploaded_at else None
                }
            }

    # Generate unique filename
    fname = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, fname)

    # Save file
    with open(file_path, "wb") as f:
        f.write(content)

    # Auto-classify document type
    doc_type = None
    classification_confidence = 0.0

    if ext not in {"png", "jpg", "jpeg"}:  # Skip classification for images
        # First try filename-based classification
        doc_type, classification_confidence = doc_utils.classify_document_type(file.filename)

        # If low confidence, try content-based classification
        if classification_confidence < 0.5:
            text_sample = doc_utils.extract_text_sample(file_path, ext)
            if text_sample:
                doc_type, classification_confidence = doc_utils.classify_document_type(
                    file.filename, text_sample
                )

    # Create document record
    doc = crud.create_document(
        db,
        deal_id,
        schemas.DocumentCreate(
            filename=fname,
            original_filename=file.filename,
            file_type=ext,
            file_size=len(content),
            category=category,
            checksum=checksum,
            doc_type=doc_type
        ),
        property_id=property_id
    )

    # Log activity
    crud.log_activity(db, deal_id, "document_uploaded", f"Document '{file.filename}' uploaded")

    return {
        "message": "Uploaded",
        "document": doc,
        "classification": {
            "doc_type": doc_type,
            "doc_type_display": doc_utils.get_doc_type_display_name(doc_type) if doc_type else None,
            "confidence": classification_confidence
        }
    }

@app.post("/api/documents/{doc_id}/analyze")
def analyze_doc(doc_id: int, auto_apply: bool = False, db: Session = Depends(get_db)):
    """Analyze document and extract metrics. If auto_apply=True, apply extracted metrics to the deal."""
    doc = crud.get_document(db, doc_id)
    if not doc: raise HTTPException(404, "Not found")
    path = os.path.join(UPLOAD_DIR, doc.filename)

    # Use enhanced analysis
    result = services.analyze_document(path, doc.file_type, doc.original_filename)

    # Update document with analysis
    crud.update_doc_analysis(db, doc_id, result["summary"])

    # Optionally apply extracted metrics to the deal
    if auto_apply and result.get("metrics"):
        metrics = result["metrics"]
        deal = crud.get_deal(db, doc.deal_id)
        if deal:
            update_data = {}
            if "beds" in metrics and not deal.total_beds:
                update_data["total_beds"] = metrics["beds"]
            if "ebitdar" in metrics and not deal.ebitdar:
                update_data["ebitdar"] = metrics["ebitdar"]
            if "asking_price" in metrics and not deal.asking_price:
                update_data["asking_price"] = metrics["asking_price"]
            if "cap_rate" in metrics and not deal.cap_rate:
                update_data["cap_rate"] = metrics["cap_rate"]
            if update_data:
                crud.update_deal(db, doc.deal_id, schemas.DealUpdate(**update_data))

    return {
        "document_id": doc_id,
        "document_type": result["document_type"],
        "summary": result["summary"],
        "metrics": result["metrics"],
        "confidence": result["confidence"],
        "extracted_data": result.get("extracted_data", {})
    }

@app.delete("/api/documents/{doc_id}")
def delete_doc(doc_id: int, db: Session = Depends(get_db)):
    doc = crud.get_document(db, doc_id)
    if not doc: raise HTTPException(404, "Not found")
    try: os.remove(os.path.join(UPLOAD_DIR, doc.filename))
    except: pass
    crud.delete_document(db, doc_id)
    return {"message": "Deleted"}

@app.patch("/api/documents/{doc_id}/category")
def update_doc_category(doc_id: int, category: str, db: Session = Depends(get_db)):
    doc = crud.get_document(db, doc_id)
    if not doc: raise HTTPException(404, "Not found")
    doc.category = category
    db.commit()
    db.refresh(doc)
    return {"message": "Updated", "document": doc}

@app.patch("/api/documents/{doc_id}/rename")
def rename_doc(doc_id: int, name: str, db: Session = Depends(get_db)):
    doc = crud.get_document(db, doc_id)
    if not doc: raise HTTPException(404, "Not found")
    doc.original_filename = name
    db.commit()
    db.refresh(doc)
    return {"message": "Renamed", "document": doc}

@app.patch("/api/documents/{doc_id}/doc-type")
def update_doc_type(doc_id: int, doc_type: str, db: Session = Depends(get_db)):
    """Manually update document type classification"""
    doc = crud.get_document(db, doc_id)
    if not doc: raise HTTPException(404, "Not found")

    # Validate doc_type
    valid_types = list(doc_utils.DOC_TYPE_PATTERNS.keys()) + ["other"]
    if doc_type not in valid_types:
        raise HTTPException(400, f"Invalid doc_type. Valid types: {', '.join(valid_types)}")

    doc.doc_type = doc_type
    db.commit()
    db.refresh(doc)
    return {
        "message": "Updated",
        "document": doc,
        "doc_type_display": doc_utils.get_doc_type_display_name(doc_type)
    }

@app.get("/api/document-types")
def get_document_types():
    """Get all available document types with display names"""
    types = []
    for key in doc_utils.DOC_TYPE_PATTERNS.keys():
        types.append({
            "key": key,
            "display_name": doc_utils.get_doc_type_display_name(key)
        })
    types.append({"key": "other", "display_name": "Other Document"})
    return {"document_types": types}

@app.post("/api/deals/{deal_id}/documents/check-duplicate")
async def check_document_duplicate(
    deal_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Check if a document is a duplicate before full upload"""
    content = await file.read()
    checksum = doc_utils.calculate_checksum(content)

    # Check within this deal
    existing_in_deal = db.query(models.Document).filter(
        models.Document.deal_id == deal_id,
        models.Document.checksum == checksum
    ).first()

    # Also check across all deals
    existing_anywhere = db.query(models.Document).filter(
        models.Document.checksum == checksum
    ).first()

    result = {
        "is_duplicate": existing_in_deal is not None,
        "checksum": checksum,
        "filename": file.filename
    }

    if existing_in_deal:
        result["existing_in_deal"] = {
            "id": existing_in_deal.id,
            "filename": existing_in_deal.original_filename,
            "uploaded_at": existing_in_deal.uploaded_at.isoformat() if existing_in_deal.uploaded_at else None
        }

    if existing_anywhere and existing_anywhere.deal_id != deal_id:
        result["existing_in_other_deal"] = {
            "id": existing_anywhere.id,
            "deal_id": existing_anywhere.deal_id,
            "filename": existing_anywhere.original_filename,
            "uploaded_at": existing_anywhere.uploaded_at.isoformat() if existing_anywhere.uploaded_at else None
        }

    return result

@app.post("/api/deals/{deal_id}/categories")
def add_category(deal_id: int, label: str, db: Session = Depends(get_db)):
    """Add a custom document category to a deal"""
    deal = crud.get_deal(db, deal_id)
    if not deal: raise HTTPException(404, "Not found")

    # Generate a key from the label
    key = re.sub(r'[^a-z0-9]+', '_', label.lower()).strip('_')
    if not key: raise HTTPException(400, "Invalid category name")

    # Initialize if None
    categories = deal.custom_categories or []

    # Check if key already exists
    if any(c['key'] == key for c in categories):
        raise HTTPException(400, "Category already exists")

    categories.append({"key": key, "label": label})
    deal.custom_categories = categories
    db.commit()
    db.refresh(deal)
    return {"message": "Added", "category": {"key": key, "label": label}, "custom_categories": deal.custom_categories}

@app.patch("/api/deals/{deal_id}/categories/{category_key}")
def rename_category(deal_id: int, category_key: str, label: str, db: Session = Depends(get_db)):
    """Rename a document category (custom or default)"""
    deal = crud.get_deal(db, deal_id)
    if not deal: raise HTTPException(404, "Not found")

    categories = deal.custom_categories or []

    # Find and update the category
    found = False
    for cat in categories:
        if cat['key'] == category_key:
            cat['label'] = label
            found = True
            break

    # If not found in custom, it might be a default category being customized
    if not found:
        # Add it as a custom override
        categories.append({"key": category_key, "label": label})

    deal.custom_categories = categories
    db.commit()
    db.refresh(deal)
    return {"message": "Renamed", "custom_categories": deal.custom_categories}

@app.delete("/api/deals/{deal_id}/categories/{category_key}")
def delete_category(deal_id: int, category_key: str, move_to: str = "other", db: Session = Depends(get_db)):
    """Delete a custom category and move its documents to another category"""
    deal = crud.get_deal(db, deal_id)
    if not deal: raise HTTPException(404, "Not found")

    categories = deal.custom_categories or []

    # Remove the category
    categories = [c for c in categories if c['key'] != category_key]
    deal.custom_categories = categories

    # Move documents from deleted category to the target
    for doc in deal.documents:
        if doc.category == category_key:
            doc.category = move_to

    db.commit()
    db.refresh(deal)
    return {"message": "Deleted", "custom_categories": deal.custom_categories}

@app.get("/api/deals/{deal_id}/activity", response_model=List[schemas.ActivityResponse])
def get_activity(deal_id: int, db: Session = Depends(get_db)):
    return crud.get_activity(db, deal_id)

@app.get("/api/deals/{deal_id}/valuation")
def get_valuation(deal_id: int, db: Session = Depends(get_db)):
    deal = crud.get_deal(db, deal_id)
    if not deal: raise HTTPException(404, "Not found")
    return crud.calc_valuation(deal)

@app.get("/api/deals/{deal_id}/tasks", response_model=List[schemas.TaskResponse])
def get_tasks(deal_id: int, db: Session = Depends(get_db)):
    return crud.get_tasks(db, deal_id)

@app.post("/api/deals/{deal_id}/tasks", response_model=schemas.TaskResponse)
def create_task(deal_id: int, task: schemas.TaskCreate, db: Session = Depends(get_db)):
    return crud.create_task(db, deal_id, task)

@app.put("/api/tasks/{task_id}", response_model=schemas.TaskResponse)
def update_task(task_id: int, task: schemas.TaskUpdate, db: Session = Depends(get_db)):
    t = crud.update_task(db, task_id, task)
    if not t: raise HTTPException(404, "Not found")
    return t

# Current Operations endpoints
@app.get("/api/current-operations")
def get_current_operations(db: Session = Depends(get_db)):
    """Get all current operations grouped by company"""
    ops = db.query(models.CurrentOperation).order_by(models.CurrentOperation.company, models.CurrentOperation.team).all()
    # Group by company
    grouped = {}
    for op in ops:
        if op.company not in grouped:
            grouped[op.company] = {"company": op.company, "teams": {}}
        if op.team not in grouped[op.company]["teams"]:
            grouped[op.company]["teams"][op.team] = []
        grouped[op.company]["teams"][op.team].append({
            "id": op.id,
            "property_name": op.property_name,
            "property_type": op.property_type,
            "address": op.address,
            "city": op.city,
            "state": op.state,
            "beds": op.beds,
            "notes": op.notes,
            "latitude": op.latitude,
            "longitude": op.longitude
        })
    return {"companies": list(grouped.values()), "total": len(ops)}

def parse_csv_content(content: bytes) -> List[dict]:
    """Parse CSV content and return list of rows as dicts"""
    decoded = content.decode('utf-8')
    reader = csv.DictReader(io.StringIO(decoded))
    return list(reader)

def parse_excel_content(content: bytes) -> List[dict]:
    """Parse Excel content and return list of rows as dicts"""
    wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []
    # First row is headers
    headers = [str(h).strip() if h else f'col_{i}' for i, h in enumerate(rows[0])]
    result = []
    for row in rows[1:]:
        if any(cell for cell in row):  # Skip empty rows
            result.append({headers[i]: row[i] for i in range(min(len(headers), len(row)))})
    return result

def parse_word_content(content: bytes) -> List[dict]:
    """Parse Word document tables and return list of rows as dicts"""
    doc = DocxDocument(io.BytesIO(content))
    result = []
    for table in doc.tables:
        rows = [[cell.text.strip() for cell in row.cells] for row in table.rows]
        if not rows:
            continue
        headers = rows[0]
        for row in rows[1:]:
            if any(cell for cell in row):
                result.append({headers[i]: row[i] for i in range(min(len(headers), len(row)))})
    return result

def parse_pdf_content(content: bytes) -> List[dict]:
    """Parse PDF tables and return list of rows as dicts"""
    result = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                if not table or len(table) < 2:
                    continue
                headers = [str(h).strip() if h else f'col_{i}' for i, h in enumerate(table[0])]
                for row in table[1:]:
                    if any(cell for cell in row):
                        result.append({headers[i]: (row[i] or '').strip() for i in range(min(len(headers), len(row)))})
    return result

def geocode_address(address: str, city: str, state: str) -> tuple:
    """Geocode an address using Nominatim (OpenStreetMap). Returns (lat, lng) or (None, None)"""
    if not any([address, city, state]):
        return None, None

    # Build address string
    parts = []
    if address:
        parts.append(address)
    if city:
        parts.append(city)
    if state:
        parts.append(state)
    parts.append("USA")

    query = ", ".join(parts)

    try:
        response = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": query, "format": "json", "limit": 1},
            headers={"User-Agent": "SNFalyze/1.0"},
            timeout=5
        )
        if response.ok and response.json():
            result = response.json()[0]
            return float(result["lat"]), float(result["lon"])
    except Exception as e:
        print(f"Geocoding failed for {query}: {e}")

    return None, None

def normalize_row(row: dict) -> dict:
    """Normalize column names to expected format"""
    # Create case-insensitive lookup
    lower_row = {k.lower().strip(): v for k, v in row.items() if k}

    def get_val(*keys):
        for k in keys:
            if k in lower_row and lower_row[k]:
                return str(lower_row[k]).strip()
        return None

    beds_val = get_val('beds', 'bed count', 'total beds', 'licensed beds')
    beds = None
    if beds_val:
        try:
            beds = int(float(beds_val))
        except:
            pass

    return {
        'company': get_val('company', 'company name', 'operator') or 'Unknown',
        'team': get_val('team', 'team name', 'region', 'group'),
        'property_name': get_val('property name', 'property', 'name', 'facility', 'facility name'),
        'property_type': get_val('property type', 'type', 'facility type'),
        'address': get_val('address', 'street', 'street address'),
        'city': get_val('city'),
        'state': get_val('state', 'st'),
        'beds': beds,
        'notes': get_val('notes', 'note', 'comments', 'comment')
    }

@app.post("/api/current-operations/upload")
async def upload_current_operations(file: UploadFile = File(...), replace: bool = True, db: Session = Depends(get_db)):
    """Upload a file with current operations. Supports CSV, Excel (.xlsx), Word (.docx), and PDF files.
    Expected columns: Company, Team, Property Name, Property Type, Address, City, State, Beds, Notes"""

    filename = file.filename.lower()
    content = await file.read()

    # Parse based on file type
    try:
        if filename.endswith('.csv'):
            rows = parse_csv_content(content)
        elif filename.endswith(('.xlsx', '.xls')):
            rows = parse_excel_content(content)
        elif filename.endswith('.docx'):
            rows = parse_word_content(content)
        elif filename.endswith('.pdf'):
            rows = parse_pdf_content(content)
        else:
            raise HTTPException(400, "Unsupported file type. Please upload CSV, Excel (.xlsx), Word (.docx), or PDF files.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400, f"Failed to parse file: {str(e)}")

    if not rows:
        raise HTTPException(400, "No data found in file. Make sure the file contains a table with headers.")

    # Clear existing if replace is True
    if replace:
        db.query(models.CurrentOperation).delete()

    count = 0
    for row in rows:
        normalized = normalize_row(row)

        # Geocode the address
        lat, lng = geocode_address(normalized['address'], normalized['city'], normalized['state'])
        normalized['latitude'] = lat
        normalized['longitude'] = lng

        op = models.CurrentOperation(**normalized)
        db.add(op)
        count += 1

        # Rate limit for Nominatim (1 request per second)
        if lat is not None:
            time.sleep(0.5)

    db.commit()
    return {"message": f"Uploaded {count} operations", "count": count}

@app.delete("/api/current-operations")
def clear_current_operations(db: Session = Depends(get_db)):
    """Clear all current operations"""
    count = db.query(models.CurrentOperation).delete()
    db.commit()
    return {"message": f"Deleted {count} operations"}

@app.post("/api/current-operations/geocode")
def geocode_current_operations(db: Session = Depends(get_db)):
    """Geocode all current operations that don't have coordinates"""
    ops = db.query(models.CurrentOperation).filter(
        (models.CurrentOperation.latitude == None) | (models.CurrentOperation.longitude == None)
    ).all()

    count = 0
    for op in ops:
        lat, lng = geocode_address(op.address, op.city, op.state)
        if lat and lng:
            op.latitude = lat
            op.longitude = lng
            count += 1
            time.sleep(1)  # Rate limit for Nominatim

    db.commit()
    return {"message": f"Geocoded {count} of {len(ops)} operations"}

@app.post("/api/properties/geocode")
def geocode_properties(db: Session = Depends(get_db)):
    """Geocode all deal properties that don't have coordinates"""
    props = db.query(models.Property).filter(
        (models.Property.latitude == None) | (models.Property.longitude == None)
    ).all()

    count = 0
    for prop in props:
        lat, lng = geocode_address(prop.address, prop.city, prop.state)
        if lat and lng:
            prop.latitude = lat
            prop.longitude = lng
            count += 1
            time.sleep(1)  # Rate limit for Nominatim

    db.commit()
    return {"message": f"Geocoded {count} of {len(props)} properties"}


# ============================================================================
# DOCUMENT ANALYSIS ENDPOINTS
# ============================================================================

@app.get("/api/standard-accounts", response_model=List[schemas.StandardAccountResponse])
def get_standard_accounts(category: Optional[str] = None, db: Session = Depends(get_db)):
    """Get all standard chart of accounts, optionally filtered by category"""
    return crud.get_standard_accounts(db, category)

@app.get("/api/documents/{doc_id}/artifacts", response_model=List[schemas.ParsedArtifactResponse])
def get_document_artifacts(doc_id: int, artifact_type: Optional[str] = None, db: Session = Depends(get_db)):
    """Get parsed artifacts (tables, text blocks) from a document"""
    return crud.get_parsed_artifacts(db, doc_id, artifact_type)

@app.get("/api/documents/{doc_id}/extracted-fields", response_model=List[schemas.ExtractedFieldResponse])
def get_document_extracted_fields(doc_id: int, db: Session = Depends(get_db)):
    """Get all extracted fields from a document"""
    return crud.get_extracted_fields(db, document_id=doc_id)

@app.post("/api/documents/{doc_id}/extracted-fields", response_model=schemas.ExtractedFieldResponse)
def create_extracted_field(doc_id: int, field: schemas.ExtractedFieldCreate, db: Session = Depends(get_db)):
    """Manually add an extracted field to a document"""
    doc = crud.get_document(db, doc_id)
    if not doc: raise HTTPException(404, "Document not found")
    return crud.create_extracted_field(db, doc_id, doc.deal_id, field, property_id=None)

@app.patch("/api/extracted-fields/{field_id}", response_model=schemas.ExtractedFieldResponse)
def update_extracted_field(field_id: int, update: schemas.ExtractedFieldUpdate, db: Session = Depends(get_db)):
    """Update an extracted field (e.g., verify or correct value)"""
    field = crud.update_extracted_field(db, field_id, update)
    if not field: raise HTTPException(404, "Field not found")
    return field

@app.get("/api/documents/{doc_id}/claims", response_model=List[schemas.ClaimResponse])
def get_document_claims(doc_id: int, db: Session = Depends(get_db)):
    """Get all claims extracted from a document"""
    return crud.get_claims(db, document_id=doc_id)

@app.post("/api/documents/{doc_id}/claims", response_model=schemas.ClaimResponse)
def create_claim(doc_id: int, claim: schemas.ClaimCreate, db: Session = Depends(get_db)):
    """Manually add a claim from a document"""
    doc = crud.get_document(db, doc_id)
    if not doc: raise HTTPException(404, "Document not found")
    return crud.create_claim(db, doc_id, doc.deal_id, claim, property_id=None)

@app.patch("/api/claims/{claim_id}/verify", response_model=schemas.ClaimResponse)
def verify_claim(claim_id: int, verification: schemas.ClaimVerification, db: Session = Depends(get_db)):
    """Verify or dispute a claim"""
    claim = crud.update_claim_verification(db, claim_id, verification)
    if not claim: raise HTTPException(404, "Claim not found")
    return claim

@app.get("/api/deals/{deal_id}/extracted-fields", response_model=List[schemas.ExtractedFieldResponse])
def get_deal_extracted_fields(deal_id: int, db: Session = Depends(get_db)):
    """Get all extracted fields for a deal"""
    return crud.get_extracted_fields(db, deal_id=deal_id)

@app.get("/api/deals/{deal_id}/claims", response_model=List[schemas.ClaimResponse])
def get_deal_claims(deal_id: int, category: Optional[str] = None, status: Optional[str] = None, db: Session = Depends(get_db)):
    """Get all claims for a deal, optionally filtered by category or verification status"""
    return crud.get_claims(db, deal_id=deal_id, category=category, verification_status=status)

@app.get("/api/deals/{deal_id}/coa-mappings", response_model=List[schemas.COAMappingResponse])
def get_deal_coa_mappings(deal_id: int, status: Optional[str] = None, db: Session = Depends(get_db)):
    """Get chart of accounts mappings for a deal"""
    return crud.get_coa_mappings(db, deal_id, status)

@app.post("/api/deals/{deal_id}/coa-mappings", response_model=schemas.COAMappingResponse)
def create_coa_mapping(deal_id: int, mapping: schemas.COAMappingCreate, db: Session = Depends(get_db)):
    """Create a new COA mapping for a deal"""
    return crud.create_coa_mapping(db, deal_id, mapping)

@app.patch("/api/coa-mappings/{mapping_id}/approve", response_model=schemas.COAMappingResponse)
def approve_coa_mapping(mapping_id: int, approval: schemas.COAMappingApproval, db: Session = Depends(get_db)):
    """Approve or reject a COA mapping"""
    mapping = crud.approve_coa_mapping(db, mapping_id, approval)
    if not mapping: raise HTTPException(404, "Mapping not found")
    return mapping

@app.get("/api/deals/{deal_id}/financial-line-items", response_model=List[schemas.FinancialLineItemResponse])
def get_deal_financials(deal_id: int, period_type: Optional[str] = None, db: Session = Depends(get_db)):
    """Get financial line items for a deal"""
    return crud.get_financial_line_items(db, deal_id, period_type)

@app.post("/api/deals/{deal_id}/financial-line-items", response_model=schemas.FinancialLineItemResponse)
def create_financial_line_item(deal_id: int, item: schemas.FinancialLineItemCreate, document_id: Optional[int] = None, property_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Create a financial line item"""
    return crud.create_financial_line_item(db, deal_id, item, document_id, property_id)

@app.get("/api/deals/{deal_id}/scenarios", response_model=List[schemas.ScenarioResponse])
def get_deal_scenarios(deal_id: int, db: Session = Depends(get_db)):
    """Get all scenarios for a deal"""
    return crud.get_scenarios(db, deal_id)

@app.post("/api/deals/{deal_id}/scenarios", response_model=schemas.ScenarioResponse)
def create_scenario(deal_id: int, scenario: schemas.ScenarioCreate, db: Session = Depends(get_db)):
    """Create a new scenario for a deal"""
    return crud.create_scenario(db, deal_id, scenario)

@app.put("/api/scenarios/{scenario_id}", response_model=schemas.ScenarioResponse)
def update_scenario(scenario_id: int, update: schemas.ScenarioUpdate, db: Session = Depends(get_db)):
    """Update a scenario"""
    scenario = crud.update_scenario(db, scenario_id, update)
    if not scenario: raise HTTPException(404, "Scenario not found")
    return scenario

@app.get("/api/deals/{deal_id}/risk-flags", response_model=List[schemas.RiskFlagResponse])
def get_deal_risk_flags(deal_id: int, status: Optional[str] = None, severity: Optional[str] = None, db: Session = Depends(get_db)):
    """Get risk flags for a deal"""
    return crud.get_risk_flags(db, deal_id, status, severity)

@app.post("/api/deals/{deal_id}/risk-flags", response_model=schemas.RiskFlagResponse)
def create_risk_flag(deal_id: int, flag: schemas.RiskFlagCreate, property_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Create a new risk flag"""
    return crud.create_risk_flag(db, deal_id, flag, property_id)

@app.patch("/api/risk-flags/{flag_id}", response_model=schemas.RiskFlagResponse)
def update_risk_flag(flag_id: int, update: schemas.RiskFlagUpdate, db: Session = Depends(get_db)):
    """Update a risk flag (e.g., acknowledge, mitigate)"""
    flag = crud.update_risk_flag(db, flag_id, update)
    if not flag: raise HTTPException(404, "Risk flag not found")
    return flag

@app.get("/api/deals/{deal_id}/scorecard", response_model=schemas.DealScorecardResponse)
def get_deal_scorecard(deal_id: int, db: Session = Depends(get_db)):
    """Get or create deal scorecard"""
    return crud.get_or_create_scorecard(db, deal_id)

@app.get("/api/deals/{deal_id}/analysis-jobs", response_model=List[schemas.AnalysisJobResponse])
def get_deal_analysis_jobs(deal_id: int, status: Optional[str] = None, db: Session = Depends(get_db)):
    """Get analysis jobs for a deal"""
    return crud.get_analysis_jobs(db, deal_id=deal_id, status=status)

@app.get("/api/documents/{doc_id}/analysis-jobs", response_model=List[schemas.AnalysisJobResponse])
def get_document_analysis_jobs(doc_id: int, status: Optional[str] = None, db: Session = Depends(get_db)):
    """Get analysis jobs for a document"""
    return crud.get_analysis_jobs(db, document_id=doc_id, status=status)

@app.post("/api/documents/{doc_id}/analyze-full", response_model=schemas.AnalysisJobResponse)
def start_document_analysis(doc_id: int, db: Session = Depends(get_db)):
    """Start full background analysis of a document (parsing, extraction, claims)"""
    doc = crud.get_document(db, doc_id)
    if not doc: raise HTTPException(404, "Document not found")
    return analysis_pipeline.start_document_analysis(db, doc_id)

@app.post("/api/deals/{deal_id}/analyze-all", response_model=schemas.AnalysisJobResponse)
def start_deal_analysis(deal_id: int, db: Session = Depends(get_db)):
    """Start background analysis of all documents in a deal"""
    deal = crud.get_deal(db, deal_id)
    if not deal: raise HTTPException(404, "Deal not found")
    return analysis_pipeline.start_deal_analysis(db, deal_id)

@app.get("/api/analysis-jobs/{job_id}", response_model=schemas.AnalysisJobResponse)
def get_analysis_job(job_id: int, db: Session = Depends(get_db)):
    """Get status of an analysis job"""
    job = db.query(models.AnalysisJob).filter(models.AnalysisJob.id == job_id).first()
    if not job: raise HTTPException(404, "Job not found")
    return job

@app.get("/api/documents/{doc_id}/om-scrub-report", response_model=schemas.OMScrubReport)
def get_om_scrub_report(doc_id: int, db: Session = Depends(get_db)):
    """Generate OM scrub report for a document"""
    doc = crud.get_document(db, doc_id)
    if not doc: raise HTTPException(404, "Document not found")
    if doc.doc_type != "om":
        raise HTTPException(400, "Document is not classified as an Offering Memorandum")
    return om_scrubber.generate_om_scrub_report(db, doc_id)

@app.post("/api/deals/{deal_id}/verify-claims")
def verify_deal_claims(deal_id: int, db: Session = Depends(get_db)):
    """Auto-verify OM claims against extracted evidence"""
    deal = crud.get_deal(db, deal_id)
    if not deal: raise HTTPException(404, "Deal not found")
    updated = om_scrubber.verify_claims_against_evidence(db, deal_id)
    return {"message": f"Verified {updated} claims", "claims_updated": updated}

@app.post("/api/documents/{doc_id}/ingest-financials")
def ingest_financial_document(doc_id: int, db: Session = Depends(get_db)):
    """Parse and ingest financial data from a document"""
    doc = crud.get_document(db, doc_id)
    if not doc: raise HTTPException(404, "Document not found")
    if doc.doc_type not in ["financials", "gl"]:
        raise HTTPException(400, "Document must be a financial statement or general ledger")
    result = financial_ingestion.ingest_financial_document(db, doc_id)
    return result

@app.get("/api/deals/{deal_id}/financial-summary")
def get_financial_summary(deal_id: int, period_type: str = "ttm", db: Session = Depends(get_db)):
    """Get calculated financial summary metrics for a deal"""
    deal = crud.get_deal(db, deal_id)
    if not deal: raise HTTPException(404, "Deal not found")
    metrics = financial_ingestion.calculate_summary_metrics(db, deal_id, period_type)
    return {"deal_id": deal_id, "period_type": period_type, "metrics": metrics}

@app.post("/api/scenarios/{scenario_id}/calculate")
def calculate_scenario(scenario_id: int, db: Session = Depends(get_db)):
    """Recalculate scenario outputs from financial data"""
    scenario = financial_ingestion.update_scenario_from_financials(db, scenario_id)
    return scenario

@app.post("/api/deals/{deal_id}/detect-risks")
def detect_deal_risks(deal_id: int, db: Session = Depends(get_db)):
    """Detect and create risk flags for a deal"""
    deal = crud.get_deal(db, deal_id)
    if not deal: raise HTTPException(404, "Deal not found")
    count = risk_scoring.create_risk_flags_for_deal(db, deal_id)
    return {"message": f"Created {count} new risk flags", "flags_created": count}

@app.post("/api/deals/{deal_id}/calculate-scorecard", response_model=schemas.DealScorecardResponse)
def calculate_deal_scorecard(deal_id: int, db: Session = Depends(get_db)):
    """Calculate comprehensive deal scorecard"""
    deal = crud.get_deal(db, deal_id)
    if not deal: raise HTTPException(404, "Deal not found")
    scorecard = risk_scoring.calculate_deal_scorecard(db, deal_id)
    return scorecard

@app.post("/api/deals/{deal_id}/full-analysis")
def run_full_deal_analysis(deal_id: int, db: Session = Depends(get_db)):
    """Run complete analysis pipeline: analyze docs, verify claims, detect risks, calculate scorecard"""
    deal = crud.get_deal(db, deal_id)
    if not deal: raise HTTPException(404, "Deal not found")

    results = {"deal_id": deal_id, "steps": []}

    # Step 1: Start document analysis
    analysis_job = analysis_pipeline.start_deal_analysis(db, deal_id)
    results["steps"].append({
        "step": "document_analysis",
        "job_id": analysis_job.id,
        "status": "started"
    })

    # Step 2: Verify claims (runs on already-processed claims)
    claims_updated = om_scrubber.verify_claims_against_evidence(db, deal_id)
    results["steps"].append({
        "step": "claim_verification",
        "claims_updated": claims_updated
    })

    # Step 3: Detect risks
    risks_created = risk_scoring.create_risk_flags_for_deal(db, deal_id)
    results["steps"].append({
        "step": "risk_detection",
        "flags_created": risks_created
    })

    # Step 4: Calculate scorecard
    scorecard = risk_scoring.calculate_deal_scorecard(db, deal_id)
    results["steps"].append({
        "step": "scorecard",
        "overall_score": scorecard.overall_score,
        "recommendation": scorecard.recommendation
    })

    return results

@app.get("/api/deals/{deal_id}/field-overrides", response_model=List[schemas.FieldOverrideResponse])
def get_deal_field_overrides(deal_id: int, db: Session = Depends(get_db)):
    """Get field override audit trail for a deal"""
    overrides = db.query(models.FieldOverride).filter(
        models.FieldOverride.deal_id == deal_id
    ).order_by(models.FieldOverride.created_at.desc()).all()
    return overrides

@app.post("/api/deals/{deal_id}/field-overrides", response_model=schemas.FieldOverrideResponse)
def create_field_override(deal_id: int, override: schemas.FieldOverrideCreate, db: Session = Depends(get_db)):
    """Record a field override for audit trail"""
    db_override = models.FieldOverride(
        deal_id=deal_id,
        entity_type=override.entity_type,
        entity_id=override.entity_id,
        field_name=override.field_name,
        old_value=override.old_value,
        new_value=override.new_value,
        reason=override.reason,
        overridden_by=override.overridden_by
    )
    db.add(db_override)
    db.commit()
    db.refresh(db_override)
    return db_override


# ============================================================================
# EXPORT ENDPOINTS
# ============================================================================

@app.get("/api/deals/{deal_id}/export/ic-memo")
def export_ic_memo_json(deal_id: int, db: Session = Depends(get_db)):
    """Export IC memo data as JSON"""
    deal = crud.get_deal(db, deal_id)
    if not deal: raise HTTPException(404, "Deal not found")
    return export_reports.generate_ic_memo(db, deal_id)

@app.get("/api/deals/{deal_id}/export/ic-memo.html", response_class=HTMLResponse)
def export_ic_memo_html(deal_id: int, db: Session = Depends(get_db)):
    """Export IC memo as HTML document"""
    deal = crud.get_deal(db, deal_id)
    if not deal: raise HTTPException(404, "Deal not found")
    html = export_reports.generate_ic_memo_html(db, deal_id)
    return HTMLResponse(content=html)

@app.get("/api/documents/{doc_id}/export/om-scrub-report.html", response_class=HTMLResponse)
def export_om_scrub_html(doc_id: int, db: Session = Depends(get_db)):
    """Export OM scrub report as HTML"""
    doc = crud.get_document(db, doc_id)
    if not doc: raise HTTPException(404, "Document not found")
    if doc.doc_type != "om":
        raise HTTPException(400, "Document is not an Offering Memorandum")
    html = export_reports.export_om_scrub_report_html(db, doc_id)
    return HTMLResponse(content=html)

@app.get("/api/deals/{deal_id}/export/data.json")
def export_deal_data(deal_id: int, db: Session = Depends(get_db)):
    """Export complete deal data as JSON"""
    deal = crud.get_deal(db, deal_id)
    if not deal: raise HTTPException(404, "Deal not found")
    return export_reports.export_deal_data_json(db, deal_id)

@app.get("/api/deals/{deal_id}/export/financials.csv")
def export_financials_csv(deal_id: int, db: Session = Depends(get_db)):
    """Export financial line items as CSV"""
    deal = crud.get_deal(db, deal_id)
    if not deal: raise HTTPException(404, "Deal not found")
    csv_content = export_reports.export_financial_summary_csv(db, deal_id)
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=deal_{deal_id}_financials.csv"}
    )


# ============================================================================
# ENHANCED ANALYSIS ENDPOINTS
# ============================================================================

@app.get("/api/deals/{deal_id}/market-analysis")
def get_market_analysis(deal_id: int, db: Session = Depends(get_db)):
    """Get comprehensive market analysis including regulatory, reimbursement, and demographics"""
    deal = crud.get_deal(db, deal_id)
    if not deal: raise HTTPException(404, "Deal not found")
    return market_analysis.generate_market_analysis(db, deal_id)

@app.post("/api/deals/{deal_id}/market-analysis")
def run_market_analysis(deal_id: int, db: Session = Depends(get_db)):
    """Run and store market analysis for a deal"""
    deal = crud.get_deal(db, deal_id)
    if not deal: raise HTTPException(404, "Deal not found")
    analysis = market_analysis.generate_market_analysis(db, deal_id)
    market_analysis.store_market_analysis(db, deal_id, analysis)
    return analysis

@app.get("/api/deals/{deal_id}/property-research")
def get_property_research(deal_id: int, db: Session = Depends(get_db)):
    """Get property research including CMS data, inspection history, and risk indicators"""
    deal = crud.get_deal(db, deal_id)
    if not deal: raise HTTPException(404, "Deal not found")
    return property_research.research_deal_properties(db, deal_id)

@app.post("/api/deals/{deal_id}/property-research")
def run_property_research(deal_id: int, db: Session = Depends(get_db)):
    """Run and store property research for a deal"""
    deal = crud.get_deal(db, deal_id)
    if not deal: raise HTTPException(404, "Deal not found")
    research = property_research.research_deal_properties(db, deal_id)
    property_research.store_property_research(db, deal_id, research)
    return research

@app.get("/api/properties/{property_id}/research")
def get_single_property_research(property_id: int, db: Session = Depends(get_db)):
    """Get research for a single property"""
    prop = db.query(models.Property).filter(models.Property.id == property_id).first()
    if not prop: raise HTTPException(404, "Property not found")
    return property_research.research_property(db, property_id)

@app.get("/api/deals/{deal_id}/deep-financial-analysis")
def get_deep_financial_analysis(deal_id: int, db: Session = Depends(get_db)):
    """Get comprehensive financial analysis with benchmarking and trends"""
    deal = crud.get_deal(db, deal_id)
    if not deal: raise HTTPException(404, "Deal not found")
    return deep_financial_analysis.generate_deep_financial_analysis(db, deal_id)

@app.post("/api/deals/{deal_id}/deep-financial-analysis")
def run_deep_financial_analysis(deal_id: int, db: Session = Depends(get_db)):
    """Run and store deep financial analysis for a deal"""
    deal = crud.get_deal(db, deal_id)
    if not deal: raise HTTPException(404, "Deal not found")
    analysis = deep_financial_analysis.generate_deep_financial_analysis(db, deal_id)
    deep_financial_analysis.store_financial_analysis(db, deal_id, analysis)
    return analysis

@app.get("/api/deals/{deal_id}/export/proforma.csv")
def export_proforma_csv(deal_id: int, db: Session = Depends(get_db)):
    """Export pro forma template as CSV for Excel"""
    deal = crud.get_deal(db, deal_id)
    if not deal: raise HTTPException(404, "Deal not found")
    csv_content = deep_financial_analysis.generate_proforma_template(db, deal_id)
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=deal_{deal_id}_proforma.csv"}
    )

@app.post("/api/deals/{deal_id}/comprehensive-analysis")
def run_comprehensive_analysis(deal_id: int, db: Session = Depends(get_db)):
    """Run complete enhanced analysis: market analysis, property research, deep financials, risks, scorecard"""
    import traceback
    deal = crud.get_deal(db, deal_id)
    if not deal: raise HTTPException(404, "Deal not found")

    results = {"deal_id": deal_id, "steps": []}

    # Step 1: Document analysis
    try:
        analysis_job = analysis_pipeline.start_deal_analysis(db, deal_id)
        results["steps"].append({
            "step": "document_analysis",
            "job_id": analysis_job.id,
            "status": "started"
        })
    except Exception as e:
        results["steps"].append({"step": "document_analysis", "status": "error", "error": str(e)})

    # Step 2: Market analysis
    try:
        mkt_analysis = market_analysis.generate_market_analysis(db, deal_id)
        market_analysis.store_market_analysis(db, deal_id, mkt_analysis)
        results["steps"].append({
            "step": "market_analysis",
            "status": "completed",
            "regulatory_environment": mkt_analysis.get("regulatory_environment", {}).get("regulatory_agency")
        })
    except Exception as e:
        results["steps"].append({"step": "market_analysis", "status": "error", "error": str(e)})

    # Step 3: Property research
    try:
        prop_research = property_research.research_deal_properties(db, deal_id)
        property_research.store_property_research(db, deal_id, prop_research)
        results["steps"].append({
            "step": "property_research",
            "status": "completed",
            "properties_found_in_cms": prop_research.get("summary", {}).get("properties_found_in_cms", 0),
            "high_risk_properties": prop_research.get("summary", {}).get("high_risk_properties", 0)
        })
    except Exception as e:
        results["steps"].append({"step": "property_research", "status": "error", "error": str(e)})

    # Step 4: Deep financial analysis
    try:
        fin_analysis = deep_financial_analysis.generate_deep_financial_analysis(db, deal_id)
        deep_financial_analysis.store_financial_analysis(db, deal_id, fin_analysis)
        results["steps"].append({
            "step": "deep_financial_analysis",
            "status": "completed",
            "ebitdar_margin": fin_analysis.get("summary", {}).get("ebitdar_margin"),
            "opportunities": len(fin_analysis.get("opportunities", []))
        })
    except Exception as e:
        results["steps"].append({"step": "deep_financial_analysis", "status": "error", "error": str(e)})

    # Step 5: Verify claims
    try:
        claims_updated = om_scrubber.verify_claims_against_evidence(db, deal_id)
        results["steps"].append({
            "step": "claim_verification",
            "claims_updated": claims_updated
        })
    except Exception as e:
        results["steps"].append({"step": "claim_verification", "status": "error", "error": str(e)})

    # Step 6: Detect risks
    try:
        risks_created = risk_scoring.create_risk_flags_for_deal(db, deal_id)
        results["steps"].append({
            "step": "risk_detection",
            "flags_created": risks_created
        })
    except Exception as e:
        results["steps"].append({"step": "risk_detection", "status": "error", "error": str(e)})

    # Step 7: Calculate scorecard
    try:
        scorecard = risk_scoring.calculate_deal_scorecard(db, deal_id)
        results["steps"].append({
            "step": "scorecard",
            "overall_score": scorecard.overall_score,
            "recommendation": scorecard.recommendation
        })
    except Exception as e:
        results["steps"].append({"step": "scorecard", "status": "error", "error": str(e)})

    return results


# ============================================================================
# WELCOME NIGHTS PRESENTATION BUILDER ENDPOINTS
# ============================================================================

# Welcome Nights asset upload directory
WN_UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "wn_uploads")
os.makedirs(WN_UPLOAD_DIR, exist_ok=True)
app.mount("/wn_uploads", StaticFiles(directory=WN_UPLOAD_DIR), name="wn_uploads")


# Brand endpoints
@app.get("/api/wn/brands", response_model=List[schemas.BrandResponse])
def get_brands(db: Session = Depends(get_db)):
    """Get all brands"""
    return crud.get_brands(db)


@app.get("/api/wn/brands/{brand_id}", response_model=schemas.BrandResponse)
def get_brand(brand_id: int, db: Session = Depends(get_db)):
    """Get a brand by ID"""
    brand = crud.get_brand(db, brand_id)
    if not brand:
        raise HTTPException(404, "Brand not found")
    return brand


@app.post("/api/wn/brands", response_model=schemas.BrandResponse)
def create_brand(brand: schemas.BrandCreate, db: Session = Depends(get_db)):
    """Create a new brand (admin only)"""
    return crud.create_brand(db, brand)


@app.put("/api/wn/brands/{brand_id}", response_model=schemas.BrandResponse)
def update_brand(brand_id: int, brand: schemas.BrandUpdate, db: Session = Depends(get_db)):
    """Update a brand (admin only)"""
    b = crud.update_brand(db, brand_id, brand)
    if not b:
        raise HTTPException(404, "Brand not found")
    return b


# Facility endpoints
@app.get("/api/wn/facilities", response_model=List[schemas.WNFacilityResponse])
def get_facilities(brand_id: Optional[int] = None, search: Optional[str] = None, db: Session = Depends(get_db)):
    """Get facilities, optionally filtered by brand"""
    return crud.get_wn_facilities(db, brand_id, search)


@app.get("/api/wn/facilities/{facility_id}", response_model=schemas.WNFacilityResponse)
def get_facility(facility_id: int, db: Session = Depends(get_db)):
    """Get a facility by ID"""
    facility = crud.get_wn_facility(db, facility_id)
    if not facility:
        raise HTTPException(404, "Facility not found")
    return facility


@app.post("/api/wn/facilities", response_model=schemas.WNFacilityResponse)
def create_facility(facility: schemas.WNFacilityCreate, db: Session = Depends(get_db)):
    """Create a new facility (admin only)"""
    return crud.create_wn_facility(db, facility)


@app.put("/api/wn/facilities/{facility_id}", response_model=schemas.WNFacilityResponse)
def update_facility(facility_id: int, facility: schemas.WNFacilityUpdate, db: Session = Depends(get_db)):
    """Update a facility (admin only)"""
    f = crud.update_wn_facility(db, facility_id, facility)
    if not f:
        raise HTTPException(404, "Facility not found")
    return f


@app.delete("/api/wn/facilities/{facility_id}")
def delete_facility(facility_id: int, db: Session = Depends(get_db)):
    """Delete a facility (admin only)"""
    if not crud.delete_wn_facility(db, facility_id):
        raise HTTPException(404, "Facility not found")
    return {"message": "Deleted"}


# Asset endpoints
@app.get("/api/wn/assets", response_model=List[schemas.WNAssetResponse])
def get_assets(brand_id: Optional[int] = None, asset_type: Optional[str] = None, db: Session = Depends(get_db)):
    """Get assets, optionally filtered by brand and type"""
    return crud.get_wn_assets(db, brand_id, asset_type)


@app.post("/api/wn/assets")
async def upload_asset(
    brand_id: int = Form(...),
    asset_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload an asset (logo, background, etc.)"""
    ext = file.filename.split(".")[-1].lower()
    if ext not in {"png", "jpg", "jpeg", "gif", "svg", "webp"}:
        raise HTTPException(400, "Invalid file type. Supported: png, jpg, jpeg, gif, svg, webp")

    content = await file.read()
    fname = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
    file_path = os.path.join(WN_UPLOAD_DIR, fname)

    with open(file_path, "wb") as f:
        f.write(content)

    asset = crud.create_wn_asset(db, schemas.WNAssetCreate(
        brand_id=brand_id,
        asset_type=asset_type,
        filename=fname,
        original_filename=file.filename,
        url=f"/wn_uploads/{fname}",
        mime_type=file.content_type,
        file_size=len(content)
    ))

    return {"message": "Uploaded", "asset": asset}


@app.delete("/api/wn/assets/{asset_id}")
def delete_asset(asset_id: int, db: Session = Depends(get_db)):
    """Delete an asset"""
    asset = crud.get_wn_asset(db, asset_id)
    if not asset:
        raise HTTPException(404, "Asset not found")
    try:
        os.remove(os.path.join(WN_UPLOAD_DIR, asset.filename))
    except:
        pass
    crud.delete_wn_asset(db, asset_id)
    return {"message": "Deleted"}


# Agenda Template endpoints
@app.get("/api/wn/agenda-templates", response_model=List[schemas.AgendaTemplateResponse])
def get_agenda_templates(brand_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Get agenda templates, optionally filtered by brand"""
    return crud.get_agenda_templates(db, brand_id)


@app.get("/api/wn/agenda-templates/{template_id}", response_model=schemas.AgendaTemplateResponse)
def get_agenda_template(template_id: int, db: Session = Depends(get_db)):
    """Get an agenda template by ID"""
    template = crud.get_agenda_template(db, template_id)
    if not template:
        raise HTTPException(404, "Template not found")
    return template


@app.post("/api/wn/agenda-templates", response_model=schemas.AgendaTemplateResponse)
def create_agenda_template(template: schemas.AgendaTemplateCreate, db: Session = Depends(get_db)):
    """Create a new agenda template (admin only)"""
    return crud.create_agenda_template(db, template)


@app.put("/api/wn/agenda-templates/{template_id}", response_model=schemas.AgendaTemplateResponse)
def update_agenda_template(template_id: int, template: schemas.AgendaTemplateUpdate, db: Session = Depends(get_db)):
    """Update an agenda template (admin only)"""
    t = crud.update_agenda_template(db, template_id, template)
    if not t:
        raise HTTPException(404, "Template not found")
    return t


@app.delete("/api/wn/agenda-templates/{template_id}")
def delete_agenda_template(template_id: int, db: Session = Depends(get_db)):
    """Delete an agenda template (admin only)"""
    if not crud.delete_agenda_template(db, template_id):
        raise HTTPException(404, "Template not found")
    return {"message": "Deleted"}


# Reusable Content endpoints
@app.get("/api/wn/content", response_model=List[schemas.ReusableContentResponse])
def get_reusable_content(brand_id: int, content_key: Optional[str] = None, db: Session = Depends(get_db)):
    """Get reusable content for a brand"""
    return crud.get_reusable_content(db, brand_id, content_key)


@app.get("/api/wn/content/{content_id}", response_model=schemas.ReusableContentResponse)
def get_reusable_content_item(content_id: int, db: Session = Depends(get_db)):
    """Get a reusable content item by ID"""
    content = crud.get_reusable_content_item(db, content_id)
    if not content:
        raise HTTPException(404, "Content not found")
    return content


@app.post("/api/wn/content", response_model=schemas.ReusableContentResponse)
def create_reusable_content(content: schemas.ReusableContentCreate, db: Session = Depends(get_db)):
    """Create a new reusable content item (admin only)"""
    return crud.create_reusable_content(db, content)


@app.put("/api/wn/content/{content_id}", response_model=schemas.ReusableContentResponse)
def update_reusable_content(content_id: int, content: schemas.ReusableContentUpdate, db: Session = Depends(get_db)):
    """Update a reusable content item (admin only)"""
    c = crud.update_reusable_content(db, content_id, content)
    if not c:
        raise HTTPException(404, "Content not found")
    return c


# Game endpoints
@app.get("/api/wn/games", response_model=List[schemas.GameResponse])
def get_games(brand_id: Optional[int] = None, game_type: Optional[str] = None, db: Session = Depends(get_db)):
    """Get games, optionally filtered by brand and type"""
    return crud.get_games(db, brand_id, game_type)


@app.get("/api/wn/games/{game_id}", response_model=schemas.GameResponse)
def get_game(game_id: int, db: Session = Depends(get_db)):
    """Get a game by ID"""
    game = crud.get_game(db, game_id)
    if not game:
        raise HTTPException(404, "Game not found")
    return game


@app.post("/api/wn/games", response_model=schemas.GameResponse)
def create_game(game: schemas.GameCreate, db: Session = Depends(get_db)):
    """Create a new game (admin only)"""
    return crud.create_game(db, game)


@app.put("/api/wn/games/{game_id}", response_model=schemas.GameResponse)
def update_game(game_id: int, game: schemas.GameUpdate, db: Session = Depends(get_db)):
    """Update a game (admin only)"""
    g = crud.update_game(db, game_id, game)
    if not g:
        raise HTTPException(404, "Game not found")
    return g


@app.delete("/api/wn/games/{game_id}")
def delete_game(game_id: int, db: Session = Depends(get_db)):
    """Delete a game (admin only)"""
    if not crud.delete_game(db, game_id):
        raise HTTPException(404, "Game not found")
    return {"message": "Deleted"}


# Presentation endpoints
@app.get("/api/wn/presentations", response_model=List[schemas.PresentationResponse])
def get_presentations(
    brand_id: Optional[int] = None,
    facility_id: Optional[int] = None,
    search: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get presentations with optional filters"""
    return crud.get_presentations(db, brand_id, facility_id, search, status)


@app.get("/api/wn/presentations/{presentation_id}", response_model=schemas.PresentationDetailResponse)
def get_presentation(presentation_id: int, db: Session = Depends(get_db)):
    """Get a presentation by ID with all slides"""
    presentation = crud.get_presentation(db, presentation_id)
    if not presentation:
        raise HTTPException(404, "Presentation not found")
    return presentation


@app.post("/api/wn/presentations", response_model=schemas.PresentationResponse)
def create_presentation(presentation: schemas.PresentationCreate, db: Session = Depends(get_db)):
    """Create a new presentation"""
    return crud.create_presentation(db, presentation)


@app.put("/api/wn/presentations/{presentation_id}", response_model=schemas.PresentationResponse)
def update_presentation(presentation_id: int, presentation: schemas.PresentationUpdate, db: Session = Depends(get_db)):
    """Update a presentation"""
    p = crud.update_presentation(db, presentation_id, presentation)
    if not p:
        raise HTTPException(404, "Presentation not found")
    return p


@app.delete("/api/wn/presentations/{presentation_id}")
def delete_presentation(presentation_id: int, db: Session = Depends(get_db)):
    """Delete a presentation"""
    if not crud.delete_presentation(db, presentation_id):
        raise HTTPException(404, "Presentation not found")
    return {"message": "Deleted"}


# Build slides endpoint
@app.post("/api/wn/presentations/{presentation_id}/build-slides", response_model=schemas.BuildSlidesResponse)
def build_presentation_slides(presentation_id: int, request: schemas.BuildSlidesRequest, db: Session = Depends(get_db)):
    """(Re)build slide instances for a presentation from config"""
    try:
        config = request.model_dump()
        slides = slide_builder.build_slides(db, presentation_id, config)
        return {
            "presentation_id": presentation_id,
            "slides_created": len(slides),
            "slide_types": [s["slide_type"] for s in slides]
        }
    except ValueError as e:
        raise HTTPException(400, str(e))


# Get slides for presentation
@app.get("/api/wn/presentations/{presentation_id}/slides", response_model=List[schemas.PresentationSlideInstanceResponse])
def get_presentation_slides(presentation_id: int, db: Session = Depends(get_db)):
    """Get all slides for a presentation in order"""
    return crud.get_presentation_slides(db, presentation_id)


# Present mode data endpoint (returns all data needed for present mode)
@app.get("/api/wn/presentations/{presentation_id}/present")
def get_presentation_present_data(presentation_id: int, db: Session = Depends(get_db)):
    """Get all data needed for present mode"""
    presentation = crud.get_presentation(db, presentation_id)
    if not presentation:
        raise HTTPException(404, "Presentation not found")

    brand = crud.get_brand(db, presentation.brand_id)
    facility = crud.get_wn_facility(db, presentation.facility_id)
    slides = crud.get_presentation_slides(db, presentation_id)

    return {
        "presentation": {
            "id": presentation.id,
            "title": presentation.title,
            "status": presentation.status,
            "config": presentation.config,
        },
        "brand": {
            "id": brand.id,
            "name": brand.name,
            "slug": brand.slug,
            "primary_color": brand.primary_color,
            "secondary_color": brand.secondary_color,
            "font_family": brand.font_family,
            "logo_url": brand.logo_url,
        },
        "facility": {
            "id": facility.id,
            "name": facility.name,
            "city": facility.city,
            "state": facility.state,
        },
        "slides": [
            {
                "id": s.id,
                "order": s.order,
                "slide_type": s.slide_type,
                "payload": s.payload,
                "notes": s.notes,
            }
            for s in slides
        ],
        "total_slides": len(slides),
    }


# Export endpoints
@app.get("/api/wn/presentations/{presentation_id}/export/pptx")
def export_presentation_pptx(presentation_id: int, db: Session = Depends(get_db)):
    """Export presentation to PPTX"""
    presentation = crud.get_presentation(db, presentation_id)
    if not presentation:
        raise HTTPException(404, "Presentation not found")

    try:
        pptx_bytes = presentation_export.export_to_pptx(db, presentation_id)
        filename = presentation_export.get_export_filename(presentation, "pptx")
        return Response(
            content=pptx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(500, f"Export failed: {str(e)}")


@app.get("/api/wn/presentations/{presentation_id}/export/pdf")
def export_presentation_pdf(presentation_id: int, db: Session = Depends(get_db)):
    """Export presentation to PDF"""
    presentation = crud.get_presentation(db, presentation_id)
    if not presentation:
        raise HTTPException(404, "Presentation not found")

    try:
        pdf_bytes = presentation_export.export_to_pdf(db, presentation_id)
        filename = presentation_export.get_export_filename(presentation, "pdf")
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(500, f"Export failed: {str(e)}")


# Mark presentation as presented
@app.post("/api/wn/presentations/{presentation_id}/mark-presented")
def mark_presentation_presented(presentation_id: int, db: Session = Depends(get_db)):
    """Mark a presentation as presented"""
    presentation = crud.get_presentation(db, presentation_id)
    if not presentation:
        raise HTTPException(404, "Presentation not found")

    presentation.status = "presented"
    presentation.presented_at = datetime.utcnow()
    db.commit()
    db.refresh(presentation)
    return {"message": "Marked as presented", "presented_at": presentation.presented_at}


# Serve frontend for non-API routes (must be at the end)
@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    """Serve the React frontend for all non-API routes"""
    if os.path.exists(STATIC_DIR):
        index_path = os.path.join(STATIC_DIR, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
    raise HTTPException(404, "Not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
