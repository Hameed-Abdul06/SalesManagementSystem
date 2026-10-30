"""Dashboard View: Executive overview with KPIs, interactive Plotly visualizations, and low-stock alerts."""
from datetime import datetime, timedelta
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from services import report_service, product_service, order_service
import config


def render_dashboard():
    """Render the main executive overview dashboard."""
    st.markdown("## 📊 Business Intelligence Dashboard")
    st.caption("Real-time revenue, order volume, inventory analytics, and financial performance.")

    # Top Filter Bar
    col_filter1, col_filter2 = st.columns([2, 2])
    with col_filter1:
        date_preset = st.selectbox(
            "Select Timeframe:",
            ["Last 30 Days", "Today", "Last 7 Days", "All Time", "Custom Date Range"],
            index=0,
            key="dash_timeframe"
        )

    start_date = None
    end_date = None
    today = datetime.now().date()

    if date_preset == "Today":
        start_date = today.strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")
    elif date_preset == "Last 7 Days":
        start_date = (today - timedelta(days=7)).strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")
    elif date_preset == "Last 30 Days":
        start_date = (today - timedelta(days=30)).strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")
    elif date_preset == "Custom Date Range":
        with col_filter2:
            custom_range = st.date_input(
                "Custom Date Range:",
                value=(today - timedelta(days=14), today),
                key="dash_custom_range"
            )
            if isinstance(custom_range, tuple) and len(custom_range) == 2:
                start_date = custom_range[0].strftime("%Y-%m-%d")
                end_date = custom_range[1].strftime("%Y-%m-%d")

    # Fetch Metrics
    metrics = report_service.get_dashboard_metrics(start_date=start_date, end_date=end_date)
    sym = config.CURRENCY_SYMBOL

    # KPI Metric Cards (Row 1)
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        with st.container(border=True):
            st.metric(
                label="Total Revenue",
                value=f"{sym}{metrics['total_revenue']:,.2f}",
                delta=f"{metrics['total_orders']} orders"
            )
    with k2:
        margin_text = f"{metrics['profit_margin']}% margin" if metrics['total_revenue'] > 0 else "0% margin"
        with st.container(border=True):
            st.metric(
                label="Estimated Profit",
                value=f"{sym}{metrics['estimated_profit']:,.2f}",
                delta=margin_text
            )
    with k3:
        with st.container(border=True):
            st.metric(
                label="Avg Order Value",
                value=f"{sym}{metrics['avg_order_value']:,.2f}",
                delta="Per sale"
            )
    with k4:
        with st.container(border=True):
            st.metric(
                label="Low Stock Items",
                value=f"{metrics['low_stock_count']} Products",
                delta=f"{metrics['out_of_stock_count']} empty",
                delta_color="inverse" if metrics["low_stock_count"] > 0 else "off"
            )

    st.write("")

    # Low Stock Warning Alert Banner
    if metrics["low_stock_count"] > 0 or metrics["out_of_stock_count"] > 0:
        with st.expander(f"⚠️ Attention: {metrics['low_stock_count']} product(s) require reordering!", expanded=True):
            low_prods = product_service.get_low_stock_products()
            if low_prods:
                low_df = pd.DataFrame(low_prods)[["sku", "name", "category", "stock_quantity", "low_stock_threshold", "selling_price"]]
                low_df.columns = ["SKU", "Product Name", "Category", "Current Stock", "Threshold", "Price"]
                st.dataframe(low_df, use_container_width=True, hide_index=True)
                st.info("Tip: Navigate to the 'Inventory & Products' tab to adjust stock or restock items.")

    # Charts Section 1: Revenue & Profit Trend + Top Selling Products
    c1, c2 = st.columns([3, 2])

    with c1:
        st.markdown("#### 📈 Revenue & Profit Dynamics")
        trend_data = report_service.get_sales_trend(group_by="daily", start_date=start_date, end_date=end_date)
        if trend_data:
            df_trend = pd.DataFrame(trend_data)
            fig_trend = go.Figure()
            fig_trend.add_trace(go.Bar(
                x=df_trend["period"],
                y=df_trend["revenue"],
                name=f"Revenue ({sym})",
                marker_color="#3b82f6"
            ))
            fig_trend.add_trace(go.Scatter(
                x=df_trend["period"],
                y=df_trend["profit"],
                name=f"Estimated Profit ({sym})",
                mode="lines+markers",
                line=dict(color="#10b981", width=3)
            ))
            fig_trend.update_layout(
                margin=dict(l=20, r=20, t=30, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                xaxis_title="Date",
                yaxis_title=f"Amount ({sym})",
                hovermode="x unified",
                template="plotly_white"
            )
            st.plotly_chart(fig_trend, use_container_width=True)
        else:
            st.info("No sales transactions found for the selected timeframe.")

    with c2:
        st.markdown("#### 🏆 Top Selling Products")
        top_prods = report_service.get_top_selling_products(limit=5, start_date=start_date, end_date=end_date)
        if top_prods:
            df_top = pd.DataFrame(top_prods)
            fig_top = px.bar(
                df_top,
                x="revenue",
                y="product_name",
                orientation="h",
                text="units_sold",
                color="revenue",
                color_continuous_scale="Blues",
                labels={"revenue": f"Revenue ({sym})", "product_name": "Product", "units_sold": "Units Sold"}
            )
            fig_top.update_layout(
                yaxis=dict(autorange="reversed"),
                margin=dict(l=20, r=20, t=30, b=20),
                showlegend=False,
                coloraxis_showscale=False,
                template="plotly_white"
            )
            fig_top.update_traces(texttemplate='%{text} units', textposition='outside')
            st.plotly_chart(fig_top, use_container_width=True)
        else:
            st.info("No product sales data available for this timeframe.")

    # Charts Section 2: Sales by Category & Payment Methods
    c3, c4 = st.columns(2)

    with c3:
        st.markdown("#### 🏷️ Sales by Category")
        cat_data = report_service.get_sales_by_category(start_date=start_date, end_date=end_date)
        if cat_data:
            df_cat = pd.DataFrame(cat_data)
            fig_cat = px.pie(
                df_cat,
                values="revenue",
                names="category",
                hole=0.45,
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig_cat.update_layout(
                margin=dict(l=20, r=20, t=30, b=20),
                template="plotly_white"
            )
            st.plotly_chart(fig_cat, use_container_width=True)
        else:
            st.info("No category sales available.")

    with c4:
        st.markdown("#### 💳 Payment Methods Breakdown")
        pm_data = report_service.get_payment_method_breakdown(start_date=start_date, end_date=end_date)
        if pm_data:
            df_pm = pd.DataFrame(pm_data)
            fig_pm = px.pie(
                df_pm,
                values="total_amount",
                names="payment_method",
                hole=0.45,
                color_discrete_sequence=px.colors.qualitative.Safe
            )
            fig_pm.update_layout(
                margin=dict(l=20, r=20, t=30, b=20),
                template="plotly_white"
            )
            st.plotly_chart(fig_pm, use_container_width=True)
        else:
            st.info("No payment method data available.")

    # Recent Orders Quick Table
    st.markdown("#### 🕒 Recent Transactions")
    recent_orders = order_service.get_all_orders()[:6]
    if recent_orders:
        recent_df = pd.DataFrame(recent_orders)[[
            "order_number", "order_date", "customer_name", "total_amount", "payment_method", "payment_status", "order_status"
        ]]
        recent_df.columns = ["Order Number", "Date & Time", "Customer", f"Total ({sym})", "Payment Method", "Payment", "Status"]
        st.dataframe(recent_df, use_container_width=True, hide_index=True)
    else:
        st.info("No orders placed yet. Go to 'Create New Order' to place your first sale!")
