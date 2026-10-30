"""Configuration settings for the Sales Management System."""
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "sales_system.db"

# Application Settings
APP_NAME = "Apex Sales & Inventory Management System"
APP_SUBTITLE = "Smart Retail & Wholesale Operations Portal"
APP_ICON = "💼"
CURRENCY_SYMBOL = "$"

# Default Thresholds
DEFAULT_LOW_STOCK_THRESHOLD = 10
DEFAULT_TAX_RATE = 5.0  # 5% default VAT/Tax

# Category Presets
PRODUCT_CATEGORIES = [
    "Electronics",
    "Apparel & Fashion",
    "Groceries & Food",
    "Home & Kitchen",
    "Books & Stationery",
    "Health & Beauty",
    "Automotive & Tools",
    "Other",
]

# Payment Methods
PAYMENT_METHODS = [
    "Cash",
    "Credit Card",
    "Debit Card",
    "UPI / Digital Wallet",
    "Bank Transfer",
]

# Order and Payment Statuses
ORDER_STATUSES = ["Completed", "Pending", "Cancelled"]
PAYMENT_STATUSES = ["Paid", "Pending", "Partial"]
CUSTOMER_TYPES = ["Retail", "Wholesale", "Corporate"]

# Invoice Header Information
COMPANY_DETAILS = {
    "name": "Apex Retail Solutions Pvt. Ltd.",
    "address": "100 Innovation Boulevard, Tech Park",
    "city": "Metropolis, NY 10001",
    "phone": "+1 (555) 019-2834",
    "email": "billing@apexsolutions.example.com",
    "website": "www.apexsolutions.example.com",
    "tax_id": "TAX-US-987654321",
}
