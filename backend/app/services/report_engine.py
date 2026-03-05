"""
NLP Report Engine.

Converts natural language questions into structured queries,
validates them, generates safe SQL, executes against a read-only
database connection, and returns formatted results.

Security approach:
- The LLM outputs a structured JSON definition, NOT raw SQL
- We validate every field against allow-lists of tables/columns
- We build parameterised SQL ourselves
- We execute against a read-only database connection
- Row limits are enforced
"""

import json
import time
import structlog
from openai import OpenAI
from app.config import get_settings
from app.database.connection import execute_readonly_query
from app.models.reports import (
    ReportQueryRequest, ReportQueryResponse, ParsedQuery, ChartType
)

settings = get_settings()
logger = structlog.get_logger()

# ─── ALLOW-LISTS ───
# Only these tables and columns can be queried.
# This is the primary security mechanism.

ALLOWED_TABLES = {
    "sales_orders": {
        "columns": [
            "id", "order_number", "customer_id", "order_date", "status",
            "subtotal", "vat_amount", "total_amount", "currency"
        ],
        "joins": {
            "customers": "sales_orders.customer_id = customers.id"
        },
        "description": "Sales orders with amounts and status",
    },
    "invoices": {
        "columns": [
            "id", "invoice_number", "customer_id", "invoice_date", "due_date",
            "subtotal", "vat_amount", "total_amount", "amount_paid", "payment_status"
        ],
        "joins": {
            "customers": "invoices.customer_id = customers.id"
        },
        "description": "Customer invoices with payment tracking",
    },
    "customers": {
        "columns": [
            "id", "customer_code", "company_name", "city", "state",
            "industry", "credit_limit", "status"
        ],
        "joins": {},
        "description": "Customer master data",
    },
    "vendors": {
        "columns": [
            "id", "vendor_code", "company_name", "city", "state",
            "category", "rating", "status"
        ],
        "joins": {},
        "description": "Vendor/supplier master data",
    },
    "purchase_orders": {
        "columns": [
            "id", "po_number", "vendor_id", "order_date", "status",
            "subtotal", "vat_amount", "total_amount"
        ],
        "joins": {
            "vendors": "purchase_orders.vendor_id = vendors.id"
        },
        "description": "Purchase orders to vendors",
    },
    "inventory_items": {
        "columns": [
            "id", "item_code", "item_name", "category", "unit_cost",
            "unit_price", "quantity_on_hand", "reorder_level"
        ],
        "joins": {},
        "description": "Product inventory catalogue",
    },
    "employees": {
        "columns": [
            "id", "employee_code", "first_name", "last_name",
            "department", "position", "annual_salary", "hire_date",
            "employment_type", "location", "status"
        ],
        "joins": {},
        "description": "Employee records",
    },
    "payroll": {
        "columns": [
            "id", "employee_id", "year", "month", "period",
            "gross_pay", "net_pay", "total_deductions",
            "pension_employee", "tax_paye"
        ],
        "joins": {
            "employees": "payroll.employee_id = employees.id"
        },
        "description": "Monthly payroll records",
    },
    "projects": {
        "columns": [
            "id", "project_code", "project_name", "department",
            "start_date", "end_date", "budget", "actual_cost",
            "completion_percentage", "status"
        ],
        "joins": {},
        "description": "Project tracking with budgets",
    },
    "fixed_assets": {
        "columns": [
            "id", "asset_code", "asset_name", "category", "purchase_date",
            "purchase_cost", "useful_life_years", "annual_depreciation",
            "accumulated_depreciation", "net_book_value", "status",
            "assigned_department", "location"
        ],
        "joins": {},
        "description": "Fixed asset register",
    },
    "general_ledger": {
        "columns": [
            "id", "journal_ref", "entry_date", "account_code",
            "description", "debit_amount", "credit_amount", "status"
        ],
        "joins": {
            "chart_of_accounts": "general_ledger.account_code = chart_of_accounts.account_code"
        },
        "description": "General ledger journal entries",
    },
    "chart_of_accounts": {
        "columns": [
            "id", "account_code", "account_name", "account_type", "sub_type"
        ],
        "joins": {},
        "description": "Chart of accounts",
    },
    "leave_records": {
        "columns": [
            "id", "employee_id", "leave_type", "start_date",
            "end_date", "days_requested", "status"
        ],
        "joins": {
            "employees": "leave_records.employee_id = employees.id"
        },
        "description": "Employee leave requests",
    },
    "stock_movements": {
        "columns": [
            "id", "item_id", "item_name", "warehouse_id",
            "movement_date", "movement_type", "quantity"
        ],
        "joins": {
            "warehouses": "stock_movements.warehouse_id = warehouses.id"
        },
        "description": "Stock movement records",
    },
    "ar_aging": {
        "columns": [
            "id", "invoice_id", "customer_id", "invoice_date",
            "due_date", "outstanding_amount", "days_outstanding", "aging_bucket"
        ],
        "joins": {
            "customers": "ar_aging.customer_id = customers.id"
        },
        "description": "Accounts receivable aging",
    },
    "ap_aging": {
        "columns": [
            "id", "po_id", "vendor_id", "po_date",
            "outstanding_amount", "days_outstanding", "aging_bucket"
        ],
        "joins": {
            "vendors": "ap_aging.vendor_id = vendors.id"
        },
        "description": "Accounts payable aging",
    },
}

