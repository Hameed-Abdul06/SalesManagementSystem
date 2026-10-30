"""Order History & Invoice UI: View past sales, modify statuses, and generate professional printable invoices."""
from datetime import datetime, timedelta
import streamlit as st
import pandas as pd
from services import order_service, customer_service
import config


def render_history():
    """Render the Order History and Invoice generation interface."""
    st.markdown("## 📜 Sales History & Invoice Generator")
    st.caption("Search past transactions, update fulfillment statuses, and view/print official tax invoices.")

    sym = config.CURRENCY_SYMBOL

    # Filters Bar
    with st.expander("🔍 Search & Filter Orders", expanded=True):
        f1, f2, f3 = st.columns(3)
        with f1:
            search_query = st.text_input("Search (Order # / Customer)", placeholder="e.g. ORD-2026...", key="hist_search")
            order_status = st.selectbox("Order Status", ["All"] + config.ORDER_STATUSES, key="hist_ord_status")
        with f2:
            payment_status = st.selectbox("Payment Status", ["All"] + config.PAYMENT_STATUSES, key="hist_pay_status")
            payment_method = st.selectbox("Payment Method", ["All"] + config.PAYMENT_METHODS, key="hist_pay_method")
        with f3:
            date_filter_type = st.selectbox("Date Filter", ["All Time", "Today", "Last 7 Days", "Last 30 Days", "Custom Range"], key="hist_date_type")

        start_date = None
        end_date = None
        today = datetime.now().date()

        if date_filter_type == "Today":
            start_date = today.strftime("%Y-%m-%d")
            end_date = today.strftime("%Y-%m-%d")
        elif date_filter_type == "Last 7 Days":
            start_date = (today - timedelta(days=7)).strftime("%Y-%m-%d")
            end_date = today.strftime("%Y-%m-%d")
        elif date_filter_type == "Last 30 Days":
            start_date = (today - timedelta(days=30)).strftime("%Y-%m-%d")
            end_date = today.strftime("%Y-%m-%d")
        elif date_filter_type == "Custom Range":
            custom_range = st.date_input("Date Range", value=(today - timedelta(days=14), today), key="hist_custom_dates")
            if isinstance(custom_range, tuple) and len(custom_range) == 2:
                start_date = custom_range[0].strftime("%Y-%m-%d")
                end_date = custom_range[1].strftime("%Y-%m-%d")

    orders = order_service.get_all_orders(
        start_date=start_date,
        end_date=end_date,
        payment_status=payment_status,
        payment_method=payment_method,
        order_status=order_status,
        search_query=search_query
    )

    if not orders:
        st.info("No orders found matching the filter criteria.")
        return

    # Metrics on filtered view
    tot_vol = len(orders)
    tot_rev = sum(o["total_amount"] for o in orders if o["order_status"] != "Cancelled")
    tot_profit = sum(o["total_amount"] - o["total_cost"] - o["tax_amount"] for o in orders if o["order_status"] != "Cancelled")

    m1, m2, m3 = st.columns(3)
    m1.metric("Orders Found", tot_vol)
    m2.metric("Cumulative Revenue", f"{sym}{tot_rev:,.2f}")
    m3.metric("Estimated Profit", f"{sym}{tot_profit:,.2f}")

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    # Orders Table
    df = pd.DataFrame(orders)[[
        "id", "order_number", "order_date", "customer_name", "item_count", "total_amount", "payment_method", "payment_status", "order_status"
    ]]
    df.columns = ["ID", "Order Number", "Date & Time", "Customer", "Items", f"Total ({sym})", "Payment Method", "Payment", "Status"]
    st.dataframe(df, use_container_width=True, hide_index=True)

    csv_data = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Export Order History to CSV",
        data=csv_data,
        file_name="sales_order_history.csv",
        mime="text/csv"
    )

    st.divider()

    # ------------------ INVOICE & ORDER DETAILS VIEWER ------------------
    st.markdown("### 🧾 Official Tax Invoice & Order Management")
    order_options = {f"{o['order_number']} | {o['customer_name']} | {sym}{o['total_amount']:.2f} | ({o['order_status']})": o["id"] for o in orders}
    chosen_order_key = st.selectbox("Select Order to View Invoice / Update Status:", list(order_options.keys()), key="select_invoice_order")
    selected_order_id = order_options[chosen_order_key]

    order = order_service.get_order_by_id(selected_order_id)
    if not order:
        st.error("Order details not found.")
        return

    # Status Update Toolbar
    u_col1, u_col2, u_col3 = st.columns([2, 2, 2])
    with u_col1:
        new_ord_status = st.selectbox("Update Fulfillment Status", config.ORDER_STATUSES, index=config.ORDER_STATUSES.index(order["order_status"]), key="upd_ord_st")
        if st.button("Apply Status Change"):
            try:
                order_service.update_order_status(order["id"], new_ord_status)
                st.success("Order status updated! (Inventory adjusted automatically if cancelled/revived).")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

    with u_col2:
        new_pay_status = st.selectbox("Update Payment Status", config.PAYMENT_STATUSES, index=config.PAYMENT_STATUSES.index(order["payment_status"]), key="upd_pay_st")
        if st.button("Apply Payment Change"):
            try:
                order_service.update_payment_status(order["id"], new_pay_status)
                st.success("Payment status updated!")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

    with u_col3:
        with st.expander("🗑️ Delete Order Record"):
            st.warning("Deleting an order permanently removes the transaction.")
            restore_inv = st.checkbox("Restore inventory for items in this order", value=True, key="chk_res_inv")
            confirm_del_ord = st.checkbox("Confirm order deletion", key="chk_conf_ord_del")
            if st.button("Delete Order Permanently", type="secondary", disabled=not confirm_del_ord):
                try:
                    order_service.delete_order(order["id"], restore_inventory=restore_inv)
                    st.success("Order deleted successfully.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)

    # Visual Invoice Display
    company = config.COMPANY_DETAILS
    with st.container(border=True):
        inv_h1, inv_h2 = st.columns([3, 2])
        with inv_h1:
            st.subheader(company["name"])
            st.caption(f"{company['address']} • {company['city']}\nPhone: {company['phone']} | Email: {company['email']} | Tax ID: {company['tax_id']}")
        with inv_h2:
            st.markdown(f"### INVOICE: {order['order_number']}")
            st.write(f"**Date:** {order['order_date']}")
            pay_color = "🟢" if order["payment_status"] == "Paid" else "🟡"
            ord_color = "🔵" if order["order_status"] == "Completed" else ("🔴" if order["order_status"] == "Cancelled" else "🟡")
            st.write(f"Payment: {pay_color} **{order['payment_status']}** | Status: {ord_color} **{order['order_status']}**")

        st.divider()

        b_col1, b_col2 = st.columns(2)
        with b_col1:
            st.markdown("**Billed To:**")
            st.markdown(f"**{order['customer_name']}**")
            st.caption(f"Phone: {order.get('customer_phone') or 'N/A'}\nEmail: {order.get('customer_email') or 'N/A'}\nAddress: {order.get('customer_address') or 'N/A'}")
        with b_col2:
            st.markdown("**Payment Details:**")
            st.write(f"Method: **{order['payment_method']}**")
            if order.get("notes"):
                st.caption(f"Notes: {order['notes']}")

        st.markdown("#### Line Items")
        items_data = []
        for item in order["items"]:
            items_data.append({
                "SKU": item.get("sku") or "N/A",
                "Item Description": item["product_name"],
                f"Unit Price ({sym})": f"{sym}{item['unit_price']:.2f}",
                "Quantity": item["quantity"],
                f"Line Total ({sym})": f"{sym}{item['line_total']:.2f}"
            })
        st.table(pd.DataFrame(items_data))

        f_left, f_right = st.columns([3, 2])
        with f_right:
            with st.container(border=True):
                r1, r2 = st.columns(2)
                r1.write("Subtotal:")
                r2.write(f"**{sym}{order['subtotal']:,.2f}**")
                
                r3, r4 = st.columns(2)
                r3.write(f"Discount ({order['discount_type']}):")
                r4.write(f"-{sym}{order['discount_amount']:,.2f}")
                
                r5, r6 = st.columns(2)
                r5.write(f"Tax / VAT ({order['tax_rate']}%):")
                r6.write(f"+{sym}{order['tax_amount']:,.2f}")
                
                st.divider()
                tot_lbl, tot_val = st.columns(2)
                tot_lbl.markdown("### Total:")
                tot_val.markdown(f"### {sym}{order['total_amount']:,.2f}")

        st.caption(f"Thank you for your business! For inquiries, contact {company['email']}.")

    # Download button for specific invoice
    invoice_csv = pd.DataFrame(order["items"])[["product_name", "quantity", "unit_price", "line_total"]].to_csv(index=False).encode('utf-8')
    st.download_button(
        label=f"📥 Download Invoice Items ({order['order_number']})",
        data=invoice_csv,
        file_name=f"invoice_{order['order_number']}.csv",
        mime="text/csv"
    )
