"""
Tool Registry — defines every action the Copilot can perform.

Each tool has a name, description, and parameter schema that gets
sent to the LLM. The LLM picks the right tool based on the user's
message and fills in the parameters.

This is the single source of truth for what the AI can do.
Adding a new capability = adding a new tool definition here +
implementing its handler in copilot.py.
"""


def get_copilot_tools() -> list[dict]:
    """
    Returns tool definitions in the format expected by the Anthropic API.

    Each tool has:
    - name: unique identifier (snake_case)
    - description: helps the LLM understand when to use it
    - input_schema: JSON Schema for the parameters
    """
    return [
        # ── Navigation Tools ──
        {
            "name": "navigate_to_module",
            "description": (
                "Navigate the user to a specific page or module in the ERP system. "
                "Use this when the user wants to go somewhere, view a page, or open a module. "
                "Examples: 'take me to sales orders', 'open the inventory page', 'go to HR'."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "description": "The module or page the user wants to navigate to (e.g., 'sales orders', 'inventory', 'payroll')"
                    }
                },
                "required": ["target"]
            }
        },

        # ── Finance Tools ──
        {
            "name": "get_cash_balance",
            "description": (
                "Get the current cash and bank balance summary. "
                "Use when the user asks about cash position, bank balances, or liquidity."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "as_of_date": {
                        "type": "string",
                        "description": "Date for the balance (ISO format). Defaults to today if not specified."
                    }
                },
                "required": []
            }
        },
        {
            "name": "get_financial_summary",
            "description": (
                "Get a financial summary including revenue, expenses, and profit for a given period. "
                "Use when the user asks about financial performance, P&L, revenue, or expenses."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date (ISO format, e.g., '2025-01-01')"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date (ISO format, e.g., '2025-12-31')"
                    },
                    "period": {
                        "type": "string",
                        "enum": ["monthly", "quarterly", "yearly"],
                        "description": "How to group the data. Defaults to monthly."
                    }
                },
                "required": []
            }
        },
        {
            "name": "get_ar_aging",
            "description": (
                "Get accounts receivable aging report showing outstanding customer balances by age bucket. "
                "Use when the user asks about AR, receivables, money owed, overdue invoices, or customer balances."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "customer_id": {
                        "type": "string",
                        "description": "Optional: filter to a specific customer"
                    }
                },
                "required": []
            }
        },
        {
            "name": "get_ap_aging",
            "description": (
                "Get accounts payable aging report showing outstanding vendor balances. "
                "Use when the user asks about AP, payables, bills due, or vendor balances."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "vendor_id": {
                        "type": "string",
                        "description": "Optional: filter to a specific vendor"
                    }
                },
                "required": []
            }
        },

        # ── Sales Tools ──
        {
            "name": "get_sales_summary",
            "description": (
                "Get sales performance summary including total orders, revenue, and top customers. "
                "Use when the user asks about sales, revenue, orders, or customer performance."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "start_date": {"type": "string", "description": "Start date (ISO format)"},
                    "end_date": {"type": "string", "description": "End date (ISO format)"},
                    "top_n": {"type": "integer", "description": "Number of top customers to return. Default 10."}
                },
                "required": []
            }
        },
        {
            "name": "get_customer_details",
            "description": (
                "Get details about a specific customer including their orders, invoices, and payment history. "
                "Use when the user asks about a particular customer by name or code."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "search_term": {
                        "type": "string",
                        "description": "Customer name, code, or partial match to search for"
                    }
                },
                "required": ["search_term"]
            }
        },
        {
            "name": "get_inactive_customers",
            "description": (
                "Find customers who haven't placed orders in a specified number of days. "
                "Use when the user asks about inactive, dormant, or at-risk customers."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "days_inactive": {
                        "type": "integer",
                        "description": "Number of days without an order to be considered inactive. Default 90."
                    }
                },
                "required": []
            }
        },

        # ── Inventory Tools ──
        {
            "name": "get_stock_levels",
            "description": (
                "Get current stock levels for all items or a specific item. "
                "Shows quantity on hand, reorder level, and stockout risk. "
                "Use when the user asks about inventory, stock, items, or reorder needs."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "item_name": {"type": "string", "description": "Optional: filter by item name"},
                    "category": {"type": "string", "description": "Optional: filter by category"},
                    "low_stock_only": {"type": "boolean", "description": "If true, only show items below reorder level"}
                },
                "required": []
            }
        },
        {
            "name": "get_warehouse_summary",
            "description": (
                "Get warehouse capacity and utilisation summary. "
                "Use when the user asks about warehouses, storage capacity, or distribution centres."
            ),
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },

        # ── Procurement Tools ──
        {
            "name": "get_vendor_performance",
            "description": (
                "Get vendor performance metrics including spend, rating, and order history. "
                "Use when the user asks about vendors, suppliers, or procurement performance."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "top_n": {"type": "integer", "description": "Number of top vendors to return. Default 10."},
                    "sort_by": {"type": "string", "enum": ["spend", "rating", "order_count"], "description": "How to rank vendors"}
                },
                "required": []
            }
        },
        {
            "name": "get_purchase_order_status",
            "description": (
                "Get status summary of purchase orders. "
                "Use when the user asks about PO status, pending orders, or procurement pipeline."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["Ordered", "Partially Received", "Received", "Cancelled"]},
                    "vendor_name": {"type": "string", "description": "Optional: filter by vendor name"}
                },
                "required": []
            }
        },

        # ── HR Tools ──
        {
            "name": "get_employee_summary",
            "description": (
                "Get employee headcount and department breakdown. "
                "Use when the user asks about employees, headcount, departments, or team size."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "department": {"type": "string", "description": "Optional: filter to a specific department"}
                },
                "required": []
            }
        },
        {
            "name": "get_payroll_summary",
            "description": (
                "Get payroll cost summary for a given period. "
                "Use when the user asks about payroll, salary costs, or compensation."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "year": {"type": "integer", "description": "Year to report on"},
                    "month": {"type": "integer", "description": "Optional: specific month (1-12)"}
                },
                "required": []
            }
        },
        {
            "name": "get_leave_summary",
            "description": (
                "Get leave utilisation summary showing pending, approved, and rejected requests. "
                "Use when the user asks about leave, time off, or absence."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["Pending", "Approved", "Rejected"]},
                    "department": {"type": "string", "description": "Optional: filter by department"}
                },
                "required": []
            }
        },

        # ── Asset Tools ──
        {
            "name": "get_asset_summary",
            "description": (
                "Get fixed asset summary including total value, depreciation, and net book value. "
                "Use when the user asks about assets, depreciation, or asset register."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "Optional: filter by asset category"}
                },
                "required": []
            }
        },

        # ── Project Tools ──
        {
            "name": "get_project_summary",
            "description": (
                "Get project portfolio summary including budget vs actual, completion status, and risks. "
                "Use when the user asks about projects, budgets, or project performance."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["In Progress", "Completed", "On Hold", "Planning", "Cancelled"]},
                    "department": {"type": "string", "description": "Optional: filter by department"}
                },
                "required": []
            }
        },

        # ── Help/Guidance Tools ──
        {
            "name": "get_help",
            "description": (
                "Provide help and guidance on how to use ERP features. "
                "Use when the user asks how to do something, needs instructions, "
                "or asks what features are available."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "The feature or process the user needs help with"
                    }
                },
                "required": ["topic"]
            }
        },
    ]
