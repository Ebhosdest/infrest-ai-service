"""
Navigation Route Registry.

This maps module names, aliases, and keywords to actual frontend routes.
When the LLM identifies a navigation intent, it calls the 'navigate'
tool with a target like "sales orders". This registry resolves that
to the actual route path.

The aliases are important — users say things differently.
"SO", "sales order", "orders", "show me sales" should all
resolve to /sales/orders.
"""

from dataclasses import dataclass


@dataclass
class Route:
    path: str
    label: str
    module: str
    description: str
    aliases: list[str]


# Every navigable route in the ERP.
# When the real app is ready, update these paths to match.
ROUTE_REGISTRY: list[Route] = [
    # Dashboard
    Route(
        path="/dashboard",
        label="Dashboard",
        module="dashboard",
        description="Main dashboard with KPIs and visualisations",
        aliases=["home", "main", "overview", "kpi", "dashboard"],
    ),

    # Finance Module
    Route(
        path="/finance/chart-of-accounts",
        label="Chart of Accounts",
        module="finance",
        description="Chart of accounts listing all GL accounts",
        aliases=["coa", "chart of accounts", "accounts", "gl accounts", "ledger accounts"],
    ),
    Route(
        path="/finance/general-ledger",
        label="General Ledger",
        module="finance",
        description="General ledger entries and journal postings",
        aliases=["gl", "general ledger", "journal entries", "journals", "ledger"],
    ),
    Route(
        path="/finance/accounts-receivable",
        label="Accounts Receivable",
        module="finance",
        description="Accounts receivable and customer balances",
        aliases=["ar", "accounts receivable", "receivables", "money owed to us", "customer balances"],
    ),
    Route(
        path="/finance/accounts-payable",
        label="Accounts Payable",
        module="finance",
        description="Accounts payable and vendor balances",
        aliases=["ap", "accounts payable", "payables", "bills", "money we owe", "vendor balances"],
    ),

    # Sales Module
    Route(
        path="/sales/customers",
        label="Customers",
        module="sales",
        description="Customer master list and details",
        aliases=["customers", "client list", "customer list", "clients", "buyers"],
    ),
    Route(
        path="/sales/orders",
        label="Sales Orders",
        module="sales",
        description="Sales orders listing",
        aliases=["sales orders", "so", "orders", "sales", "customer orders"],
    ),
    Route(
        path="/sales/invoices",
        label="Invoices",
        module="sales",
        description="Customer invoices",
        aliases=["invoices", "customer invoices", "bills sent", "invoice list"],
    ),

    # Inventory Module
    Route(
        path="/inventory/items",
        label="Inventory Items",
        module="inventory",
        description="Product and inventory item catalogue",
        aliases=["inventory", "items", "products", "stock", "sku", "catalogue", "catalog"],
    ),
    Route(
        path="/inventory/warehouses",
        label="Warehouses",
        module="inventory",
        description="Warehouse locations and capacity",
        aliases=["warehouses", "warehouse", "storage", "depot", "locations"],
    ),
    Route(
        path="/inventory/stock-movements",
        label="Stock Movements",
        module="inventory",
        description="Stock receipts, issues, transfers, and adjustments",
        aliases=["stock movements", "stock transfers", "receipts", "issues", "inventory movements"],
    ),

    # Procurement Module
    Route(
        path="/procurement/vendors",
        label="Vendors",
        module="procurement",
        description="Vendor and supplier master list",
        aliases=["vendors", "suppliers", "vendor list", "supplier list"],
    ),
    Route(
        path="/procurement/requisitions",
        label="Purchase Requisitions",
        module="procurement",
        description="Internal purchase requisitions",
        aliases=["requisitions", "pr", "purchase requests", "purchase requisitions", "buy requests"],
    ),
    Route(
        path="/procurement/purchase-orders",
        label="Purchase Orders",
        module="procurement",
        description="Purchase orders to vendors",
        aliases=["purchase orders", "po", "pos", "vendor orders", "buy orders"],
    ),

    # HR Module
    Route(
        path="/hr/employees",
        label="Employees",
        module="hr",
        description="Employee directory and records",
        aliases=["employees", "staff", "team", "personnel", "employee list", "workforce"],
    ),
    Route(
        path="/hr/leave",
        label="Leave Management",
        module="hr",
        description="Employee leave requests and balances",
        aliases=["leave", "leave management", "time off", "vacation", "absence", "leave requests"],
    ),
    Route(
        path="/hr/payroll",
        label="Payroll",
        module="hr",
        description="Payroll processing and history",
        aliases=["payroll", "salary", "wages", "pay", "compensation", "payslip"],
    ),

    # Assets Module
    Route(
        path="/assets/register",
        label="Asset Register",
        module="assets",
        description="Fixed asset register with depreciation",
        aliases=["assets", "fixed assets", "asset register", "depreciation", "asset list"],
    ),

    # Projects Module
    Route(
        path="/projects",
        label="Projects",
        module="projects",
        description="Project management and tracking",
        aliases=["projects", "project list", "project management", "project tracking"],
    ),

    # Reports Module
    Route(
        path="/reports",
        label="Reports",
        module="reports",
        description="Report templates and custom report builder",
        aliases=["reports", "reporting", "report builder", "analytics"],
    ),
    Route(
        path="/reports/ask",
        label="Ask Questions",
        module="reports",
        description="Natural language report query interface",
        aliases=["ask questions", "nlp reports", "ask", "query reports", "natural language reports"],
    ),

    # Settings
    Route(
        path="/settings",
        label="Settings",
        module="settings",
        description="User profile, preferences, and system settings",
        aliases=["settings", "preferences", "profile", "configuration", "config"],
    ),
]


def find_route(query: str) -> Route | None:
    """
    Find the best matching route for a natural language query.

    Checks exact alias matches first, then partial matches.
    Returns None if no reasonable match is found.
    """
    query_lower = query.lower().strip()

    # First pass: exact alias match
    for route in ROUTE_REGISTRY:
        if query_lower in route.aliases:
            return route

    # Second pass: check if query contains any alias
    best_match = None
    best_score = 0

    for route in ROUTE_REGISTRY:
        for alias in route.aliases:
            # Check if the alias appears in the query
            if alias in query_lower:
                score = len(alias)  # Longer matches are better
                if score > best_score:
                    best_score = score
                    best_match = route

    return best_match


def get_all_routes() -> list[dict]:
    """Return all routes as dictionaries (used in system prompts)."""
    return [
        {
            "path": r.path,
            "label": r.label,
            "module": r.module,
            "description": r.description,
        }
        for r in ROUTE_REGISTRY
    ]
