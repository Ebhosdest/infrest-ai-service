-- ============================================================
-- INFREST ERP - DATABASE SCHEMA
-- Generated for development/demo purposes
-- Database: PostgreSQL 15+
-- ============================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- CHART OF ACCOUNTS
-- ============================================================
CREATE TABLE IF NOT EXISTS chart_of_accounts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    account_code VARCHAR(10) NOT NULL UNIQUE,
    account_name VARCHAR(200) NOT NULL,
    account_type VARCHAR(50) NOT NULL,
    sub_type VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    currency VARCHAR(10) DEFAULT 'NGN',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- CUSTOMERS
-- ============================================================
CREATE TABLE IF NOT EXISTS customers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_code VARCHAR(20) NOT NULL UNIQUE,
    company_name VARCHAR(200) NOT NULL,
    contact_first_name VARCHAR(100),
    contact_last_name VARCHAR(100),
    email VARCHAR(200),
    phone VARCHAR(50),
    address TEXT,
    city VARCHAR(100),
    state VARCHAR(100),
    country VARCHAR(100) DEFAULT 'Nigeria',
    industry VARCHAR(100),
    credit_limit NUMERIC(15,2) DEFAULT 0,
    payment_terms_days INTEGER DEFAULT 30,
    status VARCHAR(20) DEFAULT 'Active',
    currency VARCHAR(10) DEFAULT 'NGN',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- VENDORS
-- ============================================================
CREATE TABLE IF NOT EXISTS vendors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vendor_code VARCHAR(20) NOT NULL UNIQUE,
    company_name VARCHAR(200) NOT NULL,
    contact_first_name VARCHAR(100),
    contact_last_name VARCHAR(100),
    email VARCHAR(200),
    phone VARCHAR(50),
    city VARCHAR(100),
    state VARCHAR(100),
    country VARCHAR(100) DEFAULT 'Nigeria',
    category VARCHAR(100),
    rating NUMERIC(3,1),
    payment_terms_days INTEGER DEFAULT 30,
    status VARCHAR(20) DEFAULT 'Active',
    currency VARCHAR(10) DEFAULT 'NGN',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- EMPLOYEES
-- ============================================================
CREATE TABLE IF NOT EXISTS employees (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    employee_code VARCHAR(20) NOT NULL UNIQUE,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(200),
    phone VARCHAR(50),
    department VARCHAR(100),
    position VARCHAR(200),
    annual_salary NUMERIC(15,2),
    hire_date DATE,
    employment_type VARCHAR(50) DEFAULT 'Full-Time',
    location VARCHAR(100),
    status VARCHAR(20) DEFAULT 'Active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- INVENTORY ITEMS
-- ============================================================
CREATE TABLE IF NOT EXISTS inventory_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    item_code VARCHAR(20) NOT NULL UNIQUE,
    item_name VARCHAR(200) NOT NULL,
    category VARCHAR(100),
    sku_prefix VARCHAR(10),
    unit_of_measure VARCHAR(50),
    unit_cost NUMERIC(15,2),
    unit_price NUMERIC(15,2),
    quantity_on_hand INTEGER DEFAULT 0,
    reorder_level INTEGER DEFAULT 10,
    is_active BOOLEAN DEFAULT TRUE,
    currency VARCHAR(10) DEFAULT 'NGN',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- WAREHOUSES
-- ============================================================
CREATE TABLE IF NOT EXISTS warehouses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    warehouse_code VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(200) NOT NULL,
    address TEXT,
    city VARCHAR(100),
    state VARCHAR(100),
    capacity_sqm INTEGER,
    status VARCHAR(20) DEFAULT 'Active'
);

