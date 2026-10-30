# 💼 Apex Sales & Inventory Management System

A production-ready, full-stack **Sales & Inventory Management System** built for college projects, retail businesses, and wholesale operations.

Built entirely with **Python**, **Streamlit**, **SQLite**, **Pandas**, and **Plotly**—no external Node.js, JavaScript, or complex web servers required.

---

## 🌟 Key Features

1. **📊 Executive Dashboard & KPIs**:
   - Real-time KPIs: **Total Revenue**, **Estimated Net Profit**, **Total Orders**, **Average Order Value**, **Active Inventory Value**, and **Low-Stock Alerts**.
   - Dynamic time-interval filter: *Today*, *Last 7 Days*, *Last 30 Days*, *Custom Date Range*, or *All Time*.
   - Interactive charts: Daily revenue vs. profit dynamics, top-selling products, category distribution, and payment channel share.
   - Low-stock warning banner with one-click drilldown.

2. **📦 Inventory & Product Catalog**:
   - Full CRUD: Add, edit, archive/delete, and search/filter products.
   - Stock control: Track cost price vs. selling price, automatically calculate profit margins, and set custom low-stock alert thresholds.
   - Quick Inventory Adjustment: Fast restock or shrinkage logging.
   - Safe Deletion: Automatically prevents corrupting historic invoices by safely archiving products with sales history.

3. **👥 Customer Relationship Management (CRM)**:
   - Add and update customer accounts (Retail, Wholesale, Corporate).
   - Lifetime analytics: Tracks total orders placed and cumulative spend per customer.
   - Purchase History Drilldown: Inspect an individual customer's entire lifetime transaction timeline.

4. **🛒 Point of Sale (POS) & Order Creation**:
   - Interactive cart with live stock validation (prevents overselling).
   - Dynamic discounts: Supports both Percentage (%) and Flat Amount ($) discounts.
   - Configurable Tax / VAT rates.
   - Multiple payment methods: Cash, Credit Card, Debit Card, UPI / Digital Wallet, Bank Transfer.
   - **Atomic Database Transactions**: Automatically deducts product stock in SQLite upon order placement. If an error occurs, changes roll back immediately.

5. **📜 Order History & Professional Invoicing**:
   - Filter and search past transactions by date, order ID, customer, payment status, or fulfillment status.
   - Update order status (Completed, Pending, Cancelled) and payment status (Paid, Pending, Partial).
   - **Automatic Stock Restitution**: Cancelling an order automatically returns items back to warehouse stock.
   - **Official Printable Tax Invoices**: Clean company branding, customer details, itemized line items, tax breakdown, and status badges.

6. **📈 Financial Reporting & Analytics**:
   - Aggregated Daily, Monthly, and Yearly sales summaries.
   - Revenue vs. Cost of Goods Sold (COGS) vs. Net Profit comparisons.
   - Category performance rankings and Top Customer leaderboards.
   - One-click **CSV exports** for all tables and reports.

7. **✨ Sample Demo Data Loader**:
   - Built-in button in the sidebar to populate realistic products, customers, and 30-day historical orders for instant viva/presentation demonstrations.

---

## 🛠️ Technology Stack

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Language** | Python 3.10+ | All backend, database, and UI logic |
| **Frontend UI** | Streamlit | Responsive web application interface |
| **Database** | SQLite 3 | Relational ACID database with Foreign Keys & WAL mode |
| **Data Processing** | Pandas | Financial aggregations, metrics, and CSV exports |
| **Data Visualization** | Plotly Express & Graph Objects | Interactive sales graphs and donut charts |
| **Testing** | Pytest | Automated unit and integration testing |

---

## 📂 Project Architecture

