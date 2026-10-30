"""Reports & Analytics UI: Aggregated financial reports, profit & loss analysis, and multi-period trends."""
from datetime import datetime, timedelta
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from services import report_service
import config


def render_reports():
    """Render comprehensive financial and operational analytics."""
    st.markdown("## 📊 Sales Analytics & Financial Reports")
    st.caption("Perform multi-period trend analysis, profit margin calculations, and export audit reports.")

    sym = config.CURRENCY_SYMBOL

    # Controls
    c_f1, c_f2, c_f3 = st.columns([2, 2, 2])
    with c_f1:
        timeframe_mode = st.selectbox("Aggregation Period:", ["Daily", "Monthly", "Yearly"], index=0, key="rep_agg_mode")
    with c_f2:
        period_scope = st.selectbox("Date Scope:", ["Past 30 Days", "Past 90 Days", "Past 1 Year", "All Historical Data", "Custom Date Range"], key="rep_scope")

    start_date = None
    end_date = None
    today = datetime.now().date()

    if period_scope == "Past 30 Days":
        start_date = (today - timedelta(days=30)).strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")
    elif period_scope == "Past 90 Days":
        start_date = (today - timedelta(days=90)).strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")
    elif period_scope == "Past 1 Year":
        start_date = (today - timedelta(days=365)).strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")
    elif period_scope == "Custom Date Range":
        with c_f3:
            cust_rng = st.date_input("Select Custom Interval", value=(today - timedelta(days=60), today), key="rep_custom_interval")
            if isinstance(cust_rng, tuple) and len(cust_rng) == 2:
                start_date = cust_rng[0].strftime("%Y-%m-%d")
                end_date = cust_rng[1].strftime("%Y-%m-%d")

    # Fetch Metrics for this period
    metrics = report_service.get_dashboard_metrics(start_date=start_date, end_date=end_date)

    # Financial Summary Bar
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Gross Revenue", f"{sym}{metrics['total_revenue']:,.2f}")
    m2.metric("Cost of Goods (COGS)", f"{sym}{metrics['total_cogs']:,.2f}")
    m3.metric("Net Profit", f"{sym}{metrics['estimated_profit']:,.2f}", f"{metrics['profit_margin']}% margin")
    m4.metric("Total Tax Collected", f"{sym}{metrics['total_tax']:,.2f}")
    m5.metric("Total Discounts Given", f"{sym}{metrics['total_discounts']:,.2f}")

    st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)

    # Sales Trends Table & Chart
    trend_mode = timeframe_mode.lower()
    trends = report_service.get_sales_trend(group_by=trend_mode, start_date=start_date, end_date=end_date)

    if trends:
        df_trends = pd.DataFrame(trends)
        
        st.markdown(f"### 📈 {timeframe_mode} Sales, Cost & Profit Comparison")
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df_trends["period"],
            y=df_trends["revenue"],
            name="Revenue",
            marker_color="#3b82f6"
        ))
        fig.add_trace(go.Bar(
            x=df_trends["period"],
            y=df_trends["cost"],
            name="COGS (Cost)",
            marker_color="#f97316"
        ))
        fig.add_trace(go.Scatter(
            x=df_trends["period"],
            y=df_trends["profit"],
            name="Net Profit",
            mode="lines+markers",
            line=dict(color="#10b981", width=3)
        ))
        fig.update_layout(
            barmode="group",
            xaxis_title="Period",
            yaxis_title=f"Amount ({sym})",
            template="plotly_white",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig, use_container_width=True)

        # Tabular View
        with st.expander(f"📋 View Detailed {timeframe_mode} Breakdown Data Table"):
            df_display = df_trends.copy()
            df_display.columns = ["Period", "Order Count", f"Revenue ({sym})", f"Cost ({sym})", f"Profit ({sym})"]
            st.dataframe(df_display, use_container_width=True, hide_index=True)

            csv_trend = df_display.to_csv(index=False).encode('utf-8')
            st.download_button(
                label=f"📥 Download {timeframe_mode} Report CSV",
                data=csv_trend,
                file_name=f"{trend_mode}_sales_report.csv",
                mime="text/csv"
            )
    else:
        st.info("No transaction data available for the chosen date range.")

    st.divider()

    # Product Performance & Customer Rankings
    col_p, col_c = st.columns(2)

    with col_p:
        st.markdown("### 🏷️ Category Revenue Performance")
        cat_data = report_service.get_sales_by_category(start_date=start_date, end_date=end_date)
        if cat_data:
            df_c = pd.DataFrame(cat_data)
            fig_c = px.bar(
                df_c,
                x="category",
                y="total_revenue",
                color="total_revenue",
                text="units_sold",
                color_continuous_scale="Viridis",
                labels={"category": "Category", "total_revenue": f"Revenue ({sym})", "units_sold": "Units"}
            )
            fig_c.update_traces(texttemplate='%{text} units', textposition='outside')
            fig_c.update_layout(showlegend=False, coloraxis_showscale=False, template="plotly_white")
            st.plotly_chart(fig_c, use_container_width=True)
        else:
            st.info("No category sales available.")

    with col_c:
        st.markdown("### 👑 Top Customers by Expenditure")
        top_custs = report_service.get_top_customers(limit=8)
        if top_custs:
            df_tc = pd.DataFrame(top_custs)[["name", "customer_type", "total_orders", "total_spent"]]
            df_tc.columns = ["Customer Name", "Type", "Orders Placed", f"Total Spent ({sym})"]
            st.dataframe(df_tc, use_container_width=True, hide_index=True)
        else:
            st.info("No customer purchase data available.")