-- ============================================================
-- SALES ORDERS
-- ============================================================
CREATE TABLE IF NOT EXISTS sales_orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_number VARCHAR(20) NOT NULL UNIQUE,
    customer_id UUID REFERENCES customers(id),
    order_date DATE NOT NULL,
    status VARCHAR(30) DEFAULT 'Pending',
    subtotal NUMERIC(15,2),
    vat_amount NUMERIC(15,2),
    total_amount NUMERIC(15,2),
    currency VARCHAR(10) DEFAULT 'NGN',
    sales_rep_id UUID REFERENCES employees(id),
    expected_delivery DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sales_order_lines (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sales_order_id UUID REFERENCES sales_orders(id),
    item_id UUID REFERENCES inventory_items(id),
    item_name VARCHAR(200),
    quantity INTEGER,
    unit_price NUMERIC(15,2),
    line_total NUMERIC(15,2),
    line_number INTEGER
);

-- ============================================================
-- INVOICES
-- ============================================================
CREATE TABLE IF NOT EXISTS invoices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    invoice_number VARCHAR(20) NOT NULL UNIQUE,
    sales_order_id UUID REFERENCES sales_orders(id),
    customer_id UUID REFERENCES customers(id),
    invoice_date DATE NOT NULL,
    due_date DATE,
    subtotal NUMERIC(15,2),
    vat_amount NUMERIC(15,2),
    total_amount NUMERIC(15,2),
    amount_paid NUMERIC(15,2) DEFAULT 0,
    payment_status VARCHAR(30) DEFAULT 'Unpaid',
    currency VARCHAR(10) DEFAULT 'NGN',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- PURCHASE REQUISITIONS
-- ============================================================
CREATE TABLE IF NOT EXISTS purchase_requisitions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pr_number VARCHAR(20) NOT NULL UNIQUE,
    requester_id UUID REFERENCES employees(id),
    department VARCHAR(100),
    request_date DATE NOT NULL,
    status VARCHAR(30) DEFAULT 'Draft',
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- PURCHASE ORDERS
-- ============================================================
CREATE TABLE IF NOT EXISTS purchase_orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    po_number VARCHAR(20) NOT NULL UNIQUE,
    pr_id UUID REFERENCES purchase_requisitions(id),
    vendor_id UUID REFERENCES vendors(id),
    order_date DATE NOT NULL,
    status VARCHAR(30) DEFAULT 'Draft',
    subtotal NUMERIC(15,2),
    vat_amount NUMERIC(15,2),
    total_amount NUMERIC(15,2),
    currency VARCHAR(10) DEFAULT 'NGN',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS purchase_order_lines (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    purchase_order_id UUID REFERENCES purchase_orders(id),
    item_id UUID REFERENCES inventory_items(id),
    item_name VARCHAR(200),
    quantity INTEGER,
    unit_price NUMERIC(15,2),
    line_total NUMERIC(15,2),
    line_number INTEGER
);

