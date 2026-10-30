"""Sales & Orders UI: Interactive Point-of-Sale (POS) order creation interface with live cart calculations."""
import streamlit as st
import pandas as pd
from services import product_service, customer_service, order_service
import config


def init_cart():
    """Ensure session state cart exists."""
    if "cart_items" not in st.session_state:
        st.session_state.cart_items = []


def render_orders():
    """Render the Create New Order / POS terminal view."""
    init_cart()
    sym = config.CURRENCY_SYMBOL

    st.markdown("## 🛒 Point of Sale / Create New Order")
    st.caption("Select customer, add products to cart, apply discounts, and complete sales transactions.")

    col_left, col_right = st.columns([3, 2])

    # ------------------ LEFT COLUMN: PRODUCT SELECTION & CART ------------------
    with col_left:
        st.markdown("### 🛍️ Add Products to Order")
        
        # Fetch active products in stock
        all_prods = product_service.get_all_products(include_inactive=False)
        in_stock_prods = [p for p in all_prods if p["stock_quantity"] > 0]

        if not in_stock_prods:
            st.warning("⚠️ No products with available stock found! Please add products or restock inventory.")
        else:
            prod_lookup = {
                f"{p['name']} ({p['sku']}) - {sym}{p['selling_price']:.2f} [{p['stock_quantity']} in stock]": p
                for p in in_stock_prods
            }

            c_prod, c_qty = st.columns([3, 1])
            with c_prod:
                selected_prod_key = st.selectbox("Select Product", list(prod_lookup.keys()), key="pos_prod_select")
                selected_p = prod_lookup[selected_prod_key]

            with c_qty:
                max_stock = selected_p["stock_quantity"]
                quantity = st.number_input(
                    "Quantity",
                    min_value=1,
                    max_value=max_stock,
                    value=1,
                    step=1,
                    key="pos_qty_input"
                )

            if st.button("➕ Add to Cart", type="secondary", use_container_width=True):
                # Check if item is already in cart
                existing_item = next((item for item in st.session_state.cart_items if item["product_id"] == selected_p["id"]), None)
                if existing_item:
                    new_qty = existing_item["quantity"] + quantity
                    if new_qty > max_stock:
                        st.error(f"Cannot add {quantity} more. Total in cart ({new_qty}) exceeds stock ({max_stock}).")
                    else:
                        existing_item["quantity"] = new_qty
                        st.success(f"Updated quantity for '{selected_p['name']}' to {new_qty}.")
                        st.rerun()
                else:
                    st.session_state.cart_items.append({
                        "product_id": selected_p["id"],
                        "name": selected_p["name"],
                        "sku": selected_p["sku"],
                        "cost_price": float(selected_p["cost_price"]),
                        "unit_price": float(selected_p["selling_price"]),
                        "quantity": int(quantity),
                        "max_stock": max_stock
                    })
                    st.success(f"Added '{selected_p['name']}' (x{quantity}) to cart.")
                    st.rerun()

        # Display Current Cart
        st.markdown("### 🛒 Current Order Cart")
        if not st.session_state.cart_items:
            st.info("Your order cart is currently empty. Select a product above and click 'Add to Cart'.")
        else:
            cart_rows = []
            for idx, item in enumerate(st.session_state.cart_items):
                cart_rows.append({
                    "Item": item["name"],
                    "SKU": item["sku"],
                    f"Unit Price ({sym})": f"{sym}{item['unit_price']:.2f}",
                    "Qty": item["quantity"],
                    f"Total ({sym})": f"{sym}{round(item['unit_price'] * item['quantity'], 2):.2f}"
                })
            
            st.dataframe(pd.DataFrame(cart_rows), use_container_width=True, hide_index=True)

            col_clr, col_rem = st.columns([1, 2])
            with col_clr:
                if st.button("🗑️ Clear Entire Cart", type="secondary"):
                    st.session_state.cart_items = []
                    st.rerun()

            with col_rem:
                item_labels = [f"{i['name']} (x{i['quantity']})" for i in st.session_state.cart_items]
                to_remove_idx = st.selectbox("Remove single item:", range(len(item_labels)), format_func=lambda x: item_labels[x], key="remove_item_sel")
                if st.button("Remove Item", type="secondary"):
                    st.session_state.cart_items.pop(to_remove_idx)
                    st.rerun()

    # ------------------ RIGHT COLUMN: CHECKOUT & PAYMENT DETAILS ------------------
    with col_right:
        st.markdown("### 💳 Checkout & Billing")

        # Customer selection
        customers = customer_service.get_all_customers()
        cust_choices = {"None (Walk-in / Cash Customer)": None}
        for c in customers:
            cust_choices[f"{c['name']} ({c['phone'] or c['email'] or 'No contact'})"] = c["id"]

        selected_cust_label = st.selectbox("Assign Customer:", list(cust_choices.keys()), key="pos_customer_sel")
        customer_id = cust_choices[selected_cust_label]

        # Financial Calculations
        d_c1, d_c2 = st.columns(2)
        with d_c1:
            discount_type = st.selectbox("Discount Type", ["Percentage", "Fixed Amount"], key="pos_disc_type")
        with d_c2:
            disc_label = "Discount (%)" if discount_type == "Percentage" else f"Discount ({sym})"
            max_disc_val = 100.0 if discount_type == "Percentage" else 100000.0
            discount_value = st.number_input(disc_label, min_value=0.0, max_value=max_disc_val, value=0.0, step=1.0, key="pos_disc_val")

        tax_rate = st.number_input("Tax / VAT Rate (%)", min_value=0.0, max_value=100.0, value=config.DEFAULT_TAX_RATE, step=0.5, key="pos_tax_rate")

        # Payment options
        p_c1, p_c2 = st.columns(2)
        with p_c1:
            payment_method = st.selectbox("Payment Method", config.PAYMENT_METHODS, key="pos_pay_method")
        with p_c2:
            payment_status = st.selectbox("Payment Status", config.PAYMENT_STATUSES, index=0, key="pos_pay_status")

        order_status = st.selectbox("Order Status", ["Completed", "Pending"], index=0, key="pos_ord_status")
        notes = st.text_input("Order Notes (Optional)", placeholder="e.g. Rush delivery, gift packing", key="pos_notes")

        # Live Summary Card
        totals = order_service.calculate_order_totals(
            items=st.session_state.cart_items,
            discount_type="Percentage" if discount_type == "Percentage" else "Fixed",
            discount_value=discount_value,
            tax_rate=tax_rate
        )

        with st.container(border=True):
            st.markdown("#### 🧾 Order Summary")
            col_lbl, col_val = st.columns([2, 1])
            with col_lbl:
                st.write("Subtotal:")
                st.write(f"Discount ({totals['discount_type']}):")
                st.write(f"Tax / VAT ({totals['tax_rate']}%):")
            with col_val:
                st.write(f"**{sym}{totals['subtotal']:,.2f}**")
                st.write(f"-{sym}{totals['discount_amount']:,.2f}")
                st.write(f"+{sym}{totals['tax_amount']:,.2f}")

            st.divider()
            t_col1, t_col2 = st.columns([2, 1])
            with t_col1:
                st.markdown("### Total:")
            with t_col2:
                st.markdown(f"### {sym}{totals['total_amount']:,.2f}")

            st.caption(f"Estimated Profit: {sym}{totals['estimated_profit']:,.2f}")

        if st.button("🚀 Complete Order & Process Payment", type="primary", use_container_width=True, disabled=len(st.session_state.cart_items) == 0):
            try:
                created = order_service.create_order(
                    customer_id=customer_id,
                    items=st.session_state.cart_items,
                    payment_method=payment_method,
                    payment_status=payment_status,
                    order_status=order_status,
                    discount_type="Percentage" if discount_type == "Percentage" else "Fixed",
                    discount_value=discount_value,
                    tax_rate=tax_rate,
                    notes=notes
                )
                st.session_state.cart_items = []
                st.balloons()
                st.success(f"🎉 Order **{created['order_number']}** placed successfully! Inventory has been automatically updated.")
                st.info("You can view and print the invoice in the 'Order History & Invoices' section.")
            except Exception as e:
                st.error(f"Transaction failed: {e}")
