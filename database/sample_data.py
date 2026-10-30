"""Sample data seeder for the Sales Management System.
Generates realistic products, customers, and order history for college demos.
"""
from datetime import datetime, timedelta
import random
from typing import Optional
from pathlib import Path
from .connection import get_connection
from .schema import init_db

SAMPLE_PRODUCTS = [
    # (sku, name, category, cost_price, selling_price, stock_quantity, low_stock_threshold, description)
    ("ELEC-101", "Wireless Ergonomic Mouse", "Electronics", 15.00, 29.99, 45, 10, "Optical wireless mouse with rechargeable battery and silent click."),
    ("ELEC-102", "RGB Mechanical Keyboard", "Electronics", 35.00, 69.99, 28, 8, "Mechanical keyboard with brown switches and customizable RGB backlighting."),
    ("ELEC-103", "USB-C Multiport Adapter 7-in-1", "Electronics", 18.50, 39.50, 15, 5, "Includes 4K HDMI, 100W PD charging, and 3x USB 3.0 ports."),
    ("ELEC-104", "27-inch 4K IPS Monitor", "Electronics", 180.00, 279.99, 8, 5, "Ultra-thin bezel, 99% sRGB color gamut, HDR400 display."),
    ("ELEC-105", "Noise-Cancelling Headphones", "Electronics", 45.00, 89.99, 6, 10, "Over-ear Bluetooth headphones with active noise cancellation."),
    ("ELEC-106", "Fast Wireless Charging Stand", "Electronics", 10.00, 22.00, 3, 10, "15W fast charging stand for Qi-enabled devices."),  # Low stock on purpose
    
    ("APP-201", "Organic Cotton Crewneck T-Shirt", "Apparel & Fashion", 8.00, 19.99, 60, 15, "100% combed organic ring-spun cotton unisex t-shirt."),
    ("APP-202", "Classic Denim Jacket", "Apparel & Fashion", 24.00, 54.99, 22, 5, "Durable vintage-wash denim jacket with copper buttons."),
    ("APP-203", "Everyday Chino Trousers", "Apparel & Fashion", 16.00, 39.00, 30, 10, "Comfortable stretch twill trousers suitable for office or casual wear."),
    ("APP-204", "Athletic Fleece Pullover Hoodie", "Apparel & Fashion", 19.00, 44.50, 18, 8, "Breathable cotton-polyester blend activewear hoodie."),

    ("GROC-301", "Artisan Dark Roast Coffee Beans 1kg", "Groceries & Food", 9.50, 18.99, 50, 12, "Single-origin Arabica beans roasted with hints of dark chocolate."),
    ("GROC-302", "Organic Japanese Matcha Green Tea 100g", "Groceries & Food", 11.00, 24.50, 4, 10, "Ceremonial grade pure matcha powder."),  # Low stock on purpose
    ("GROC-303", "Raw Almonds & Walnuts Mix 500g", "Groceries & Food", 6.00, 13.50, 40, 10, "Non-GMO heart-healthy nut mix packed fresh."),

    ("HOME-401", "Insulated Stainless Steel Water Bottle 1L", "Home & Kitchen", 7.50, 19.99, 35, 10, "Double-walled vacuum insulated, keeps liquids cold 24 hrs."),
    ("HOME-402", "Granite Non-Stick Frying Pan 28cm", "Home & Kitchen", 14.00, 32.00, 14, 5, "PFOA-free durable granite-coated cooking pan with induction base."),
    ("HOME-403", "Aroma Essential Oil Diffuser 500ml", "Home & Kitchen", 12.00, 26.99, 20, 6, "Ultrasonic cool mist humidifier with 7 color ambient LEDs."),

    ("STAT-501", "Hardcover Bullet Grid Notebook", "Books & Stationery", 4.00, 12.50, 45, 10, "160 GSM bleed-proof bamboo paper with expanding inner pocket."),
    ("STAT-502", "Fine Line Gel Pen Set (Pack of 10)", "Books & Stationery", 3.50, 9.99, 2, 15, "0.5mm smooth quick-drying archival black ink pens."),  # Low stock on purpose
]

SAMPLE_CUSTOMERS = [
    ("Aarav Sharma", "aarav.sharma@example.com", "+1-555-0101", "124 Oak Street, Suite 4B", "Retail", "Regular customer, prefers tech accessories."),
    ("Sophia Martinez", "sophia.m@example.com", "+1-555-0102", "742 Evergreen Terrace", "Retail", "Prefers weekend deliveries."),
    ("Marcus Chen", "marcus.chen@example.com", "+1-555-0103", "88 Industrial Pkwy", "Wholesale", "Corporate buyer for local tech startup."),
    ("Priya Patel", "priya.patel@example.com", "+1-555-0104", "512 Maple Avenue", "Retail", "Loyal repeat customer for home goods."),
    ("David Miller", "david.m@example.com", "+1-555-0105", "1032 Pine Ridge Rd", "Wholesale", "Runs a student retail club."),
    ("Emma Watson", "emma.w@example.com", "+1-555-0106", "310 Riverdale Boulevard", "Retail", "Frequently buys stationery and books."),
    ("Liam Johnson", "liam.j@example.com", "+1-555-0107", "404 Northpoint Dr", "Retail", "Walk-in retail customer."),
    ("TechNova Innovations", "procurement@technova.example.com", "+1-555-0199", "1200 Silicon Ave", "Corporate", "B2B enterprise account."),
]