```
SalesManagementSystem/
│
├── app.py                      # Main application entry point & router
├── config.py                   # System configuration, constants, and company profile
├── requirements.txt            # Python package dependencies
├── .gitignore                  # Git ignore rules
├── README.md                   # Project documentation & presentation guide
│
├── database/
│   ├── __init__.py
│   ├── connection.py           # SQLite connection pool, WAL mode, transaction context
│   ├── schema.py               # Table DDL definitions, constraints, indexes
│   └── sample_data.py          # Realistic college demo dataset generator
│
├── services/
│   ├── __init__.py
│   ├── product_service.py      # Product catalog, stock adjustments, low-stock alerts
│   ├── customer_service.py     # Customer management & purchase history
│   ├── order_service.py        # Order transactions, stock deductions, invoice generation
│   └── report_service.py       # Financial analytics, COGS, profit calculations
│
├── ui/
│   ├── __init__.py
│   ├── styles.py               # Modern UI styling, KPI cards, badges, invoice styles
│   ├── dashboard.py            # Dashboard view with charts & metrics
│   ├── products.py             # Product inventory management view
│   ├── customers.py            # Customer directory & history drilldown view
│   ├── orders.py               # Point-of-Sale / Order creation view
│   ├── history.py              # Order history & printable invoice generator
│   └── reports.py              # Sales & profit reports view
│
└── tests/
    ├── __init__.py
    ├── test_calculations.py    # Unit tests for totals, discounts, taxes & profits
    └── test_inventory.py       # Integration tests for stock decrement & rollback
```

---

## 🚀 Step-by-Step Setup Guide (Windows)

### 1. Open Terminal
Open **PowerShell** or **Command Prompt** and navigate to your project directory:
```powershell
cd c:\Users\Abhishek\Desktop\SalesManagementSystem
```

### 2. Create a Virtual Environment
```powershell
python -m venv venv
```

### 3. Activate the Virtual Environment
```powershell
.\venv\Scripts\Activate.ps1
```
*(If on Command Prompt `cmd.exe`, use `venv\Scripts\activate.bat`)*

### 4. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 5. Run Automated Tests
Verify that all calculation logic and inventory transactions pass:
```powershell
pytest tests/
```

### 6. Launch the Application
Run the Streamlit dashboard:
```powershell
python -m streamlit run app.py
```
Your default web browser will open at `http://localhost:8501`.

---

## 🧪 Automated Testing

The project includes an automated test suite verifying core business rules:
- **Discounts & Taxes**: Verifies percentage discounts, flat discounts, subtotal capping, and VAT calculations.
- **Profit Calculations**: Verifies `Revenue - Cost of Goods Sold - Tax`.
- **Inventory Decrement**: Confirms stock is reduced upon completed orders.
- **Stock Guard (Overselling Prevention)**: Verifies that an order is blocked if requested units exceed stock.
- **Order Cancellation Restitution**: Verifies that stock is returned to inventory if an order is cancelled.
- **Data Isolation**: Tests execute against an isolated temporary SQLite database, leaving production data untouched.

Run the test suite anytime:
```powershell
pytest -v tests/
```

---

## 🗄️ Database Entity-Relationship (ER) Overview

- **`products`**: `id`, `sku`, `name`, `category`, `cost_price`, `selling_price`, `stock_quantity`, `low_stock_threshold`, `description`, `is_active`, `created_at`, `updated_at`.
- **`customers`**: `id`, `name`, `email`, `phone`, `address`, `customer_type`, `notes`, `created_at`.
- **`orders`**: `id`, `order_number`, `customer_id`, `order_date`, `subtotal`, `discount_type`, `discount_value`, `discount_amount`, `tax_rate`, `tax_amount`, `total_amount`, `total_cost`, `payment_method`, `payment_status`, `order_status`, `notes`.
- **`order_items`**: `id`, `order_id`, `product_id`, `product_name`, `cost_price`, `unit_price`, `quantity`, `line_total`.

---

## 🎓 College Project Demo / Presentation Tips

1. **First-Time Setup**: Click **"✨ Load Sample Demo Data"** in the sidebar to populate the system with realistic data across products, customers, and past 30-day transactions.
2. **Dashboard**: Show the teacher the **KPI Cards**, the **Low-Stock Alert** table, and how changing time filters dynamically refreshes the Plotly charts.
3. **Inventory**: Add a new product or adjust stock, highlighting the instant margin calculation.
4. **Place a Sale**: Show the **POS order screen**, add items, apply a 10% discount, and complete the order. Point out that the product stock decreased immediately.
5. **Invoice**: Switch to **"Order History & Invoices"** to show the professional tax invoice with customer details and line items.
6. **Code Quality**: Mention **SQLite WAL mode**, **foreign key constraints**, **modular architecture**, and **automated tests**.
