#!/bin/bash
cd backend
[ ! -d venv ] && python3 -m venv venv
source venv/bin/activate
pip install -q fastapi uvicorn python-multipart sqlalchemy PyPDF2 pydantic
uvicorn app.main:app --reload --port 8000
