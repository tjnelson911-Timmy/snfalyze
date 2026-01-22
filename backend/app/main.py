from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import os, re
from datetime import datetime
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
