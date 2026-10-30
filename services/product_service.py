"""Product Service: Handles product catalog management, search, and stock level controls."""
from typing import List, Dict, Any, Optional
from database.connection import get_connection, get_db_cursor


def get_all_products(
    include_inactive: bool = False,
    category: Optional[str] = None,
    search_query: Optional[str] = None,
    stock_status: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Fetch products with optional category, search, and stock filtering."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        query = "SELECT * FROM products WHERE 1=1"
        params = []

        if not include_inactive:
            query += " AND is_active = 1"

        if category and category != "All":
            query += " AND category = ?"
            params.append(category)

        if search_query:
            term = f"%{search_query.strip()}%"
            query += " AND (name LIKE ? OR sku LIKE ? OR description LIKE ?)"
            params.extend([term, term, term])

        if stock_status == "Low Stock":
            query += " AND stock_quantity <= low_stock_threshold AND stock_quantity > 0"
        elif stock_status == "Out of Stock":
            query += " AND stock_quantity = 0"
        elif stock_status == "In Stock":
            query += " AND stock_quantity > low_stock_threshold"

        query += " ORDER BY name ASC"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_product_by_id(product_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve a single product by its database ID."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_product_by_sku(sku: str) -> Optional[Dict[str, Any]]:
    """Retrieve a product by its unique SKU code."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE LOWER(sku) = LOWER(?)", (sku.strip(),))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def create_product(
    sku: str,
    name: str,
    category: str,
    cost_price: float,
    selling_price: float,
    stock_quantity: int,
    low_stock_threshold: int = 10,
    description: str = ""
) -> Dict[str, Any]:
    """Create a new product with input validation."""
    sku = sku.strip().upper()
    name = name.strip()
    category = category.strip()

    if not sku:
        raise ValueError("Product SKU/Code is required.")
    if not name:
        raise ValueError("Product name is required.")
    if not category:
        raise ValueError("Product category is required.")
    if cost_price < 0:
        raise ValueError("Cost price cannot be negative.")
    if selling_price < 0:
        raise ValueError("Selling price cannot be negative.")
    if stock_quantity < 0:
        raise ValueError("Stock quantity cannot be negative.")
    if low_stock_threshold < 0:
        raise ValueError("Low stock threshold cannot be negative.")

    # Check for existing SKU
    existing = get_product_by_sku(sku)
    if existing:
        raise ValueError(f"A product with SKU '{sku}' already exists ({existing['name']}).")

    with get_db_cursor() as cursor:
        cursor.execute("""
            INSERT INTO products (
                sku, name, category, cost_price, selling_price,
                stock_quantity, low_stock_threshold, description, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, (sku, name, category, cost_price, selling_price, stock_quantity, low_stock_threshold, description))
        product_id = cursor.lastrowid

    return get_product_by_id(product_id)


def update_product(
    product_id: int,
    sku: str,
    name: str,
    category: str,
    cost_price: float,
    selling_price: float,
    stock_quantity: int,
    low_stock_threshold: int = 10,
    description: str = "",
    is_active: int = 1
) -> Dict[str, Any]:
    """Update an existing product's attributes."""
    sku = sku.strip().upper()
    name = name.strip()

    if not sku or not name:
        raise ValueError("SKU and Name are required fields.")
    if cost_price < 0 or selling_price < 0 or stock_quantity < 0 or low_stock_threshold < 0:
        raise ValueError("Prices, stock, and thresholds must be non-negative numbers.")

    # Check if SKU was changed to one that belongs to another product
    existing = get_product_by_sku(sku)
    if existing and existing["id"] != product_id:
        raise ValueError(f"SKU '{sku}' is already assigned to '{existing['name']}'.")

    with get_db_cursor() as cursor:
        cursor.execute("""
            UPDATE products
            SET sku = ?, name = ?, category = ?, cost_price = ?, selling_price = ?,
                stock_quantity = ?, low_stock_threshold = ?, description = ?,
                is_active = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (sku, name, category, cost_price, selling_price, stock_quantity, low_stock_threshold, description, is_active, product_id))

    return get_product_by_id(product_id)


def delete_product(product_id: int) -> Dict[str, Any]:
    """Delete a product.
    
    If the product has sales history in order_items, it is archived (soft-deleted, is_active = 0)
    to protect historic audit and financial records. If no orders exist, it is hard-deleted.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM order_items WHERE product_id = ?", (product_id,))
        order_count = cursor.fetchone()[0]

        if order_count > 0:
            # Soft delete to preserve historical integrity
            with get_db_cursor() as cur:
                cur.execute("UPDATE products SET is_active = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (product_id,))
            return {"action": "archived", "message": f"Product has {order_count} historical order records. Safely archived (deactivated) instead of erased."}
        else:
            with get_db_cursor() as cur:
                cur.execute("DELETE FROM products WHERE id = ?", (product_id,))
            return {"action": "deleted", "message": "Product permanently removed from database."}
    finally:
        conn.close()


def adjust_stock(product_id: int, quantity_change: int, reason: str = "") -> Dict[str, Any]:
    """Adjust stock quantity for a product (e.g. stock replenishment or shrinkage)."""
    with get_db_cursor() as cursor:
        cursor.execute("SELECT stock_quantity, name FROM products WHERE id = ?", (product_id,))
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Product ID {product_id} not found.")

        current_stock = row["stock_quantity"]
        new_stock = current_stock + quantity_change
        if new_stock < 0:
            raise ValueError(f"Cannot reduce stock by {abs(quantity_change)}. Current stock is only {current_stock}.")

        cursor.execute("""
            UPDATE products
            SET stock_quantity = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (new_stock, product_id))

    return {"product_id": product_id, "previous_stock": current_stock, "new_stock": new_stock}


def get_low_stock_products() -> List[Dict[str, Any]]:
    """Retrieve all active products currently at or below their low stock threshold."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM products
            WHERE is_active = 1 AND stock_quantity <= low_stock_threshold
            ORDER BY stock_quantity ASC
        """)
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()