ALLOWED_AGGREGATIONS = ["SUM", "AVG", "COUNT", "MIN", "MAX"]

# ─── QUERY PARSING PROMPT ───

PARSE_PROMPT = """You are a query parser for an ERP system. Given a natural language question, extract a structured query definition as JSON.

AVAILABLE TABLES:
{tables}

RULES:
- Output ONLY valid JSON, no other text
- source_table must be one of the available tables
- measures must use columns that exist in the source table
- aggregation must be one of: SUM, AVG, COUNT, MIN, MAX
- dimensions must be valid column names
- filters must use valid column names and operators (=, !=, >, <, >=, <=, LIKE, IN, BETWEEN)
- For date filters, use ISO format (YYYY-MM-DD)
- limit must be between 1 and 10000

CRITICAL — TIME GROUPING:
When the user asks for data "by month", "by quarter", "by year", or "monthly", "quarterly", "yearly":
- Do NOT use the raw date column as a dimension
- Instead, set "time_grouping" to the period: "month", "quarter", or "year"
- Set "time_column" to the date column to group by (e.g., "order_date", "entry_date", "invoice_date")
- Do NOT include the date column in "dimensions"

Examples:
- "revenue by month for 2025" → time_grouping: "month", time_column: "order_date", dimensions: []
- "sales by quarter" → time_grouping: "quarter", time_column: "order_date", dimensions: []
- "monthly payroll" → time_grouping: "month", time_column: "payment_date", dimensions: []
- "customers by industry" → no time_grouping, dimensions: ["industry"]

OUTPUT FORMAT:
{{
  "source_table": "table_name",
  "measures": [{{"column": "col_name", "aggregation": "SUM", "alias": "total_x"}}],
  "dimensions": ["col1", "col2"],
  "filters": [{{"column": "col", "operator": ">=", "value": "2025-01-01"}}],
  "order_by": {{"column": "alias_or_col", "direction": "DESC"}},
  "limit": 100,
  "time_grouping": null,
  "time_column": null,
  "interpretation": "Human-readable summary of what this query does",
  "joins": ["table_to_join"]
}}
"""


def _build_table_descriptions() -> str:
    lines = []
    for table, config in ALLOWED_TABLES.items():
        cols = ", ".join(config["columns"])
        lines.append(f"- {table}: {config['description']}. Columns: {cols}")
    return "\n".join(lines)


def _select_chart_type(parsed: dict) -> ChartType:
    """Pick the best chart type based on query structure."""
    dims = parsed.get("dimensions", [])
    measures = parsed.get("measures", [])
    time_grouping = parsed.get("time_grouping")

    # Time-based grouping → line chart
    if time_grouping:
        return ChartType.LINE

    # Time-based dimension → line chart
    time_cols = ["entry_date", "order_date", "invoice_date", "movement_date",
                 "hire_date", "purchase_date", "start_date", "year", "month", "period"]
    if any(d in time_cols for d in dims):
        return ChartType.LINE

    # Single measure with categories → bar chart
    if len(measures) == 1 and len(dims) == 1:
        return ChartType.BAR

    # Multiple measures → grouped bar
    if len(measures) > 1:
        return ChartType.GROUPED_BAR

    # Part-of-whole (status, category breakdowns)
    part_cols = ["status", "category", "aging_bucket", "leave_type", "department",
                 "account_type", "industry", "movement_type"]
    if any(d in part_cols for d in dims):
        return ChartType.PIE

    return ChartType.BAR


