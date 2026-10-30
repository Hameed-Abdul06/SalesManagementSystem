"""Order Service: Core transactional engine handling order creation, stock adjustments, and invoicing."""
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from database.connection import get_connection, get_db_cursor
import config


def calculate_order_totals(
    items: List[Dict[str, Any]],
    discount_type: str = "Percentage",
    discount_value: float = 0.0,
    tax_rate: float = 0.0
) -> Dict[str, float]:
    """Calculate subtotal, discount, tax, total, and cost of goods sold.
    
    items: list of dicts with 'unit_price', 'cost_price', 'quantity'
    """
    if discount_value < 0:
        raise ValueError("Discount value cannot be negative.")
    if tax_rate < 0:
        raise ValueError("Tax rate cannot be negative.")

    subtotal = 0.0
    total_cost = 0.0

    for item in items:
        qty = int(item.get("quantity", 1))
        if qty <= 0:
            raise ValueError(f"Quantity for item '{item.get('name', 'Product')}' must be greater than zero.")
        price = float(item.get("unit_price", 0.0))
        cost = float(item.get("cost_price", 0.0))

        subtotal += price * qty
        total_cost += cost * qty

    subtotal = round(subtotal, 2)
    total_cost = round(total_cost, 2)

    # Calculate Discount
    if discount_type == "Percentage":
        discount_amount = round(subtotal * (min(100.0, discount_value) / 100.0), 2)
    else:  # Fixed Amount
        discount_amount = round(min(subtotal, discount_value), 2)

    taxable = max(0.0, subtotal - discount_amount)
    tax_amount = round(taxable * (tax_rate / 100.0), 2)
    total_amount = round(taxable + tax_amount, 2)

    return {
        "subtotal": subtotal,
        "discount_type": discount_type,
        "discount_value": round(discount_value, 2),
        "discount_amount": discount_amount,
        "tax_rate": round(tax_rate, 2),
        "tax_amount": tax_amount,
        "total_amount": total_amount,
        "total_cost": total_cost,
        "estimated_profit": round(total_amount - total_cost - tax_amount, 2)
    }


def generate_order_number() -> str:
    """Generate a unique timestamped order number."""
    now_str = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"ORD-{now_str}"


