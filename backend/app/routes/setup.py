"""
One-time database setup endpoints.
Creates tables and loads seed data on Render.
"""

from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from app.database.connection import async_session
import os
import csv

router = APIRouter(prefix="/api/setup", tags=["setup"])


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
                        params = {f"p{i}": (v if v != "" else None) for i, v in enumerate(row)}
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
