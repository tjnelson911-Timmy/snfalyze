#!/bin/bash
echo "Starting SNFalyze..."
(cd backend && source venv/bin/activate 2>/dev/null || (python3 -m venv venv && source venv/bin/activate) && pip install -q fastapi uvicorn python-multipart sqlalchemy PyPDF2 pydantic && uvicorn app.main:app --reload --port 8000) &
sleep 2
(cd frontend && npm install -s && npm run dev) &
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:5173"
echo "Press Ctrl+C to stop"
wait
