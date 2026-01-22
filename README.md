# SNFalyze Deal Tracker

Professional deal management platform for skilled nursing facility (SNF) acquisitions.

## Features

- **CMS Facility Search** - Search 15,000+ SNF facilities from CMS Medicare data with star ratings, beds, occupancy
- **Pipeline Kanban Board** - Visual deal pipeline (Vetting → Pipeline → Due Diligence → Current Ops)
- **Document Analysis** - Upload PDFs, Word docs, Excel files with intelligent metric extraction
- **Property Portfolios** - Track multiple facilities in a single deal
- **Valuation Calculator** - Income approach (cap rate) and market approach ($/bed) analysis
- **Task Management** - Track due diligence tasks per deal
- **Activity Logging** - Full audit trail of deal changes

## Quick Start (Local Development)

```bash
# Install dependencies
cd frontend && npm install
cd ../backend && pip install -r requirements.txt

# Start servers
./start.sh
```

Opens http://localhost:5173

## Deploy to Railway

1. Push code to GitHub:
```bash
git remote add origin https://github.com/YOUR_USERNAME/snfalyze.git
git push -u origin main
```

2. Go to [Railway](https://railway.app) and create a new project
3. Select "Deploy from GitHub repo"
4. Choose your `snfalyze` repository
5. Railway will auto-detect the configuration and deploy

Your app will be live at `https://your-app.up.railway.app`

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy, SQLite
- **Frontend**: React 18, Vite, React Router
- **Styling**: Custom CSS (Cascadia HC-inspired teal theme)
- **Data**: CMS Medicare Provider Database

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/facilities/search?q=name` | Search CMS facilities |
| `GET /api/deals` | List all deals |
| `POST /api/deals` | Create new deal |
| `GET /api/deals/:id` | Get deal details |
| `POST /api/deals/:id/documents` | Upload document |
| `POST /api/documents/:id/analyze` | Analyze document |
| `GET /api/deals/:id/valuation` | Calculate valuation |

## License

MIT
