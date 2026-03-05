# Infrest ERP — AI Service

AI-powered Copilot and NLP Report Engine for Infrest ERP.

## What This Does

Two features:

1. **Infrest Copilot** — Chat endpoint that answers questions about ERP data, navigates users to modules, and provides guidance. Uses OpenAI GPT-4o with function/tool calling.

2. **NLP Report Query** — Natural language to structured report. Users type "Show me revenue by month for 2025" and get back formatted data with chart configuration.

## Prerequisites

Install these before starting:

- **Python 3.11+**: [python.org/downloads](https://python.org/downloads)
- **Docker Desktop**: [docker.com/products/docker-desktop](https://docker.com/products/docker-desktop)
- **OpenAI API Key**: [platform.openai.com/api-keys](https://platform.openai.com/api-keys)

## Setup — Run These Commands In Order

### Step 1: Start Database

Open a terminal in the project root folder:

```bash
docker compose up -d
```

This starts PostgreSQL and Redis. Wait 10 seconds for them to be ready.

### Step 2: Load Schema

```bash
docker exec -i infrest-db psql -U infrest -d infrest_erp < database/sql/01_schema.sql
```

### Step 3: Load Seed Data

**Mac/Linux:**
```bash
for file in database/seed/*.csv; do
  table=$(basename "$file" .csv)
  echo "Loading $table..."
  docker exec -i infrest-db psql -U infrest -d infrest_erp -c "\COPY $table FROM STDIN CSV HEADER" < "$file"
done
```

**Windows PowerShell:**
```powershell
Get-ChildItem database\seed\*.csv | ForEach-Object {
    $table = $_.BaseName
    Write-Host "Loading $table..."
    Get-Content $_.FullName | docker exec -i infrest-db psql -U infrest -d infrest_erp -c "\COPY $table FROM STDIN CSV HEADER"
}
```

### Step 4: Set Up Python Environment

```bash
cd backend
python3 -m venv venv
```

Activate it:
- **Mac/Linux:** `source venv/bin/activate`
- **Windows:** `venv\Scripts\activate`

Then install dependencies:
```bash
pip install -r requirements.txt
```

### Step 5: Add Your OpenAI Key

Edit `backend/.env` and replace `sk-your-openai-api-key-here` with your actual key.

### Step 6: Start the Server

```bash
uvicorn app.main:app --port 8090 --reload
```

### Step 7: Test It

Open your browser: **http://localhost:8090/docs**

This shows the Swagger UI with all endpoints. Try these:

**Test Copilot:**
POST `/api/copilot/chat` with body:
```json
{
  "message": "What is my current cash balance?",
  "session_id": "test-001"
}
```

**Test NLP Reports:**
POST `/api/reports/query` with body:
```json
{
  "query": "Show me top 10 customers by sales this year",
  "session_id": "test-001"
}
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/copilot/chat` | POST | Send a message to the Copilot |
| `/api/copilot/health` | GET | Health check |
| `/api/reports/query` | POST | NLP report query |
| `/api/reports/examples` | GET | Example queries |
| `/docs` | GET | Interactive API documentation |

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI entry point
│   ├── config.py            # Environment configuration
│   ├── models/
│   │   ├── chat.py          # Copilot request/response schemas
│   │   └── reports.py       # Report query schemas
│   ├── services/
│   │   ├── copilot.py       # Copilot orchestration (the brain)
│   │   ├── llm_client.py    # OpenAI GPT integration
│   │   ├── tool_registry.py # 20 tool definitions
│   │   ├── erp_client.py    # Database queries (simulates ERP APIs)
│   │   ├── navigation.py    # Route registry for ERP navigation
│   │   └── report_engine.py # NLP → SQL engine with security
│   ├── database/
│   │   └── connection.py    # PostgreSQL async connection
│   └── routes/
│       ├── chat.py          # /api/copilot/* endpoints
│       └── reports.py       # /api/reports/* endpoints
├── .env                     # Your configuration
└── requirements.txt
```

## How to Stop Everything

```bash
# Stop the Python server: Ctrl+C
# Stop Docker containers:
docker compose down
```

## For Frontend Engineers

The AI service exposes REST APIs that the frontend widget consumes. See `/docs` for the full API specification. The key contracts are:

- **Chat**: POST JSON to `/api/copilot/chat`, get structured response with `response_type` indicating how to render it
- **Navigation**: Responses with `response_type: "navigation"` include a `navigation.path` field — use your router to navigate there
- **Reports**: POST to `/api/reports/query`, get back `columns`, `rows`, `chart_type`, and `chart_config`
