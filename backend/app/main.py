from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
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
async def upload_doc(deal_id: int, file: UploadFile = File(...), category: str = Form("other"), db: Session = Depends(get_db)):
    ext = file.filename.split(".")[-1].lower()
    if ext not in {"pdf", "docx", "xlsx", "csv", "png", "jpg"}: raise HTTPException(400, "Invalid type")
    fname = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
    with open(os.path.join(UPLOAD_DIR, fname), "wb") as f:
        content = await file.read()
        f.write(content)
    doc = crud.create_document(db, deal_id, schemas.DocumentCreate(filename=fname, original_filename=file.filename, file_type=ext, file_size=len(content), category=category))
    return {"message": "Uploaded", "document": doc}

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