def _validate_parsed_query(parsed: dict) -> list[str]:
    """Validate the parsed query against allow-lists. Returns list of errors."""
    errors = []

    table = parsed.get("source_table", "")
    if table not in ALLOWED_TABLES:
        errors.append(f"Table '{table}' is not available for querying")
        return errors

    table_config = ALLOWED_TABLES[table]
    valid_cols = set(table_config["columns"])

    # Validate time_column if present
    time_column = parsed.get("time_column")
    if time_column and time_column not in valid_cols:
        errors.append(f"Time column '{time_column}' not found in {table}")

    # Validate time_grouping
    time_grouping = parsed.get("time_grouping")
    if time_grouping and time_grouping not in ("month", "quarter", "year"):
        errors.append(f"Time grouping '{time_grouping}' must be month, quarter, or year")

    # Check join tables and add their columns
    for join_table in parsed.get("joins", []):
        if join_table in ALLOWED_TABLES and join_table in table_config.get("joins", {}):
            valid_cols.update(ALLOWED_TABLES[join_table]["columns"])
        elif join_table not in table_config.get("joins", {}):
            errors.append(f"Cannot join '{table}' with '{join_table}'")

    # Validate measures
    for m in parsed.get("measures", []):
        if m.get("aggregation", "").upper() not in ALLOWED_AGGREGATIONS:
            errors.append(f"Aggregation '{m.get('aggregation')}' is not allowed")
        if m.get("column") != "*" and m.get("column") not in valid_cols:
            errors.append(f"Column '{m.get('column')}' not found in {table}")

    # Validate dimensions
    for d in parsed.get("dimensions", []):
        if d not in valid_cols:
            errors.append(f"Dimension '{d}' not found in {table}")

    # Validate filters
    allowed_operators = {"=", "!=", ">", "<", ">=", "<=", "LIKE", "IN", "BETWEEN"}
    for f in parsed.get("filters", []):
        if f.get("column") not in valid_cols:
            errors.append(f"Filter column '{f.get('column')}' not found in {table}")
        if f.get("operator", "").upper() not in allowed_operators:
            errors.append(f"Operator '{f.get('operator')}' is not allowed")

    return errors


def _build_sql(parsed: dict) -> tuple[str, dict]:
    """
    Build a safe, parameterised SQL query from validated parsed structure.
    Returns (sql_string, params_dict).
    """
    table = parsed["source_table"]
    table_config = ALLOWED_TABLES[table]
    params = {}
    param_counter = 0

    # Handle time grouping (monthly, quarterly, yearly)
    time_grouping = parsed.get("time_grouping")
    time_column = parsed.get("time_column")
    time_expr = None

    if time_grouping and time_column:
        # Validate time_column exists
        if time_column in table_config["columns"]:
            period_map = {"month": "month", "quarter": "quarter", "year": "year"}
            pg_period = period_map.get(time_grouping, "month")
            time_expr = f"DATE_TRUNC('{pg_period}', {time_column})"

    # SELECT clause
    select_parts = []

    if time_expr:
        select_parts.append(f"{time_expr} AS period")

    for dim in parsed.get("dimensions", []):
        select_parts.append(dim)

    for m in parsed.get("measures", []):
        agg = m["aggregation"].upper()
        col = m["column"]
        alias = m.get("alias", f"{agg.lower()}_{col}")
        if col == "*":
            select_parts.append(f"{agg}(*) AS {alias}")
        else:
            select_parts.append(f"{agg}({col}) AS {alias}")

    if not select_parts:
        select_parts = ["*"]

    # FROM clause with JOINs
    from_clause = table
    for join_table in parsed.get("joins", []):
        if join_table in table_config.get("joins", {}):
            join_condition = table_config["joins"][join_table]
            from_clause += f" JOIN {join_table} ON {join_condition}"

    # WHERE clause
    where_parts = []
    for f in parsed.get("filters", []):
        param_counter += 1
        param_name = f"p{param_counter}"
        col = f["column"]
        op = f["operator"].upper()

        if op == "LIKE":
            where_parts.append(f"{col} LIKE :{param_name}")
            params[param_name] = f"%{f['value']}%"
        elif op == "IN":
            # For IN, we need to handle list values
            vals = f["value"] if isinstance(f["value"], list) else [f["value"]]
            placeholders = []
            for i, v in enumerate(vals):
                pn = f"{param_name}_{i}"
                placeholders.append(f":{pn}")
                params[pn] = v
            where_parts.append(f"{col} IN ({', '.join(placeholders)})")
        else:
            where_parts.append(f"{col} {op} :{param_name}")
            params[param_name] = f["value"]

    # GROUP BY
    group_by = ""
    group_parts = []
    if time_expr:
        group_parts.append(time_expr)
    if parsed.get("dimensions"):
        group_parts.extend(parsed["dimensions"])
    if group_parts:
        group_by = "GROUP BY " + ", ".join(group_parts)

    # ORDER BY
    order_by = ""
    if time_expr:
        order_by = "ORDER BY period ASC"
    elif parsed.get("order_by"):
        ob = parsed["order_by"]
        direction = ob.get("direction", "DESC").upper()
        if direction not in ("ASC", "DESC"):
            direction = "DESC"
        order_by = f"ORDER BY {ob['column']} {direction}"

    # LIMIT
    limit = min(parsed.get("limit", 100), 10000)

    # Assemble
    sql = f"SELECT {', '.join(select_parts)} FROM {from_clause}"
    if where_parts:
        sql += f" WHERE {' AND '.join(where_parts)}"
    if group_by:
        sql += f" {group_by}"
    if order_by:
        sql += f" {order_by}"
    sql += f" LIMIT {limit}"

    return sql, params


