-- =============================================================================
-- Smart Freight Revenue Management System
-- Complete PostgreSQL Schema
-- Run: psql -U freight_user -d freight_db -f schema.sql
-- =============================================================================

-- ── Extensions ────────────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- MASTER TABLES
-- =============================================================================

CREATE TABLE IF NOT EXISTS roles (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(50)  NOT NULL UNIQUE,
    description TEXT         DEFAULT '',
    permissions JSONB        DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS user_groups (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(100) NOT NULL UNIQUE,
    description TEXT         DEFAULT '',
    status      BOOLEAN      DEFAULT TRUE,
    created_at  TIMESTAMPTZ  DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS currencies (
    id   SERIAL PRIMARY KEY,
    code VARCHAR(5)  NOT NULL UNIQUE,
    name VARCHAR(50) NOT NULL
);

INSERT INTO currencies (code, name) VALUES
    ('INR', 'Indian Rupee'),
    ('USD', 'US Dollar'),
    ('EUR', 'Euro'),
    ('GBP', 'British Pound'),
    ('AED', 'UAE Dirham'),
    ('SGD', 'Singapore Dollar'),
    ('CNY', 'Chinese Yuan')
ON CONFLICT DO NOTHING;

CREATE TABLE IF NOT EXISTS charge_types (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(100) NOT NULL UNIQUE,
    description TEXT         DEFAULT '',
    is_taxable  BOOLEAN      DEFAULT TRUE
);

INSERT INTO charge_types (name, is_taxable) VALUES
    ('Ocean Freight',          TRUE),
    ('Air Freight',            TRUE),
    ('Origin THC',             TRUE),
    ('Destination THC',        TRUE),
    ('Documentation Fee',      TRUE),
    ('B/L Fee',                TRUE),
    ('Inland Haulage',         TRUE),
    ('CFS Charges',            TRUE),
    ('Custom Clearance',       TRUE),
    ('Port Handling',          TRUE),
    ('Insurance',              TRUE),
    ('Fuel Surcharge',         TRUE),
    ('Container Detention',    TRUE),
    ('Demurrage',              TRUE),
    ('Miscellaneous',          TRUE)
ON CONFLICT DO NOTHING;

-- =============================================================================
-- USERS
-- =============================================================================

CREATE TABLE IF NOT EXISTS users (
    id              BIGSERIAL    PRIMARY KEY,
    email           VARCHAR(150) NOT NULL UNIQUE,
    name            VARCHAR(100) NOT NULL,
    password        TEXT         NOT NULL,
    phone           VARCHAR(20)  DEFAULT '',
    role_id         INT          REFERENCES roles(id) ON DELETE SET NULL,
    group_id        INT          REFERENCES user_groups(id) ON DELETE SET NULL,
    employee_id     VARCHAR(30)  UNIQUE,
    is_active       BOOLEAN      DEFAULT TRUE,
    is_staff        BOOLEAN      DEFAULT FALSE,
    is_superuser    BOOLEAN      DEFAULT FALSE,
    last_login_ip   INET,
    profile_picture TEXT         DEFAULT '',
    created_at      TIMESTAMPTZ  DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email  ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role   ON users(role_id);

-- =============================================================================
-- AUDIT LOG
-- =============================================================================

CREATE TABLE IF NOT EXISTS audit_logs (
    id               BIGSERIAL   PRIMARY KEY,
    table_name       VARCHAR(80) NOT NULL,
    record_id        BIGINT,
    action           VARCHAR(20) NOT NULL,
    endpoint         VARCHAR(255) DEFAULT '',
    changed_by_id    BIGINT      REFERENCES users(id) ON DELETE SET NULL,
    ip_address       INET,
    changed_at       TIMESTAMPTZ DEFAULT NOW(),
    payload_snapshot JSONB
);

CREATE INDEX IF NOT EXISTS idx_audit_table    ON audit_logs(table_name, record_id);
CREATE INDEX IF NOT EXISTS idx_audit_user     ON audit_logs(changed_by_id);
CREATE INDEX IF NOT EXISTS idx_audit_datetime ON audit_logs(changed_at);

-- =============================================================================
-- CUSTOMERS
-- =============================================================================

CREATE TABLE IF NOT EXISTS customers (
    id                  BIGSERIAL      PRIMARY KEY,
    company_name        VARCHAR(200)   NOT NULL,
    business_type       VARCHAR(30)    DEFAULT 'trader',
    gst                 VARCHAR(20)    UNIQUE,
    pan                 VARCHAR(12)    DEFAULT '',
    iec                 VARCHAR(15)    DEFAULT '',
    credit_limit        DECIMAL(14,2)  DEFAULT 0,
    credit_days         SMALLINT       DEFAULT 30,
    outstanding_balance DECIMAL(14,2)  DEFAULT 0,
    website             VARCHAR(200)   DEFAULT '',
    notes               TEXT           DEFAULT '',
    status              VARCHAR(15)    DEFAULT 'active',
    assigned_to_id      BIGINT         REFERENCES users(id) ON DELETE SET NULL,
    created_by_id       BIGINT         REFERENCES users(id) ON DELETE SET NULL,
    updated_by_id       BIGINT         REFERENCES users(id) ON DELETE SET NULL,
    created_at          TIMESTAMPTZ    DEFAULT NOW(),
    updated_at          TIMESTAMPTZ    DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_customers_gst    ON customers(gst);
CREATE INDEX IF NOT EXISTS idx_customers_status ON customers(status);

CREATE TABLE IF NOT EXISTS customer_contacts (
    id          BIGSERIAL    PRIMARY KEY,
    customer_id BIGINT       NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    name        VARCHAR(100) NOT NULL,
    designation VARCHAR(80)  DEFAULT '',
    phone       VARCHAR(20)  DEFAULT '',
    email       VARCHAR(150) DEFAULT '',
    is_primary  BOOLEAN      DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS customer_addresses (
    id           BIGSERIAL   PRIMARY KEY,
    customer_id  BIGINT      NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    address_type VARCHAR(15) DEFAULT 'both',
    address_line TEXT        NOT NULL,
    city         VARCHAR(80) NOT NULL,
    state        VARCHAR(80) DEFAULT '',
    country      VARCHAR(80) DEFAULT 'India',
    pin_code     VARCHAR(12) DEFAULT '',
    is_default   BOOLEAN     DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS customer_documents (
    id            BIGSERIAL    PRIMARY KEY,
    customer_id   BIGINT       NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    document_type VARCHAR(30)  NOT NULL,
    file_name     VARCHAR(200) NOT NULL,
    file_url      TEXT         NOT NULL,
    is_verified   BOOLEAN      DEFAULT FALSE,
    uploaded_by_id BIGINT      REFERENCES users(id) ON DELETE SET NULL,
    uploaded_at   TIMESTAMPTZ  DEFAULT NOW()
);

-- =============================================================================
-- VENDORS
-- =============================================================================

CREATE TABLE IF NOT EXISTS vendors (
    id              BIGSERIAL      PRIMARY KEY,
    name            VARCHAR(200)   NOT NULL,
    service_type    VARCHAR(20)    NOT NULL,
    gst             VARCHAR(20)    UNIQUE,
    pan             VARCHAR(12)    DEFAULT '',
    contact_name    VARCHAR(100)   DEFAULT '',
    contact_email   VARCHAR(150)   DEFAULT '',
    contact_phone   VARCHAR(20)    DEFAULT '',
    address         TEXT           DEFAULT '',
    bank_name       VARCHAR(100)   DEFAULT '',
    bank_account    VARCHAR(30)    DEFAULT '',
    bank_ifsc       VARCHAR(15)    DEFAULT '',
    credit_limit    DECIMAL(14,2)  DEFAULT 0,
    credit_days     SMALLINT       DEFAULT 30,
    status          VARCHAR(15)    DEFAULT 'active',
    notes           TEXT           DEFAULT '',
    created_by_id   BIGINT         REFERENCES users(id) ON DELETE SET NULL,
    updated_by_id   BIGINT         REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ    DEFAULT NOW(),
    updated_at      TIMESTAMPTZ    DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_vendors_service ON vendors(service_type, status);

CREATE TABLE IF NOT EXISTS vendor_rates (
    id            BIGSERIAL      PRIMARY KEY,
    vendor_id     BIGINT         NOT NULL REFERENCES vendors(id) ON DELETE CASCADE,
    service_desc  VARCHAR(200)   NOT NULL,
    origin        VARCHAR(150)   DEFAULT '',
    destination   VARCHAR(150)   DEFAULT '',
    mode          VARCHAR(20)    DEFAULT '',
    rate          DECIMAL(12,2)  NOT NULL,
    currency      VARCHAR(5)     DEFAULT 'INR',
    unit          VARCHAR(30)    DEFAULT '',
    valid_from    DATE           NOT NULL,
    valid_to      DATE,
    created_at    TIMESTAMPTZ    DEFAULT NOW()
);

-- =============================================================================
-- QUOTATIONS
-- =============================================================================

CREATE TABLE IF NOT EXISTS quotations (
    id               BIGSERIAL      PRIMARY KEY,
    quotation_number VARCHAR(30)    NOT NULL UNIQUE,
    customer_id      BIGINT         NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
    origin           VARCHAR(150)   NOT NULL,
    destination      VARCHAR(150)   NOT NULL,
    mode             VARCHAR(15)    NOT NULL,
    incoterms        VARCHAR(10)    DEFAULT '',
    cargo_type       VARCHAR(80)    DEFAULT '',
    cargo_ready_date DATE,
    delivery_date    DATE,
    validity_date    DATE,
    currency         VARCHAR(5)     DEFAULT 'INR',
    exchange_rate    DECIMAL(10,4)  DEFAULT 1.0,
    subtotal         DECIMAL(14,2)  DEFAULT 0,
    gst_percent      DECIMAL(5,2)   DEFAULT 18.0,
    gst_amount       DECIMAL(14,2)  DEFAULT 0,
    total_amount     DECIMAL(14,2)  DEFAULT 0,
    status           VARCHAR(15)    DEFAULT 'draft',
    notes            TEXT           DEFAULT '',
    terms_conditions TEXT           DEFAULT '',
    created_by_id    BIGINT         REFERENCES users(id) ON DELETE SET NULL,
    updated_by_id    BIGINT         REFERENCES users(id) ON DELETE SET NULL,
    created_at       TIMESTAMPTZ    DEFAULT NOW(),
    updated_at       TIMESTAMPTZ    DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_quotations_customer ON quotations(customer_id);
CREATE INDEX IF NOT EXISTS idx_quotations_status   ON quotations(status);
CREATE INDEX IF NOT EXISTS idx_quotations_number   ON quotations(quotation_number);

CREATE TABLE IF NOT EXISTS quotation_items (
    id              BIGSERIAL      PRIMARY KEY,
    quotation_id    BIGINT         NOT NULL REFERENCES quotations(id) ON DELETE CASCADE,
    charge_type_id  INT            NOT NULL REFERENCES charge_types(id) ON DELETE RESTRICT,
    description     VARCHAR(200)   DEFAULT '',
    quantity        DECIMAL(10,3)  DEFAULT 1,
    unit            VARCHAR(20)    DEFAULT '',
    unit_price      DECIMAL(12,2)  NOT NULL,
    amount          DECIMAL(14,2)  NOT NULL
);

-- =============================================================================
-- SHIPMENTS
-- =============================================================================

CREATE TABLE IF NOT EXISTS shipments (
    id                  BIGSERIAL      PRIMARY KEY,
    shipment_number     VARCHAR(30)    NOT NULL UNIQUE,
    quotation_id        BIGINT         UNIQUE REFERENCES quotations(id) ON DELETE SET NULL,
    customer_id         BIGINT         NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
    vendor_id           BIGINT         REFERENCES vendors(id) ON DELETE SET NULL,
    mode                VARCHAR(15)    NOT NULL,
    origin              VARCHAR(150)   NOT NULL,
    destination         VARCHAR(150)   NOT NULL,
    port_of_loading     VARCHAR(150)   DEFAULT '',
    port_of_discharge   VARCHAR(150)   DEFAULT '',
    carrier_name        VARCHAR(100)   DEFAULT '',
    vessel_name         VARCHAR(100)   DEFAULT '',
    voyage_number       VARCHAR(50)    DEFAULT '',
    mbl_number          VARCHAR(50)    DEFAULT '',
    hbl_number          VARCHAR(50)    DEFAULT '',
    awb_number          VARCHAR(50)    DEFAULT '',
    etd                 DATE,
    eta                 DATE,
    atd                 DATE,
    ata                 DATE,
    currency            VARCHAR(5)     DEFAULT 'INR',
    selling_amount      DECIMAL(14,2)  DEFAULT 0,
    buying_amount       DECIMAL(14,2)  DEFAULT 0,
    status              VARCHAR(25)    DEFAULT 'booked',
    notes               TEXT           DEFAULT '',
    created_by_id       BIGINT         REFERENCES users(id) ON DELETE SET NULL,
    updated_by_id       BIGINT         REFERENCES users(id) ON DELETE SET NULL,
    created_at          TIMESTAMPTZ    DEFAULT NOW(),
    updated_at          TIMESTAMPTZ    DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_shipments_customer ON shipments(customer_id);
CREATE INDEX IF NOT EXISTS idx_shipments_status   ON shipments(status);
CREATE INDEX IF NOT EXISTS idx_shipments_number   ON shipments(shipment_number);
CREATE INDEX IF NOT EXISTS idx_shipments_eta      ON shipments(eta);

CREATE TABLE IF NOT EXISTS containers (
    id               BIGSERIAL      PRIMARY KEY,
    shipment_id      BIGINT         NOT NULL REFERENCES shipments(id) ON DELETE CASCADE,
    container_number VARCHAR(15)    DEFAULT '',
    container_type   VARCHAR(10)    NOT NULL,
    seal_number      VARCHAR(30)    DEFAULT '',
    gross_weight     DECIMAL(10,3),
    cbm              DECIMAL(10,3),
    packages         INT            DEFAULT 0,
    description      VARCHAR(200)   DEFAULT ''
);

CREATE TABLE IF NOT EXISTS shipment_tracking (
    id           BIGSERIAL    PRIMARY KEY,
    shipment_id  BIGINT       NOT NULL REFERENCES shipments(id) ON DELETE CASCADE,
    status       VARCHAR(25)  NOT NULL,
    location     VARCHAR(150) DEFAULT '',
    description  TEXT         DEFAULT '',
    event_date   TIMESTAMPTZ  NOT NULL,
    recorded_by_id BIGINT     REFERENCES users(id) ON DELETE SET NULL,
    created_at   TIMESTAMPTZ  DEFAULT NOW()
);

-- =============================================================================
-- INVOICES
-- =============================================================================

CREATE TABLE IF NOT EXISTS invoices (
    id              BIGSERIAL      PRIMARY KEY,
    invoice_number  VARCHAR(30)    NOT NULL UNIQUE,
    invoice_type    VARCHAR(20)    DEFAULT 'tax_invoice',
    customer_id     BIGINT         NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
    shipment_id     BIGINT         UNIQUE REFERENCES shipments(id) ON DELETE SET NULL,
    invoice_date    DATE           DEFAULT CURRENT_DATE,
    due_date        DATE,
    currency        VARCHAR(5)     DEFAULT 'INR',
    exchange_rate   DECIMAL(10,4)  DEFAULT 1.0,
    subtotal        DECIMAL(14,2)  DEFAULT 0,
    discount_amount DECIMAL(14,2)  DEFAULT 0,
    is_interstate   BOOLEAN        DEFAULT TRUE,
    igst_percent    DECIMAL(5,2)   DEFAULT 0,
    igst_amount     DECIMAL(14,2)  DEFAULT 0,
    cgst_percent    DECIMAL(5,2)   DEFAULT 0,
    cgst_amount     DECIMAL(14,2)  DEFAULT 0,
    sgst_percent    DECIMAL(5,2)   DEFAULT 0,
    sgst_amount     DECIMAL(14,2)  DEFAULT 0,
    total_gst       DECIMAL(14,2)  DEFAULT 0,
    total_amount    DECIMAL(14,2)  DEFAULT 0,
    amount_paid     DECIMAL(14,2)  DEFAULT 0,
    balance_due     DECIMAL(14,2)  DEFAULT 0,
    status          VARCHAR(15)    DEFAULT 'draft',
    notes           TEXT           DEFAULT '',
    terms           TEXT           DEFAULT '',
    pdf_url         TEXT           DEFAULT '',
    created_by_id   BIGINT         REFERENCES users(id) ON DELETE SET NULL,
    updated_by_id   BIGINT         REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ    DEFAULT NOW(),
    updated_at      TIMESTAMPTZ    DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_invoices_customer ON invoices(customer_id);
CREATE INDEX IF NOT EXISTS idx_invoices_status   ON invoices(status);
CREATE INDEX IF NOT EXISTS idx_invoices_number   ON invoices(invoice_number);
CREATE INDEX IF NOT EXISTS idx_invoices_due_date ON invoices(due_date);

CREATE TABLE IF NOT EXISTS invoice_items (
    id          BIGSERIAL      PRIMARY KEY,
    invoice_id  BIGINT         NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    description VARCHAR(200)   NOT NULL,
    hsn_sac     VARCHAR(10)    DEFAULT '',
    quantity    DECIMAL(10,3)  DEFAULT 1,
    unit        VARCHAR(20)    DEFAULT '',
    unit_price  DECIMAL(12,2)  NOT NULL,
    amount      DECIMAL(14,2)  NOT NULL
);

-- =============================================================================
-- PAYMENTS
-- =============================================================================

CREATE TABLE IF NOT EXISTS payments (
    id               BIGSERIAL      PRIMARY KEY,
    payment_number   VARCHAR(30)    NOT NULL UNIQUE,
    customer_id      BIGINT         NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
    invoice_id       BIGINT         NOT NULL REFERENCES invoices(id)  ON DELETE RESTRICT,
    amount           DECIMAL(14,2)  NOT NULL CHECK (amount > 0),
    currency         VARCHAR(5)     DEFAULT 'INR',
    exchange_rate    DECIMAL(10,4)  DEFAULT 1.0,
    payment_method   VARCHAR(20)    NOT NULL,
    reference_number VARCHAR(100)   DEFAULT '',
    payment_date     DATE           NOT NULL,
    bank_account     VARCHAR(100)   DEFAULT '',
    notes            TEXT           DEFAULT '',
    status           VARCHAR(15)    DEFAULT 'pending',
    reconciled       BOOLEAN        DEFAULT FALSE,
    reconciled_by_id BIGINT         REFERENCES users(id) ON DELETE SET NULL,
    reconciled_at    TIMESTAMPTZ,
    created_by_id    BIGINT         REFERENCES users(id) ON DELETE SET NULL,
    updated_by_id    BIGINT         REFERENCES users(id) ON DELETE SET NULL,
    created_at       TIMESTAMPTZ    DEFAULT NOW(),
    updated_at       TIMESTAMPTZ    DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_payments_customer     ON payments(customer_id);
CREATE INDEX IF NOT EXISTS idx_payments_invoice      ON payments(invoice_id);
CREATE INDEX IF NOT EXISTS idx_payments_status       ON payments(status);
CREATE INDEX IF NOT EXISTS idx_payments_date         ON payments(payment_date);

CREATE TABLE IF NOT EXISTS transactions (
    id          BIGSERIAL      PRIMARY KEY,
    payment_id  BIGINT         NOT NULL REFERENCES payments(id) ON DELETE CASCADE,
    tx_type     VARCHAR(10)    NOT NULL,
    account     VARCHAR(80)    NOT NULL,
    amount      DECIMAL(14,2)  NOT NULL,
    narration   VARCHAR(200)   DEFAULT '',
    created_at  TIMESTAMPTZ    DEFAULT NOW()
);

-- =============================================================================
-- VENDOR PAYMENTS
-- =============================================================================

CREATE TABLE IF NOT EXISTS vendor_payments (
    id               BIGSERIAL      PRIMARY KEY,
    payment_number   VARCHAR(30)    NOT NULL UNIQUE,
    vendor_id        BIGINT         NOT NULL REFERENCES vendors(id)   ON DELETE RESTRICT,
    shipment_id      BIGINT         REFERENCES shipments(id) ON DELETE SET NULL,
    amount           DECIMAL(14,2)  NOT NULL CHECK (amount > 0),
    currency         VARCHAR(5)     DEFAULT 'INR',
    payment_method   VARCHAR(30)    DEFAULT '',
    reference_number VARCHAR(100)   DEFAULT '',
    payment_date     DATE,
    due_date         DATE,
    description      VARCHAR(200)   DEFAULT '',
    status           VARCHAR(15)    DEFAULT 'pending',
    created_by_id    BIGINT         REFERENCES users(id) ON DELETE SET NULL,
    updated_by_id    BIGINT         REFERENCES users(id) ON DELETE SET NULL,
    created_at       TIMESTAMPTZ    DEFAULT NOW(),
    updated_at       TIMESTAMPTZ    DEFAULT NOW()
);

-- =============================================================================
-- SEED DATA — Default Roles
-- =============================================================================

INSERT INTO roles (name, description) VALUES
    ('super_admin', 'Full system access'),
    ('admin',       'Full API access'),
    ('manager',     'All modules; no user deletion'),
    ('sales',       'Customers, Quotations, read-only Shipments'),
    ('operations',  'Shipments, Containers, Tracking'),
    ('accounts',    'Invoices, Payments, AR/AP, Reports'),
    ('viewer',      'Read-only across all modules')
ON CONFLICT DO NOTHING;

-- =============================================================================
-- DONE
-- =============================================================================
-- Run after schema creation:
--   python manage.py migrate
--   python manage.py createsuperuser