def seed_sample_data(db_path: Optional[Path] = None, force: bool = False) -> dict:
    """Populate database with sample products, customers, and orders if empty.
    
    Returns a dictionary summarizing the seeded counts.
    """
    init_db(db_path)
    conn = get_connection(db_path)
    
    try:
        cursor = conn.cursor()
        
        # Check if products already exist
        cursor.execute("SELECT COUNT(*) FROM products")
        existing_products = cursor.fetchone()[0]
        
        if existing_products > 0 and not force:
            return {"status": "skipped", "message": "Database already contains data."}
            
        if force:
            # Clear existing data safely
            cursor.execute("DELETE FROM order_items")
            cursor.execute("DELETE FROM orders")
            cursor.execute("DELETE FROM products")
            cursor.execute("DELETE FROM customers")
            
        # 1. Insert Products
        inserted_product_ids = []
        for p in SAMPLE_PRODUCTS:
            cursor.execute("""
                INSERT INTO products (sku, name, category, cost_price, selling_price, stock_quantity, low_stock_threshold, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, p)
            inserted_product_ids.append(cursor.lastrowid)
            
        # 2. Insert Customers
        inserted_customer_ids = []
        for c in SAMPLE_CUSTOMERS:
            cursor.execute("""
                INSERT INTO customers (name, email, phone, address, customer_type, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, c)
            inserted_customer_ids.append(cursor.lastrowid)
            
        # 3. Fetch inserted products info for realistic orders
        cursor.execute("SELECT id, name, cost_price, selling_price FROM products")
        products_pool = cursor.fetchall()
        
        # 4. Generate ~25 realistic orders spread over the last 30 days
        payment_methods = ["Cash", "Credit Card", "UPI / Digital Wallet", "Bank Transfer"]
        order_count = 0
        now = datetime.now()
        
        random.seed(42)  # Deterministic seed for reproducible college demo
        
        for i in range(1, 26):
            # Distribute dates over past 30 days
            days_ago = random.randint(0, 28)
            order_date = (now - timedelta(days=days_ago, hours=random.randint(1, 10), minutes=random.randint(0, 50))).strftime("%Y-%m-%d %H:%M:%S")
            customer_id = random.choice(inserted_customer_ids)
            order_number = f"ORD-{order_date[:10].replace('-', '')}-{i:04d}"
            
            # Select 1 to 4 distinct products
            selected_items = random.sample(products_pool, k=random.randint(1, 4))
            
            subtotal = 0.0
            total_cost = 0.0
            order_items_to_insert = []
            
            for prod in selected_items:
                p_id, p_name, c_price, s_price = prod[0], prod[1], prod[2], prod[3]
                qty = random.randint(1, 3)
                line_tot = round(s_price * qty, 2)
                line_cost = round(c_price * qty, 2)
                
                subtotal += line_tot
                total_cost += line_cost
                order_items_to_insert.append((p_id, p_name, c_price, s_price, qty, line_tot))
            
            # Discount
            discount_type = random.choice(["Percentage", "None"])
            if discount_type == "Percentage" and random.random() > 0.4:
                discount_pct = random.choice([5.0, 10.0, 15.0])
                discount_amount = round(subtotal * (discount_pct / 100.0), 2)
                discount_value = discount_pct
            else:
                discount_type = "Fixed"
                discount_value = 0.0
                discount_amount = 0.0
                
            tax_rate = 5.0
            taxable_amount = max(0.0, subtotal - discount_amount)
            tax_amount = round(taxable_amount * (tax_rate / 100.0), 2)
            total_amount = round(taxable_amount + tax_amount, 2)
            
            payment_method = random.choice(payment_methods)
            payment_status = "Paid" if random.random() > 0.1 else "Pending"
            order_status = "Completed" if payment_status == "Paid" else "Pending"
            
            cursor.execute("""
                INSERT INTO orders (
                    order_number, customer_id, order_date, subtotal, 
                    discount_type, discount_value, discount_amount, 
                    tax_rate, tax_amount, total_amount, total_cost, 
                    payment_method, payment_status, order_status, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order_number, customer_id, order_date, subtotal,
                discount_type, discount_value, discount_amount,
                tax_rate, tax_amount, total_amount, total_cost,
                payment_method, payment_status, order_status, "College demo sample transaction"
            ))
            
            order_id = cursor.lastrowid
            order_count += 1
            
            for item in order_items_to_insert:
                cursor.execute("""
                    INSERT INTO order_items (order_id, product_id, product_name, cost_price, unit_price, quantity, line_total)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (order_id, item[0], item[1], item[2], item[3], item[4], item[5]))
        
        conn.commit()
        return {
            "status": "success",
            "products_count": len(SAMPLE_PRODUCTS),
            "customers_count": len(SAMPLE_CUSTOMERS),
            "orders_count": order_count,
            "message": f"Successfully loaded {len(SAMPLE_PRODUCTS)} products, {len(SAMPLE_CUSTOMERS)} customers, and {order_count} orders."
        }
    finally:
        conn.close()