-- ============================================================
-- GENERAL LEDGER
-- ============================================================
CREATE TABLE IF NOT EXISTS general_ledger (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    journal_ref VARCHAR(30) NOT NULL,
    entry_date DATE NOT NULL,
    account_code VARCHAR(10) REFERENCES chart_of_accounts(account_code),
    account_id UUID REFERENCES chart_of_accounts(id),
    description TEXT,
    debit_amount NUMERIC(15,2) DEFAULT 0,
    credit_amount NUMERIC(15,2) DEFAULT 0,
    net_amount NUMERIC(15,2) DEFAULT 0,
    status VARCHAR(20) DEFAULT 'Posted',
    source VARCHAR(50),
    posted_by UUID REFERENCES employees(id),
    currency VARCHAR(10) DEFAULT 'NGN',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_gl_date ON general_ledger(entry_date);
CREATE INDEX idx_gl_account ON general_ledger(account_code);

-- ============================================================
-- FIXED ASSETS
-- ============================================================
CREATE TABLE IF NOT EXISTS fixed_assets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    asset_code VARCHAR(20) NOT NULL UNIQUE,
    asset_name VARCHAR(200) NOT NULL,
    category VARCHAR(100),
    gl_account_code VARCHAR(10),
    purchase_date DATE,
    purchase_cost NUMERIC(15,2),
    useful_life_years INTEGER,
    depreciation_method VARCHAR(50) DEFAULT 'Straight-Line',
    annual_depreciation NUMERIC(15,2),
    accumulated_depreciation NUMERIC(15,2),
    net_book_value NUMERIC(15,2),
    status VARCHAR(30) DEFAULT 'In Use',
    assigned_department VARCHAR(100),
    location VARCHAR(100),
    currency VARCHAR(10) DEFAULT 'NGN',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- LEAVE RECORDS
-- ============================================================
CREATE TABLE IF NOT EXISTS leave_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    employee_id UUID REFERENCES employees(id),
    leave_type VARCHAR(50),
    start_date DATE,
    end_date DATE,
    days_requested INTEGER,
    status VARCHAR(20) DEFAULT 'Pending',
    approved_by UUID REFERENCES employees(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- PAYROLL
-- ============================================================
CREATE TABLE IF NOT EXISTS payroll (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    employee_id UUID REFERENCES employees(id),
    year INTEGER,
    month INTEGER,
    period VARCHAR(10),
    basic_salary NUMERIC(15,2),
    housing_allowance NUMERIC(15,2),
    transport_allowance NUMERIC(15,2),
    other_allowances NUMERIC(15,2),
    gross_pay NUMERIC(15,2),
    pension_employee NUMERIC(15,2),
    pension_employer NUMERIC(15,2),
    tax_paye NUMERIC(15,2),
    nhf NUMERIC(15,2),
    total_deductions NUMERIC(15,2),
    net_pay NUMERIC(15,2),
    status VARCHAR(20) DEFAULT 'Paid',
    payment_date DATE,
    currency VARCHAR(10) DEFAULT 'NGN',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- PROJECTS
-- ============================================================
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_code VARCHAR(20) NOT NULL UNIQUE,
    project_name VARCHAR(200) NOT NULL,
    department VARCHAR(100),
    project_manager_id UUID REFERENCES employees(id),
    start_date DATE,
    end_date DATE,
    budget NUMERIC(15,2),
    actual_cost NUMERIC(15,2) DEFAULT 0,
    completion_percentage INTEGER DEFAULT 0,
    status VARCHAR(30) DEFAULT 'Planning',
    currency VARCHAR(10) DEFAULT 'NGN',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS project_costs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES projects(id),
    cost_date DATE,
    cost_category VARCHAR(100),
    description TEXT,
    amount NUMERIC(15,2),
    vendor_id UUID,
    currency VARCHAR(10) DEFAULT 'NGN',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- STOCK MOVEMENTS
-- ============================================================
CREATE TABLE IF NOT EXISTS stock_movements (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    item_id UUID REFERENCES inventory_items(id),
    item_name VARCHAR(200),
    warehouse_id UUID REFERENCES warehouses(id),
    movement_date DATE,
    movement_type VARCHAR(30),
    quantity INTEGER,
    reference_document VARCHAR(50),
    performed_by UUID REFERENCES employees(id),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- AR / AP AGING VIEWS
-- ============================================================
CREATE TABLE IF NOT EXISTS ar_aging (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    invoice_id UUID REFERENCES invoices(id),
    customer_id UUID REFERENCES customers(id),
    invoice_date DATE,
    due_date DATE,
    outstanding_amount NUMERIC(15,2),
    days_outstanding INTEGER,
    aging_bucket VARCHAR(20),
    currency VARCHAR(10) DEFAULT 'NGN'
);

CREATE TABLE IF NOT EXISTS ap_aging (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    po_id UUID REFERENCES purchase_orders(id),
    vendor_id UUID REFERENCES vendors(id),
    po_date DATE,
    outstanding_amount NUMERIC(15,2),
    days_outstanding INTEGER,
    aging_bucket VARCHAR(20),
    currency VARCHAR(10) DEFAULT 'NGN'
);

-- ============================================================
-- AUDIT TRAIL
-- ============================================================
CREATE TABLE IF NOT EXISTS audit_trail (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID,
    action VARCHAR(50),
    module VARCHAR(100),
    entity_type VARCHAR(100),
    entity_id UUID,
    description TEXT,
    ip_address VARCHAR(50),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
