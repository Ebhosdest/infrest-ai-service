# Claude Code — Prompts for This Project

## How to Use Claude Code Efficiently (Save Credits)

Three rules:
1. Give context ONCE at the start of each session, then ask specific questions
2. Never ask Claude Code to "rewrite" entire files — ask it to fix specific issues
3. Use /compact to compress the conversation when it gets long

---

## FIRST: The Context Prompt (Use This Once When You Start)

Paste this ONCE when you open Claude Code for the project:

```
Read the project structure in this repo. This is a Python FastAPI backend
for an AI-powered ERP assistant called "Infrest Copilot". It uses OpenAI
GPT-4o with function/tool calling to answer questions about ERP data.
The database is PostgreSQL with demo data already loaded. The key files are:
- app/main.py (FastAPI entry point)
- app/services/copilot.py (orchestration logic)
- app/services/llm_client.py (OpenAI integration)
- app/services/erp_client.py (database queries)
- app/services/report_engine.py (NLP to SQL)
- app/services/tool_registry.py (tool definitions)

Don't rewrite files unless I ask. Just answer my questions or fix what I point to.
```

---

## Debugging Prompts (When Things Break)

### If the server won't start:
```
The server throws this error when I run uvicorn: [paste the error]
Fix only the file causing the error.
```

### If a database query fails:
```
The query in erp_client.py method get_sales_summary throws: [paste error]
The table schema is in database/sql/01_schema.sql. Fix the query.
```

### If OpenAI returns unexpected results:
```
When I send "What is my cash balance?" to /api/copilot/chat, the LLM
is not calling the get_cash_balance tool. Check the tool definition in
tool_registry.py and the system prompt in llm_client.py. What's wrong?
```

---

## Adding New Features (Specific Prompts)

### Add a new tool for the Copilot:
```
Add a new tool called "get_budget_vs_actual" to tool_registry.py
that compares project budgets against actual costs. Then add the
handler in erp_client.py and wire it up in copilot.py.
The projects table has: budget, actual_cost, project_name, status columns.
```

### Add Keycloak authentication:
```
Add JWT token validation middleware to this FastAPI app. The Keycloak
server is at http://localhost:8080, realm is "infrest". Create the
middleware in app/security/auth.py and apply it to all /api/* routes.
Use python-jose to verify the JWT.
```

### Add rate limiting:
```
Add rate limiting to the chat and reports endpoints. Max 15 requests
per minute per session_id. Use an in-memory dict for now (we'll
switch to Redis later). Add it as FastAPI middleware.
```

### Add a new report table to the allow-list:
```
In report_engine.py, add the "stock_movements" table to ALLOWED_TABLES.
Include columns: item_name, warehouse_id, movement_date, movement_type, quantity.
It can join with warehouses on stock_movements.warehouse_id = warehouses.id.
```

---

## Testing Prompts

### Write a test for the copilot:
```
Write a pytest test in tests/test_copilot.py that:
1. Mocks the OpenAI API response to return a tool_use for get_cash_balance
2. Mocks the database to return test data
3. Verifies the copilot returns a proper ChatResponse
Keep it simple, just one test function.
```

### Test the NLP report engine:
```
Write a pytest test for the report_engine._validate_parsed_query function.
Test that it rejects invalid table names, invalid columns, and invalid operators.
Test that it accepts a valid parsed query for the sales_orders table.
```

---

## Optimisation Prompts (When It's Working But Slow)

### Reduce OpenAI token usage:
```
The system prompt in llm_client.py is using too many tokens.
Shorten it without losing important context. Keep the route list
but compress everything else. Show me only the changed SYSTEM_PROMPT string.
```

### Speed up database queries:
```
The get_financial_summary query in erp_client.py is slow.
Suggest indexes to add to the general_ledger table and optimise the query.
Show me the CREATE INDEX statements and the updated query.
```

---

## Commands You Should Know

```bash
# Start fresh (if Docker containers are messed up)
docker compose down -v && docker compose up -d

# Check if database has data
docker exec infrest-db psql -U infrest -d infrest_erp -c "SELECT COUNT(*) FROM customers;"

# Watch server logs in real-time
uvicorn app.main:app --port 8090 --reload --log-level debug

# Run tests
pytest tests/ -v

# Check your OpenAI usage
# Go to: platform.openai.com/usage
```

---

## What NOT to Ask Claude Code (Saves Credits)

- Don't ask it to explain the architecture — you already have the docs
- Don't ask it to refactor code that's already working
- Don't ask it to generate documentation — write it yourself
- Don't ask it to review the whole codebase — point to specific files
- Don't ask open-ended questions like "make this better"
