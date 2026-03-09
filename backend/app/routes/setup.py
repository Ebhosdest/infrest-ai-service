"""
One-time database setup endpoints.
Creates tables and loads seed data on Render.
"""

from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from app.database.connection import async_session
import os
import csv
from datetime import date, datetime

router = APIRouter(prefix="/api/setup", tags=["setup"])


def convert_value(value, col_name):
    if value == "" or value is None:
        return None
    if col_name in ("is_active",):
        return value.lower() in ("true", "1", "yes")
    if col_name in ("needs_reorder",):
        return value.lower() in ("true", "1", "yes")
    if col_name in ("year", "month", "days_requested", "days_outstanding",
                     "quantity", "quantity_on_hand", "reorder_level",
                     "line_number", "capacity_sqm", "useful_life_years",
                     "completion_percentage", "payment_terms_days",
                     "rate_limit_per_minute", "total_rows"):
        return int(value)
    if col_name in ("order_date", "invoice_date", "due_date", "hire_date",
                     "purchase_date", "start_date", "end_date", "entry_date",
                     "request_date", "movement_date", "cost_date", "po_date",
                     "payment_date", "expected_delivery"):
        try:
            return date.fromisoformat(value[:10])
        except (ValueError, TypeError):
            return value
    if col_name in ("created_at", "timestamp"):
        try:
            return datetime.fromisoformat(value)
        except (ValueError, TypeError):
            return value
    if col_name in ("credit_limit", "annual_salary", "unit_cost", "unit_price",
                     "subtotal", "vat_amount", "total_amount", "amount_paid",
                     "debit_amount", "credit_amount", "net_amount",
                     "gross_pay", "net_pay", "total_deductions",
                     "pension_employee", "pension_employer", "tax_paye", "nhf",
                     "basic_salary", "housing_allowance", "transport_allowance",
                     "other_allowances", "line_total", "stock_value",
                     "purchase_cost", "annual_depreciation",
                     "accumulated_depreciation", "net_book_value",
                     "budget", "actual_cost", "amount", "outstanding_amount",
                     "rating", "avg_salary", "total_salary_cost",
                     "lifetime_revenue", "total_spend", "budget_utilisation"):
        try:
            return float(value)
        except (ValueError, TypeError):
            return value
    return value


@router.post("/create-tables")
async def create_tables():
    schema_path = os.path.join(os.path.dirname(__file__), "..", "..", "schema.sql")
    if not os.path.exists(schema_path):
        raise HTTPException(status_code=404, detail="schema.sql not found")
    with open(schema_path, "r") as f:
        schema_sql = f.read()
    async with async_session() as session:
        statements = [s.strip() for s in schema_sql.split(";") if s.strip()]
        for stmt in statements:
            if stmt:
                try:
                    await session.execute(text(stmt))
                except Exception as e:
                    print(f"Statement error (continuing): {e}")
        await session.commit()
    return {"status": "Tables created successfully"}


@router.post("/load-seed-data")
async def load_seed_data():
    seed_dir = os.path.join(os.path.dirname(__file__), "..", "..", "seed")
    if not os.path.exists(seed_dir):
        raise HTTPException(status_code=404, detail="seed directory not found")
    load_order = [
        "chart_of_accounts", "customers", "vendors", "employees",
        "inventory_items", "warehouses", "sales_orders", "sales_order_lines",
        "invoices", "purchase_requisitions", "purchase_orders",
        "purchase_order_lines", "general_ledger", "fixed_assets",
        "leave_records", "payroll", "projects", "project_costs",
        "stock_movements", "ar_aging", "ap_aging"
    ]
    results = {}
    for table in load_order:
        csv_path = os.path.join(seed_dir, f"{table}.csv")
        if not os.path.exists(csv_path):
            results[table] = "file not found"
            continue
        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                headers = next(reader)
                cols = ", ".join(headers)
                count = 0
                async with async_session() as session:
                    for row in reader:
                        placeholders = ", ".join([f":p{i}" for i in range(len(row))])
                        params = {}
                        for i, v in enumerate(row):
                            params[f"p{i}"] = convert_value(v, headers[i])
                        await session.execute(
                            text(f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"),
                            params
                        )
                        count += 1
                    await session.commit()
                results[table] = f"{count} rows loaded"
        except Exception as e:
            results[table] = f"error: {str(e)}"
    return {"status": "Seed data loading complete", "results": results}