def create_order(
    customer_id: Optional[int],
    items: List[Dict[str, Any]],
    payment_method: str = "Cash",
    payment_status: str = "Paid",
    order_status: str = "Completed",
    discount_type: str = "Percentage",
    discount_value: float = 0.0,
    tax_rate: float = config.DEFAULT_TAX_RATE,
    notes: str = ""
) -> Dict[str, Any]:
    """Atomically create an order, record line items, and deduct inventory stock.
    
    If any product lacks sufficient stock, rolls back and raises an exception.
    """
    if not items:
        raise ValueError("Cannot place an empty order. Please add at least one product.")

    if payment_method not in config.PAYMENT_METHODS:
        raise ValueError(f"Invalid payment method: {payment_method}")

    # Calculate financial breakdown
    calc = calculate_order_totals(items, discount_type, discount_value, tax_rate)
    order_number = generate_order_number()

    with get_db_cursor() as cursor:
        # Step 1: Pre-check stock levels for all products
        for item in items:
            p_id = item["product_id"]
            qty = item["quantity"]

            cursor.execute("SELECT name, stock_quantity, cost_price, selling_price FROM products WHERE id = ?", (p_id,))
            prod = cursor.fetchone()
            if not prod:
                raise ValueError(f"Product ID {p_id} does not exist.")

            if prod["stock_quantity"] < qty:
                raise ValueError(
                    f"Insufficient stock for '{prod['name']}'. Requested: {qty}, Available: {prod['stock_quantity']}."
                )

        # Step 2: Insert the parent Order record
        cursor.execute("""
            INSERT INTO orders (
                order_number, customer_id, order_date, subtotal,
                discount_type, discount_value, discount_amount,
                tax_rate, tax_amount, total_amount, total_cost,
                payment_method, payment_status, order_status, notes
            ) VALUES (?, ?, CURRENT_TIMESTAMP, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            order_number, customer_id, calc["subtotal"],
            calc["discount_type"], calc["discount_value"], calc["discount_amount"],
            calc["tax_rate"], calc["tax_amount"], calc["total_amount"], calc["total_cost"],
            payment_method, payment_status, order_status, notes
        ))
        order_id = cursor.lastrowid

        # Step 3: Insert Order Items and reduce Inventory Stock
        for item in items:
            p_id = item["product_id"]
            qty = item["quantity"]
            unit_price = item["unit_price"]
            cost_price = item["cost_price"]
            line_total = round(unit_price * qty, 2)

            cursor.execute("""
                INSERT INTO order_items (
                    order_id, product_id, product_name, cost_price, unit_price, quantity, line_total
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (order_id, p_id, item["name"], cost_price, unit_price, qty, line_total))

            # Only decrement stock if the order status is Completed or Pending
            if order_status in ["Completed", "Pending"]:
                cursor.execute("""
                    UPDATE products
                    SET stock_quantity = stock_quantity - ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (qty, p_id))

    return get_order_by_id(order_id)


def get_all_orders(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    customer_id: Optional[int] = None,
    payment_status: Optional[str] = None,
    payment_method: Optional[str] = None,
    order_status: Optional[str] = None,
    search_query: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Retrieve filtered orders with customer details."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        query = """
            SELECT o.*, 
                   COALESCE(c.name, 'Walk-in Customer') AS customer_name,
                   c.phone AS customer_phone,
                   c.email AS customer_email,
                   COUNT(oi.id) AS item_count
            FROM orders o
            LEFT JOIN customers c ON o.customer_id = c.id
            LEFT JOIN order_items oi ON o.id = oi.order_id
            WHERE 1=1
        """
        params = []

        if start_date:
            query += " AND DATE(o.order_date) >= DATE(?)"
            params.append(start_date)

        if end_date:
            query += " AND DATE(o.order_date) <= DATE(?)"
            params.append(end_date)

        if customer_id:
            query += " AND o.customer_id = ?"
            params.append(customer_id)

        if payment_status and payment_status != "All":
            query += " AND o.payment_status = ?"
            params.append(payment_status)

        if payment_method and payment_method != "All":
            query += " AND o.payment_method = ?"
            params.append(payment_method)

        if order_status and order_status != "All":
            query += " AND o.order_status = ?"
            params.append(order_status)

        if search_query:
            term = f"%{search_query.strip()}%"
            query += " AND (o.order_number LIKE ? OR c.name LIKE ? OR c.phone LIKE ?)"
            params.extend([term, term, term])

        query += " GROUP BY o.id ORDER BY o.order_date DESC"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_order_by_id(order_id: int) -> Optional[Dict[str, Any]]:
    """Fetch complete order details including its line items and customer information."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        query = """
            SELECT o.*, 
                   COALESCE(c.name, 'Walk-in Customer') AS customer_name,
                   c.email AS customer_email,
                   c.phone AS customer_phone,
                   c.address AS customer_address,
                   c.customer_type
            FROM orders o
            LEFT JOIN customers c ON o.customer_id = c.id
            WHERE o.id = ?
        """
        cursor.execute(query, (order_id,))
        order_row = cursor.fetchone()
        if not order_row:
            return None

        order_dict = dict(order_row)

        cursor.execute("""
            SELECT oi.*, p.sku
            FROM order_items oi
            LEFT JOIN products p ON oi.product_id = p.id
            WHERE oi.order_id = ?
        """, (order_id,))
        order_dict["items"] = [dict(r) for r in cursor.fetchall()]

        return order_dict
    finally:
        conn.close()


def update_order_status(order_id: int, new_status: str) -> Dict[str, Any]:
    """Update order status with automatic stock restitution if cancelled."""
    if new_status not in config.ORDER_STATUSES:
        raise ValueError(f"Invalid order status: {new_status}")

    with get_db_cursor() as cursor:
        cursor.execute("SELECT order_status FROM orders WHERE id = ?", (order_id,))
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Order ID {order_id} not found.")

        old_status = row["order_status"]
        if old_status == new_status:
            return get_order_by_id(order_id)

        # Retrieve items
        cursor.execute("SELECT product_id, quantity FROM order_items WHERE order_id = ?", (order_id,))
        items = cursor.fetchall()

        # If transitioning to Cancelled from an active order: restore stock
        if new_status == "Cancelled" and old_status in ["Completed", "Pending"]:
            for item in items:
                cursor.execute("""
                    UPDATE products
                    SET stock_quantity = stock_quantity + ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (item["quantity"], item["product_id"]))

        # If reviving a Cancelled order back to Completed/Pending: deduct stock
        elif old_status == "Cancelled" and new_status in ["Completed", "Pending"]:
            for item in items:
                cursor.execute("SELECT stock_quantity, name FROM products WHERE id = ?", (item["product_id"],))
                p = cursor.fetchone()
                if p and p["stock_quantity"] < item["quantity"]:
                    raise ValueError(f"Cannot revive order: Insufficient stock for '{p['name']}' ({p['stock_quantity']} available).")
                cursor.execute("""
                    UPDATE products
                    SET stock_quantity = stock_quantity - ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (item["quantity"], item["product_id"]))

        cursor.execute("UPDATE orders SET order_status = ? WHERE id = ?", (new_status, order_id))

    return get_order_by_id(order_id)


def update_payment_status(order_id: int, new_payment_status: str) -> Dict[str, Any]:
    """Update the payment status for an existing order."""
    if new_payment_status not in config.PAYMENT_STATUSES:
        raise ValueError(f"Invalid payment status: {new_payment_status}")

    with get_db_cursor() as cursor:
        cursor.execute("UPDATE orders SET payment_status = ? WHERE id = ?", (new_payment_status, order_id))

    return get_order_by_id(order_id)


def delete_order(order_id: int, restore_inventory: bool = True) -> Dict[str, Any]:
    """Permanently delete an order with optional inventory restitution."""
    with get_db_cursor() as cursor:
        cursor.execute("SELECT order_status FROM orders WHERE id = ?", (order_id,))
        order = cursor.fetchone()
        if not order:
            raise ValueError(f"Order ID {order_id} not found.")

        if restore_inventory and order["order_status"] != "Cancelled":
            cursor.execute("SELECT product_id, quantity FROM order_items WHERE order_id = ?", (order_id,))
            for item in cursor.fetchall():
                cursor.execute("""
                    UPDATE products
                    SET stock_quantity = stock_quantity + ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (item["quantity"], item["product_id"]))

        cursor.execute("DELETE FROM orders WHERE id = ?", (order_id,))

    return {"status": "success", "message": f"Order {order_id} successfully deleted."}
