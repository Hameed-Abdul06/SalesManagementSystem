"""Report Service: Aggregates business performance metrics, profit analysis, and time-series trends."""
from typing import Dict, Any, List, Optional
from database.connection import get_connection


def get_dashboard_metrics(start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
    """Calculate key performance indicators (KPIs) for the executive dashboard."""
    conn = get_connection()
    try:
        cursor = conn.cursor()

        # Date filtering condition
        date_filter = ""
        params = []
        if start_date:
            date_filter += " AND DATE(order_date) >= DATE(?)"
            params.append(start_date)
        if end_date:
            date_filter += " AND DATE(order_date) <= DATE(?)"
            params.append(end_date)

        # 1. Financial & Order Metrics (ignoring Cancelled orders)
        query_orders = f"""
            SELECT 
                COUNT(*) AS total_orders,
                COALESCE(SUM(total_amount), 0.0) AS total_revenue,
                COALESCE(SUM(total_cost), 0.0) AS total_cogs,
                COALESCE(SUM(tax_amount), 0.0) AS total_tax,
                COALESCE(SUM(discount_amount), 0.0) AS total_discounts
            FROM orders
            WHERE order_status != 'Cancelled' {date_filter}
        """
        cursor.execute(query_orders, params)
        ord_stats = cursor.fetchone()

        total_orders = ord_stats["total_orders"]
        total_revenue = round(ord_stats["total_revenue"], 2)
        total_cogs = round(ord_stats["total_cogs"], 2)
        total_tax = round(ord_stats["total_tax"], 2)
        total_discounts = round(ord_stats["total_discounts"], 2)

        # Gross Profit = Revenue - Cost of Goods Sold
        estimated_profit = round(total_revenue - total_cogs - total_tax, 2)
        avg_order_value = round(total_revenue / total_orders, 2) if total_orders > 0 else 0.0
        profit_margin = round((estimated_profit / total_revenue) * 100, 1) if total_revenue > 0 else 0.0

        # 2. Total active products & inventory count
        cursor.execute("""
            SELECT 
                COUNT(*) AS total_products,
                COALESCE(SUM(stock_quantity), 0) AS total_inventory_units,
                COALESCE(SUM(stock_quantity * cost_price), 0.0) AS inventory_asset_value,
                SUM(CASE WHEN stock_quantity <= low_stock_threshold AND stock_quantity > 0 THEN 1 ELSE 0 END) AS low_stock_count,
                SUM(CASE WHEN stock_quantity = 0 THEN 1 ELSE 0 END) AS out_of_stock_count
            FROM products
            WHERE is_active = 1
        """)
        prod_stats = cursor.fetchone()

        # 3. Total customers count
        cursor.execute("SELECT COUNT(*) AS total_customers FROM customers")
        cust_stats = cursor.fetchone()

        # 4. Pending / Unpaid orders count
        cursor.execute("""
            SELECT COUNT(*) AS pending_orders, COALESCE(SUM(total_amount), 0.0) AS pending_amount 
            FROM orders 
            WHERE payment_status = 'Pending' AND order_status != 'Cancelled'
        """)
        pending_stats = cursor.fetchone()

        return {
            "total_revenue": total_revenue,
            "total_orders": total_orders,
            "estimated_profit": estimated_profit,
            "profit_margin": profit_margin,
            "total_cogs": total_cogs,
            "total_tax": total_tax,
            "total_discounts": total_discounts,
            "avg_order_value": avg_order_value,
            "total_products": prod_stats["total_products"] or 0,
            "total_inventory_units": prod_stats["total_inventory_units"] or 0,
            "inventory_asset_value": round(prod_stats["inventory_asset_value"] or 0.0, 2),
            "low_stock_count": prod_stats["low_stock_count"] or 0,
            "out_of_stock_count": prod_stats["out_of_stock_count"] or 0,
            "total_customers": cust_stats["total_customers"] or 0,
            "pending_orders": pending_stats["pending_orders"] or 0,
            "pending_amount": round(pending_stats["pending_amount"] or 0.0, 2),
        }
    finally:
        conn.close()


def get_sales_trend(
    group_by: str = "daily",  # 'daily', 'monthly', 'yearly'
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Retrieve time-aggregated sales revenue, costs, and profits."""
    conn = get_connection()
    try:
        cursor = conn.cursor()

        if group_by == "monthly":
            date_format = "strftime('%Y-%m', order_date)"
        elif group_by == "yearly":
            date_format = "strftime('%Y', order_date)"
        else:
            date_format = "DATE(order_date)"

        query = f"""
            SELECT 
                {date_format} AS period,
                COUNT(*) AS order_count,
                COALESCE(SUM(total_amount), 0.0) AS revenue,
                COALESCE(SUM(total_cost), 0.0) AS cost,
                COALESCE(SUM(total_amount - total_cost - tax_amount), 0.0) AS profit
            FROM orders
            WHERE order_status != 'Cancelled'
        """
        params = []

        if start_date:
            query += " AND DATE(order_date) >= DATE(?)"
            params.append(start_date)
        if end_date:
            query += " AND DATE(order_date) <= DATE(?)"
            params.append(end_date)

        query += f" GROUP BY {date_format} ORDER BY period ASC"
        cursor.execute(query, params)
        rows = cursor.fetchall()

        return [
            {
                "period": r["period"],
                "order_count": r["order_count"],
                "revenue": round(r["revenue"], 2),
                "cost": round(r["cost"], 2),
                "profit": round(r["profit"], 2),
            }
            for r in rows
        ]
    finally:
        conn.close()


def get_top_selling_products(limit: int = 10, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve top selling products by volume and revenue."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        query = """
            SELECT 
                oi.product_id,
                oi.product_name,
                COALESCE(p.category, 'Uncategorized') AS category,
                SUM(oi.quantity) AS total_quantity,
                SUM(oi.line_total) AS total_sales,
                SUM(oi.line_total - (oi.cost_price * oi.quantity)) AS total_profit
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.id
            LEFT JOIN products p ON oi.product_id = p.id
            WHERE o.order_status != 'Cancelled'
        """
        params = []
        if start_date:
            query += " AND DATE(o.order_date) >= DATE(?)"
            params.append(start_date)
        if end_date:
            query += " AND DATE(o.order_date) <= DATE(?)"
            params.append(end_date)

        query += " GROUP BY oi.product_name ORDER BY total_sales DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [
            {
                "product_name": r["product_name"],
                "category": r["category"],
                "units_sold": r["total_quantity"],
                "revenue": round(r["total_sales"], 2),
                "profit": round(r["total_profit"], 2),
            }
            for r in rows
        ]
    finally:
        conn.close()


def get_sales_by_category(start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
    """Group sales volume and revenue by product category."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        query = """
            SELECT 
                COALESCE(p.category, 'Other') AS category,
                SUM(oi.quantity) AS units_sold,
                SUM(oi.line_total) AS total_revenue
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.id
            LEFT JOIN products p ON oi.product_id = p.id
            WHERE o.order_status != 'Cancelled'
        """
        params = []
        if start_date:
            query += " AND DATE(o.order_date) >= DATE(?)"
            params.append(start_date)
        if end_date:
            query += " AND DATE(o.order_date) <= DATE(?)"
            params.append(end_date)

        query += " GROUP BY category ORDER BY total_revenue DESC"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [
            {
                "category": r["category"],
                "units_sold": r["units_sold"],
                "revenue": round(r["total_revenue"], 2),
            }
            for r in rows
        ]
    finally:
        conn.close()


def get_payment_method_breakdown(start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
    """Distribution of sales across different payment channels."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        query = """
            SELECT 
                payment_method,
                COUNT(*) AS order_count,
                COALESCE(SUM(total_amount), 0.0) AS total_amount
            FROM orders
            WHERE order_status != 'Cancelled'
        """
        params = []
        if start_date:
            query += " AND DATE(order_date) >= DATE(?)"
            params.append(start_date)
        if end_date:
            query += " AND DATE(order_date) <= DATE(?)"
            params.append(end_date)

        query += " GROUP BY payment_method ORDER BY total_amount DESC"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [
            {
                "payment_method": r["payment_method"],
                "order_count": r["order_count"],
                "total_amount": round(r["total_amount"], 2),
            }
            for r in rows
        ]
    finally:
        conn.close()


def get_top_customers(limit: int = 10) -> List[Dict[str, Any]]:
    """Retrieve top customers ranked by cumulative expenditure."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        query = """
            SELECT 
                c.id,
                c.name,
                c.email,
                c.phone,
                c.customer_type,
                COUNT(o.id) AS total_orders,
                COALESCE(SUM(o.total_amount), 0.0) AS total_spent
            FROM customers c
            JOIN orders o ON c.id = o.customer_id
            WHERE o.order_status != 'Cancelled'
            GROUP BY c.id
            ORDER BY total_spent DESC
            LIMIT ?
        """
        cursor.execute(query, (limit,))
        rows = cursor.fetchall()
        return [
            {
                "name": r["name"],
                "email": r["email"],
                "phone": r["phone"],
                "customer_type": r["customer_type"],
                "total_orders": r["total_orders"],
                "total_spent": round(r["total_spent"], 2),
            }
            for r in rows
        ]
    finally:
        conn.close()