def _generate_refinements(parsed: dict, query: str) -> list[str]:
    """Suggest follow-up queries based on the current one."""
    suggestions = []
    table = parsed.get("source_table", "")

    # Time-based suggestions
    if any("date" in f.get("column", "") for f in parsed.get("filters", [])):
        suggestions.append("Show the same data for the previous period")

    # Drill-down suggestions
    if parsed.get("dimensions"):
        suggestions.append(f"Break this down further by month")
        if "department" not in parsed["dimensions"]:
            suggestions.append("Add department breakdown")
        if "status" not in parsed["dimensions"]:
            suggestions.append("Group by status")

    # Metric alternatives
    if any(m.get("aggregation") == "SUM" for m in parsed.get("measures", [])):
        suggestions.append("Show averages instead of totals")

    # General
    suggestions.append("Export this data to Excel")

    return suggestions[:4]


class ReportEngine:
    """
    NLP Report Query Engine.

    Flow:
    1. User types natural language query
    2. GPT parses it into a structured definition
    3. We validate against allow-lists
    4. We build safe SQL
    5. Execute on read-only connection
    6. Format and return results
    """

    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)

    async def process_query(self, request: ReportQueryRequest) -> ReportQueryResponse:
        start_time = time.time()

        try:
            # Step 1: Parse natural language into structured query
            parsed = await self._parse_query(request.query, request.refinement_context)

            # Step 2: Validate against allow-lists
            errors = _validate_parsed_query(parsed)
            if errors:
                return ReportQueryResponse(
                    query_interpretation=f"I couldn't process that query: {'; '.join(errors)}",
                    columns=[],
                    rows=[],
                    total_rows=0,
                    chart_type=ChartType.BAR,
                    chart_config={},
                    processing_time_ms=int((time.time() - start_time) * 1000),
                )

            # Step 3: Build safe SQL
            sql, params = _build_sql(parsed)
            logger.info("report_sql_generated", sql=sql, params=params)

            # Step 4: Execute on read-only connection
            rows = await execute_readonly_query(sql, params)

            # Step 5: Format results
            columns = list(rows[0].keys()) if rows else []
            chart_type = _select_chart_type(parsed)

            # Build chart config
            chart_config = {
                "type": chart_type.value,
                "title": parsed.get("interpretation", request.query),
                "x_axis": parsed.get("dimensions", [None])[0] if parsed.get("dimensions") else None,
                "y_axis": [m.get("alias", m["column"]) for m in parsed.get("measures", [])],
            }

            # Convert rows to serialisable format
            serialised_rows = []
            for row in rows:
                serialised_rows.append({
                    k: float(v) if isinstance(v, (int, float)) and k != "id" else str(v)
                    for k, v in row.items()
                })

            return ReportQueryResponse(
                query_interpretation=parsed.get("interpretation", ""),
                columns=columns,
                rows=serialised_rows,
                total_rows=len(serialised_rows),
                chart_type=chart_type,
                chart_config=chart_config,
                sql_preview=sql if settings.debug else None,
                suggested_refinements=_generate_refinements(parsed, request.query),
                processing_time_ms=int((time.time() - start_time) * 1000),
            )

        except Exception as e:
            logger.error("report_engine_error", error=str(e), query=request.query)
            return ReportQueryResponse(
                query_interpretation=f"Something went wrong processing your query. Try rephrasing it.",
                columns=[],
                rows=[],
                total_rows=0,
                chart_type=ChartType.BAR,
                chart_config={},
                processing_time_ms=int((time.time() - start_time) * 1000),
            )

    async def _parse_query(self, query: str, refinement_context: str = None) -> dict:
        """Use GPT to parse natural language into structured query definition."""
        prompt = PARSE_PROMPT.format(tables=_build_table_descriptions())

        user_message = f"Query: {query}"
        if refinement_context:
            user_message = f"Previous query context: {refinement_context}\n\nNew query: {query}"

        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_message},
            ],
            max_tokens=1000,
            temperature=0.1,  # Very low for consistent structured output
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content
        parsed = json.loads(raw)

        logger.info("query_parsed", query=query, parsed=parsed)
        return parsed