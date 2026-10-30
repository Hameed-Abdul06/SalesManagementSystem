"""Customer Service: Manages customer records, profiles, and historical purchases."""
from typing import List, Dict, Any, Optional
from database.connection import get_connection, get_db_cursor


def get_all_customers(
    search_query: Optional[str] = None,
    customer_type: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Retrieve customers with optional text search and customer type filter."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        query = """
            SELECT c.*, 
                   COUNT(o.id) AS total_orders, 
                   COALESCE(SUM(CASE WHEN o.order_status != 'Cancelled' THEN o.total_amount ELSE 0 END), 0.0) AS total_spent
            FROM customers c
            LEFT JOIN orders o ON c.id = o.customer_id
            WHERE 1=1
        """
        params = []

        if customer_type and customer_type != "All":
            query += " AND c.customer_type = ?"
            params.append(customer_type)

        if search_query:
            term = f"%{search_query.strip()}%"
            query += " AND (c.name LIKE ? OR c.email LIKE ? OR c.phone LIKE ?)"
            params.extend([term, term, term])

        query += " GROUP BY c.id ORDER BY c.name ASC"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_customer_by_id(customer_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve a single customer by ID with aggregate spending metrics."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        query = """
            SELECT c.*, 
                   COUNT(o.id) AS total_orders, 
                   COALESCE(SUM(CASE WHEN o.order_status != 'Cancelled' THEN o.total_amount ELSE 0 END), 0.0) AS total_spent
            FROM customers c
            LEFT JOIN orders o ON c.id = o.customer_id
            WHERE c.id = ?
            GROUP BY c.id
        """
        cursor.execute(query, (customer_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def create_customer(
    name: str,
    email: str = "",
    phone: str = "",
    address: str = "",
    customer_type: str = "Retail",
    notes: str = ""
) -> Dict[str, Any]:
    """Create a new customer record with validation."""
    name = name.strip()
    email = email.strip()
    phone = phone.strip()

    if not name:
        raise ValueError("Customer name is required.")

    with get_db_cursor() as cursor:
        cursor.execute("""
            INSERT INTO customers (name, email, phone, address, customer_type, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name, email, phone, address, customer_type, notes))
        customer_id = cursor.lastrowid

    return get_customer_by_id(customer_id)


def update_customer(
    customer_id: int,
    name: str,
    email: str = "",
    phone: str = "",
    address: str = "",
    customer_type: str = "Retail",
    notes: str = ""
) -> Dict[str, Any]:
    """Update customer demographic and contact details."""
    name = name.strip()
    if not name:
        raise ValueError("Customer name is required.")

    with get_db_cursor() as cursor:
        cursor.execute("""
            UPDATE customers
            SET name = ?, email = ?, phone = ?, address = ?, customer_type = ?, notes = ?
            WHERE id = ?
        """, (name, email.strip(), phone.strip(), address.strip(), customer_type, notes.strip(), customer_id))

    return get_customer_by_id(customer_id)


def delete_customer(customer_id: int) -> Dict[str, Any]:
    """Delete a customer. Existing orders remain with customer_id set to NULL."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM orders WHERE customer_id = ?", (customer_id,))
        order_count = cursor.fetchone()[0]

        with get_db_cursor() as cur:
            cur.execute("DELETE FROM customers WHERE id = ?", (customer_id,))

        return {
            "status": "success",
            "message": f"Customer removed. ({order_count} associated historical orders preserved with unassigned customer)."
        }
    finally:
        conn.close()


def get_customer_order_history(customer_id: int) -> List[Dict[str, Any]]:
    """Retrieve all orders placed by this customer with item counts."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        query = """
            SELECT o.*, COUNT(oi.id) AS item_count
            FROM orders o
            LEFT JOIN order_items oi ON o.id = oi.order_id
            WHERE o.customer_id = ?
            GROUP BY o.id
            ORDER BY o.order_date DESC
        """
        cursor.execute(query, (customer_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()
