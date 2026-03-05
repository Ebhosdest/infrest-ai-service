"""
ERP Client — fetches data from the ERP system.

In development, this queries the PostgreSQL database directly
(simulating the real ERP APIs). In production, you swap this
to call the actual Spring Boot REST APIs via HTTP.

Each method here corresponds to one tool in tool_registry.py.
The method names match the tool names exactly — this is intentional
so the copilot service can call them dynamically.
"""

from datetime import date, timedelta
from app.database.connection import execute_query


class ERPClient:
    """
    Adapter for ERP data access.

    Every public method returns a dictionary that the LLM
    can use to compose a human-readable response.
    """

    async def get_cash_balance(self, as_of_date: str = None) -> dict:
        target_date = as_of_date or date.today().isoformat()

        query = """
            SELECT
                coa.account_name,
                coa.account_code,
                COALESCE(SUM(gl.debit_amount), 0) - COALESCE(SUM(gl.credit_amount), 0) AS balance
            FROM chart_of_accounts coa
            LEFT JOIN general_ledger gl ON gl.account_code = coa.account_code
                AND gl.entry_date <= :target_date
            WHERE coa.sub_type = 'Bank' OR coa.sub_type = 'Cash'
            GROUP BY coa.account_name, coa.account_code
            ORDER BY balance DESC
        """
        rows = await execute_query(query, {"target_date": target_date})

        total = sum(row["balance"] for row in rows)
        return {
            "as_of_date": target_date,
            "total_cash_balance": total,
            "accounts": [
                {"name": r["account_name"], "code": r["account_code"], "balance": float(r["balance"])}
                for r in rows
            ],
            "currency": "NGN",
        }

    async def get_financial_summary(self, start_date: str = None, end_date: str = None, period: str = "monthly") -> dict:
        if not start_date:
            start_date = date(date.today().year, 1, 1).isoformat()
        if not end_date:
            end_date = date.today().isoformat()

        # Revenue
        rev_query = """
            SELECT COALESCE(SUM(debit_amount), 0) - COALESCE(SUM(credit_amount), 0) AS total
            FROM general_ledger
            WHERE account_code LIKE '4%%' AND entry_date BETWEEN :start AND :end
        """
        rev_rows = await execute_query(rev_query, {"start": start_date, "end": end_date})

        # Expenses
        exp_query = """
            SELECT COALESCE(SUM(debit_amount), 0) - COALESCE(SUM(credit_amount), 0) AS total
            FROM general_ledger
            WHERE (account_code LIKE '5%%' OR account_code LIKE '6%%')
                AND entry_date BETWEEN :start AND :end
        """
        exp_rows = await execute_query(exp_query, {"start": start_date, "end": end_date})

        # Note: revenue accounts normally have credit balances,
        # so the net amount calculation might be negative. We take the absolute.
        revenue = abs(float(rev_rows[0]["total"])) if rev_rows else 0
        expenses = abs(float(exp_rows[0]["total"])) if exp_rows else 0
        profit = revenue - expenses

        return {
            "period": {"start": start_date, "end": end_date},
            "total_revenue": revenue,
            "total_expenses": expenses,
            "net_profit": profit,
            "profit_margin": round((profit / revenue * 100), 2) if revenue > 0 else 0,
            "currency": "NGN",
        }

    async def get_ar_aging(self, customer_id: str = None) -> dict:
        where_clause = "WHERE 1=1"
        params = {}
        if customer_id:
            where_clause += " AND a.customer_id = :customer_id"
            params["customer_id"] = customer_id

        query = f"""
            SELECT
                a.aging_bucket,
                COUNT(*) as invoice_count,
                SUM(a.outstanding_amount) as total_outstanding
            FROM ar_aging a
            {where_clause}
            GROUP BY a.aging_bucket
            ORDER BY
                CASE a.aging_bucket
                    WHEN 'Current' THEN 1
                    WHEN '31-60' THEN 2
                    WHEN '61-90' THEN 3
                    WHEN 'Over 90' THEN 4
                END
        """
        rows = await execute_query(query, params)

        total = sum(float(r["total_outstanding"]) for r in rows)
        return {
            "total_outstanding": total,
            "buckets": [
                {"bucket": r["aging_bucket"], "count": r["invoice_count"], "amount": float(r["total_outstanding"])}
                for r in rows
            ],
            "currency": "NGN",
        }

    async def get_ap_aging(self, vendor_id: str = None) -> dict:
        where_clause = "WHERE 1=1"
        params = {}
        if vendor_id:
            where_clause += " AND a.vendor_id = :vendor_id"
            params["vendor_id"] = vendor_id

        query = f"""
            SELECT
                a.aging_bucket,
                COUNT(*) as po_count,
                SUM(a.outstanding_amount) as total_outstanding
            FROM ap_aging a
            {where_clause}
            GROUP BY a.aging_bucket
            ORDER BY
                CASE a.aging_bucket
                    WHEN 'Current' THEN 1
                    WHEN '31-60' THEN 2
                    WHEN '61-90' THEN 3
                    WHEN 'Over 90' THEN 4
                END
        """
        rows = await execute_query(query, params)

        total = sum(float(r["total_outstanding"]) for r in rows)
        return {
            "total_outstanding": total,
            "buckets": [
                {"bucket": r["aging_bucket"], "count": r["po_count"], "amount": float(r["total_outstanding"])}
                for r in rows
            ],
            "currency": "NGN",
        }

    async def get_sales_summary(self, start_date: str = None, end_date: str = None, top_n: int = 10) -> dict:
        if not start_date:
            start_date = date(date.today().year, 1, 1).isoformat()
        if not end_date:
            end_date = date.today().isoformat()

        # Overall summary
        summary_query = """
            SELECT
                COUNT(*) as total_orders,
                SUM(total_amount) as total_revenue,
                AVG(total_amount) as avg_order_value,
                COUNT(CASE WHEN status = 'Completed' THEN 1 END) as completed_orders,
                COUNT(CASE WHEN status = 'Pending' THEN 1 END) as pending_orders
            FROM sales_orders
            WHERE order_date BETWEEN :start AND :end
        """
        summary = await execute_query(summary_query, {"start": start_date, "end": end_date})

        # Top customers
        top_query = """
            SELECT
                c.company_name,
                c.customer_code,
                COUNT(so.id) as order_count,
                SUM(so.total_amount) as total_revenue
            FROM sales_orders so
            JOIN customers c ON c.id = so.customer_id
            WHERE so.order_date BETWEEN :start AND :end
            GROUP BY c.company_name, c.customer_code
            ORDER BY total_revenue DESC
            LIMIT :top_n
        """
        top_customers = await execute_query(top_query, {"start": start_date, "end": end_date, "top_n": top_n})

        s = summary[0] if summary else {}
        return {
            "period": {"start": start_date, "end": end_date},
            "total_orders": s.get("total_orders", 0),
            "total_revenue": float(s.get("total_revenue", 0) or 0),
            "avg_order_value": float(s.get("avg_order_value", 0) or 0),
            "completed_orders": s.get("completed_orders", 0),
            "pending_orders": s.get("pending_orders", 0),
            "top_customers": [
                {
                    "name": r["company_name"],
                    "code": r["customer_code"],
                    "orders": r["order_count"],
                    "revenue": float(r["total_revenue"]),
                }
                for r in top_customers
            ],
            "currency": "NGN",
        }

    async def get_customer_details(self, search_term: str) -> dict:
        query = """
            SELECT c.*,
                COUNT(DISTINCT so.id) as total_orders,
                COALESCE(SUM(so.total_amount), 0) as lifetime_revenue,
                MAX(so.order_date) as last_order_date
            FROM customers c
            LEFT JOIN sales_orders so ON so.customer_id = c.id
            WHERE LOWER(c.company_name) LIKE LOWER(:search)
                OR c.customer_code LIKE UPPER(:search)
            GROUP BY c.id
            LIMIT 5
        """
        rows = await execute_query(query, {"search": f"%{search_term}%"})

        return {
            "results": [
                {
                    "name": r["company_name"],
                    "code": r["customer_code"],
                    "industry": r["industry"],
                    "status": r["status"],
                    "credit_limit": float(r["credit_limit"]),
                    "total_orders": r["total_orders"],
                    "lifetime_revenue": float(r["lifetime_revenue"]),
                    "last_order": str(r["last_order_date"]) if r["last_order_date"] else "Never",
                    "contact": f"{r['contact_first_name']} {r['contact_last_name']}",
                    "email": r["email"],
                    "phone": r["phone"],
                }
                for r in rows
            ],
            "count": len(rows),
            "currency": "NGN",
        }

    async def get_inactive_customers(self, days_inactive: int = 90) -> dict:
        cutoff = (date.today() - timedelta(days=days_inactive)).isoformat()
        query = """
            SELECT
                c.company_name, c.customer_code, c.industry,
                MAX(so.order_date) as last_order_date,
                COUNT(so.id) as total_orders,
                COALESCE(SUM(so.total_amount), 0) as lifetime_revenue
            FROM customers c
            LEFT JOIN sales_orders so ON so.customer_id = c.id
            WHERE c.status = 'Active'
            GROUP BY c.id, c.company_name, c.customer_code, c.industry
            HAVING MAX(so.order_date) < :cutoff OR MAX(so.order_date) IS NULL
            ORDER BY lifetime_revenue DESC
            LIMIT 50
        """
        rows = await execute_query(query, {"cutoff": cutoff})

        return {
            "days_threshold": days_inactive,
            "count": len(rows),
            "customers": [
                {
                    "name": r["company_name"],
                    "code": r["customer_code"],
                    "industry": r["industry"],
                    "last_order": str(r["last_order_date"]) if r["last_order_date"] else "Never",
                    "total_orders": r["total_orders"],
                    "lifetime_revenue": float(r["lifetime_revenue"]),
                }
                for r in rows
            ],
            "currency": "NGN",
        }

    async def get_stock_levels(self, item_name: str = None, category: str = None, low_stock_only: bool = False) -> dict:
        conditions = ["1=1"]
        params = {}

        if item_name:
            conditions.append("LOWER(item_name) LIKE LOWER(:item_name)")
            params["item_name"] = f"%{item_name}%"
        if category:
            conditions.append("LOWER(category) = LOWER(:category)")
            params["category"] = category
        if low_stock_only:
            conditions.append("quantity_on_hand <= reorder_level")

        where = " AND ".join(conditions)
        query = f"""
            SELECT item_code, item_name, category, quantity_on_hand,
                   reorder_level, unit_cost, unit_price,
                   (quantity_on_hand * unit_cost) as stock_value,
                   CASE WHEN quantity_on_hand <= reorder_level THEN true ELSE false END as needs_reorder
            FROM inventory_items
            WHERE {where}
            ORDER BY quantity_on_hand ASC
        """
        rows = await execute_query(query, params)

        total_value = sum(float(r["stock_value"]) for r in rows)
        reorder_count = sum(1 for r in rows if r["needs_reorder"])

        return {
            "total_items": len(rows),
            "total_stock_value": total_value,
            "items_needing_reorder": reorder_count,
            "items": [
                {
                    "code": r["item_code"],
                    "name": r["item_name"],
                    "category": r["category"],
                    "qty_on_hand": r["quantity_on_hand"],
                    "reorder_level": r["reorder_level"],
                    "stock_value": float(r["stock_value"]),
                    "needs_reorder": r["needs_reorder"],
                }
                for r in rows
            ],
            "currency": "NGN",
        }

    async def get_warehouse_summary(self) -> dict:
        query = """
            SELECT w.warehouse_code, w.name, w.city, w.state, w.capacity_sqm, w.status,
                   COUNT(DISTINCT sm.item_id) as unique_items,
                   COALESCE(SUM(CASE WHEN sm.movement_type = 'Receipt' THEN sm.quantity ELSE 0 END), 0) as total_received,
                   COALESCE(SUM(CASE WHEN sm.movement_type = 'Issue' THEN sm.quantity ELSE 0 END), 0) as total_issued
            FROM warehouses w
            LEFT JOIN stock_movements sm ON sm.warehouse_id = w.id
            GROUP BY w.id, w.warehouse_code, w.name, w.city, w.state, w.capacity_sqm, w.status
            ORDER BY w.warehouse_code
        """
        rows = await execute_query(query)

        return {
            "total_warehouses": len(rows),
            "warehouses": [
                {
                    "code": r["warehouse_code"],
                    "name": r["name"],
                    "location": f"{r['city']}, {r['state']}",
                    "capacity_sqm": r["capacity_sqm"],
                    "status": r["status"],
                    "unique_items": r["unique_items"],
                    "total_received": r["total_received"],
                    "total_issued": r["total_issued"],
                }
                for r in rows
            ],
        }

    async def get_vendor_performance(self, top_n: int = 10, sort_by: str = "spend") -> dict:
        order_col = {
            "spend": "total_spend",
            "rating": "v.rating",
            "order_count": "order_count",
        }.get(sort_by, "total_spend")

        query = f"""
            SELECT v.vendor_code, v.company_name, v.category, v.rating,
                   COUNT(po.id) as order_count,
                   COALESCE(SUM(po.total_amount), 0) as total_spend
            FROM vendors v
            LEFT JOIN purchase_orders po ON po.vendor_id = v.id
            WHERE v.status = 'Active'
            GROUP BY v.id, v.vendor_code, v.company_name, v.category, v.rating
            ORDER BY {order_col} DESC
            LIMIT :top_n
        """
        rows = await execute_query(query, {"top_n": top_n})

        return {
            "top_vendors": [
                {
                    "code": r["vendor_code"],
                    "name": r["company_name"],
                    "category": r["category"],
                    "rating": float(r["rating"]) if r["rating"] else 0,
                    "orders": r["order_count"],
                    "total_spend": float(r["total_spend"]),
                }
                for r in rows
            ],
            "currency": "NGN",
        }

    async def get_purchase_order_status(self, status: str = None, vendor_name: str = None) -> dict:
        conditions = ["1=1"]
        params = {}
        if status:
            conditions.append("po.status = :status")
            params["status"] = status
        if vendor_name:
            conditions.append("LOWER(v.company_name) LIKE LOWER(:vendor_name)")
            params["vendor_name"] = f"%{vendor_name}%"

        where = " AND ".join(conditions)
        query = f"""
            SELECT po.status, COUNT(*) as count, SUM(po.total_amount) as total_value
            FROM purchase_orders po
            JOIN vendors v ON v.id = po.vendor_id
            WHERE {where}
            GROUP BY po.status
            ORDER BY total_value DESC
        """
        rows = await execute_query(query, params)

        return {
            "status_breakdown": [
                {"status": r["status"], "count": r["count"], "value": float(r["total_value"])}
                for r in rows
            ],
            "currency": "NGN",
        }

    async def get_employee_summary(self, department: str = None) -> dict:
        conditions = ["status = 'Active'"]
        params = {}
        if department:
            conditions.append("LOWER(department) = LOWER(:dept)")
            params["dept"] = department

        where = " AND ".join(conditions)
        query = f"""
            SELECT department, COUNT(*) as headcount,
                   AVG(annual_salary) as avg_salary,
                   SUM(annual_salary) as total_salary_cost
            FROM employees
            WHERE {where}
            GROUP BY department
            ORDER BY headcount DESC
        """
        rows = await execute_query(query, params)

        total_headcount = sum(r["headcount"] for r in rows)
        total_cost = sum(float(r["total_salary_cost"]) for r in rows)

        return {
            "total_headcount": total_headcount,
            "total_annual_salary_cost": total_cost,
            "departments": [
                {
                    "department": r["department"],
                    "headcount": r["headcount"],
                    "avg_salary": float(r["avg_salary"]),
                    "total_cost": float(r["total_salary_cost"]),
                }
                for r in rows
            ],
            "currency": "NGN",
        }

    async def get_payroll_summary(self, year: int = None, month: int = None) -> dict:
        if not year:
            year = date.today().year

        conditions = ["p.year = :year"]
        params = {"year": year}
        if month:
            conditions.append("p.month = :month")
            params["month"] = month

        where = " AND ".join(conditions)
        query = f"""
            SELECT
                SUM(gross_pay) as total_gross,
                SUM(net_pay) as total_net,
                SUM(total_deductions) as total_deductions,
                SUM(pension_employee) as total_pension_employee,
                SUM(pension_employer) as total_pension_employer,
                SUM(tax_paye) as total_tax,
                COUNT(DISTINCT employee_id) as employee_count
            FROM payroll p
            WHERE {where}
        """
        rows = await execute_query(query, params)
        r = rows[0] if rows else {}

        return {
            "year": year,
            "month": month,
            "employee_count": r.get("employee_count", 0),
            "total_gross_pay": float(r.get("total_gross", 0) or 0),
            "total_net_pay": float(r.get("total_net", 0) or 0),
            "total_deductions": float(r.get("total_deductions", 0) or 0),
            "total_paye_tax": float(r.get("total_tax", 0) or 0),
            "total_pension_employee": float(r.get("total_pension_employee", 0) or 0),
            "total_pension_employer": float(r.get("total_pension_employer", 0) or 0),
            "currency": "NGN",
        }

    async def get_leave_summary(self, status: str = None, department: str = None) -> dict:
        conditions = ["1=1"]
        params = {}
        if status:
            conditions.append("lr.status = :status")
            params["status"] = status
        if department:
            conditions.append("LOWER(e.department) = LOWER(:dept)")
            params["dept"] = department

        where = " AND ".join(conditions)
        query = f"""
            SELECT lr.status, lr.leave_type, COUNT(*) as count, SUM(lr.days_requested) as total_days
            FROM leave_records lr
            JOIN employees e ON e.id = lr.employee_id
            WHERE {where}
            GROUP BY lr.status, lr.leave_type
            ORDER BY count DESC
        """
        rows = await execute_query(query, params)

        return {
            "breakdown": [
                {"status": r["status"], "leave_type": r["leave_type"], "count": r["count"], "total_days": r["total_days"]}
                for r in rows
            ],
        }

    async def get_asset_summary(self, category: str = None) -> dict:
        conditions = ["1=1"]
        params = {}
        if category:
            conditions.append("LOWER(category) = LOWER(:cat)")
            params["cat"] = category

        where = " AND ".join(conditions)
        query = f"""
            SELECT category,
                   COUNT(*) as asset_count,
                   SUM(purchase_cost) as total_cost,
                   SUM(accumulated_depreciation) as total_depreciation,
                   SUM(net_book_value) as total_nbv
            FROM fixed_assets
            WHERE {where}
            GROUP BY category
            ORDER BY total_cost DESC
        """
        rows = await execute_query(query, params)

        return {
            "categories": [
                {
                    "category": r["category"],
                    "count": r["asset_count"],
                    "total_cost": float(r["total_cost"]),
                    "total_depreciation": float(r["total_depreciation"]),
                    "net_book_value": float(r["total_nbv"]),
                }
                for r in rows
            ],
            "totals": {
                "total_assets": sum(r["asset_count"] for r in rows),
                "total_cost": sum(float(r["total_cost"]) for r in rows),
                "total_depreciation": sum(float(r["total_depreciation"]) for r in rows),
                "total_nbv": sum(float(r["total_nbv"]) for r in rows),
            },
            "currency": "NGN",
        }

    async def get_project_summary(self, status: str = None, department: str = None) -> dict:
        conditions = ["1=1"]
        params = {}
        if status:
            conditions.append("p.status = :status")
            params["status"] = status
        if department:
            conditions.append("LOWER(p.department) = LOWER(:dept)")
            params["dept"] = department

        where = " AND ".join(conditions)
        query = f"""
            SELECT p.project_code, p.project_name, p.department, p.status,
                   p.budget, p.actual_cost, p.completion_percentage,
                   p.start_date, p.end_date,
                   CASE WHEN p.budget > 0 THEN ROUND((p.actual_cost / p.budget * 100)::numeric, 1) ELSE 0 END as budget_utilisation
            FROM projects p
            WHERE {where}
            ORDER BY p.budget DESC
        """
        rows = await execute_query(query, params)

        total_budget = sum(float(r["budget"]) for r in rows)
        total_actual = sum(float(r["actual_cost"]) for r in rows)

        return {
            "total_projects": len(rows),
            "total_budget": total_budget,
            "total_actual_cost": total_actual,
            "budget_variance": total_budget - total_actual,
            "projects": [
                {
                    "code": r["project_code"],
                    "name": r["project_name"],
                    "department": r["department"],
                    "status": r["status"],
                    "budget": float(r["budget"]),
                    "actual_cost": float(r["actual_cost"]),
                    "completion": r["completion_percentage"],
                    "budget_utilisation": float(r["budget_utilisation"]),
                }
                for r in rows
            ],
            "currency": "NGN",
        }