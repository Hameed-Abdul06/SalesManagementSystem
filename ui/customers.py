"""Customer Management UI: Manage customer directory, add/edit profiles, and drill down into purchase history."""
import streamlit as st
import pandas as pd
from services import customer_service
import config


def render_customers():
    """Render customer directory and CRM interface."""
    st.markdown("## 👥 Customer Directory & CRM")
    st.caption("Manage customer accounts, view detailed transaction history, and analyze customer lifetime value.")

    tab_list, tab_add, tab_history = st.tabs(["📋 Customer Directory", "➕ Add New Customer", "📜 Purchase History Drilldown"])

    sym = config.CURRENCY_SYMBOL

    # ------------------ TAB 1: CUSTOMER DIRECTORY ------------------
    with tab_list:
        col_s1, col_s2 = st.columns([3, 2])
        with col_s1:
            search_query = st.text_input("🔍 Search Customers", placeholder="Search by name, email, or phone number...", key="cust_search")
        with col_s2:
            type_filter = st.selectbox("Customer Type", ["All"] + config.CUSTOMER_TYPES, key="cust_type_filter")

        customers = customer_service.get_all_customers(search_query=search_query, customer_type=type_filter)

        if customers:
            # Summary Metrics
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Customers", len(customers))
            c2.metric("Total Customer Spend", f"{sym}{sum(c['total_spent'] for c in customers):,.2f}")
            c3.metric("Retail Accounts", sum(1 for c in customers if c["customer_type"] == "Retail"))
            c4.metric("Wholesale / Corporate", sum(1 for c in customers if c["customer_type"] in ["Wholesale", "Corporate"]))

            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

            # Table
            df = pd.DataFrame(customers)[["id", "name", "email", "phone", "customer_type", "total_orders", "total_spent"]]
            df.columns = ["ID", "Name", "Email", "Phone", "Type", "Total Orders", f"Total Spent ({sym})"]
            st.dataframe(df, use_container_width=True, hide_index=True)

            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Export Customers to CSV",
                data=csv,
                file_name="customers_directory.csv",
                mime="text/csv"
            )

            st.divider()

            # Modify or Delete
            st.markdown("### ⚙️ Edit / Manage Customer Record")
            cust_options = {f"{c['name']} (ID: {c['id']}) - {c['phone']}": c for c in customers}
            chosen_label = st.selectbox("Select Customer to Modify:", list(cust_options.keys()), key="cust_select_modify")
            chosen_cust = cust_options[chosen_label]

            col_edit, col_del = st.columns([3, 2])
            with col_edit:
                with st.expander("✏️ Edit Customer Information", expanded=False):
                    with st.form(key=f"cust_edit_form_{chosen_cust['id']}"):
                        edit_name = st.text_input("Full Name *", value=chosen_cust["name"])
                        edit_email = st.text_input("Email", value=chosen_cust.get("email") or "")
                        edit_phone = st.text_input("Phone", value=chosen_cust.get("phone") or "")
                        edit_addr = st.text_input("Address", value=chosen_cust.get("address") or "")
                        
                        type_idx = config.CUSTOMER_TYPES.index(chosen_cust["customer_type"]) if chosen_cust["customer_type"] in config.CUSTOMER_TYPES else 0
                        edit_type = st.selectbox("Customer Type", config.CUSTOMER_TYPES, index=type_idx)
                        edit_notes = st.text_area("Notes", value=chosen_cust.get("notes") or "")

                        submit_cust_edit = st.form_submit_button("💾 Update Customer", type="primary")

                        if submit_cust_edit:
                            try:
                                customer_service.update_customer(
                                    customer_id=chosen_cust["id"],
                                    name=edit_name,
                                    email=edit_email,
                                    phone=edit_phone,
                                    address=edit_addr,
                                    customer_type=edit_type,
                                    notes=edit_notes
                                )
                                st.success("Customer profile updated successfully!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")

            with col_del:
                with st.expander("🗑️ Delete Customer", expanded=False):
                    st.warning(f"Are you sure you want to remove customer **{chosen_cust['name']}**?")
                    st.caption("Existing orders will be preserved with customer unassigned.")
                    confirm_del = st.checkbox("Confirm customer removal", key="chk_confirm_del_cust")
                    if st.button("Delete Customer Record", type="secondary", disabled=not confirm_del):
                        try:
                            res = customer_service.delete_customer(chosen_cust["id"])
                            st.success(res["message"])
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
        else:
            st.info("No customers found. Add a customer in the 'Add New Customer' tab or load sample data.")

    # ------------------ TAB 2: ADD NEW CUSTOMER ------------------
    with tab_add:
        st.markdown("### ➕ Register New Customer")
        st.caption("Add a customer profile for billing, order dispatch, and records.")

        with st.form(key="add_customer_form", clear_on_submit=True):
            ac1, ac2 = st.columns(2)
            with ac1:
                name = st.text_input("Full Name *", placeholder="e.g. John Doe")
                email = st.text_input("Email Address", placeholder="e.g. john@example.com")
                phone = st.text_input("Phone Number", placeholder="e.g. +1-555-0199")

            with ac2:
                cust_type = st.selectbox("Account Type *", config.CUSTOMER_TYPES)
                address = st.text_input("Billing / Shipping Address", placeholder="e.g. 452 Elm Street, Suite 2")
                notes = st.text_area("Customer Notes", placeholder="Special preferences, delivery instructions...")

            submit_new_cust = st.form_submit_button("✨ Save Customer Record", type="primary", use_container_width=True)

            if submit_new_cust:
                try:
                    res = customer_service.create_customer(
                        name=name,
                        email=email,
                        phone=phone,
                        address=address,
                        customer_type=cust_type,
                        notes=notes
                    )
                    st.success(f"Customer **{res['name']}** successfully created!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    # ------------------ TAB 3: PURCHASE HISTORY DRILLDOWN ------------------
    with tab_history:
        st.markdown("### 📜 Customer Lifetime Purchase History")
        st.caption("Drill down into an individual customer's transaction timeline.")

        all_c = customer_service.get_all_customers()
        if not all_c:
            st.info("No customers available.")
        else:
            c_select_map = {f"{c['name']} (ID: {c['id']}) - {c['phone']}": c for c in all_c}
            chosen_drill = st.selectbox("Select Customer to Inspect:", list(c_select_map.keys()), key="drill_cust_sel")
            customer_info = c_select_map[chosen_drill]

            # Profile Header
            with st.container():
                st.markdown(f"""
                **Customer:** {customer_info['name']} | **Type:** {customer_info['customer_type']} | **Email:** {customer_info.get('email') or 'N/A'} | **Phone:** {customer_info.get('phone') or 'N/A'}  
                **Address:** {customer_info.get('address') or 'N/A'} | **Notes:** {customer_info.get('notes') or 'None'}
                """)

            orders_history = customer_service.get_customer_order_history(customer_info["id"])
            if orders_history:
                df_hist = pd.DataFrame(orders_history)[[
                    "order_number", "order_date", "subtotal", "discount_amount", "tax_amount", "total_amount", "payment_method", "payment_status", "order_status"
                ]]
                df_hist.columns = [
                    "Order Number", "Date", f"Subtotal ({sym})", f"Discount ({sym})", f"Tax ({sym})", f"Total ({sym})", "Payment Method", "Payment", "Status"
                ]
                st.dataframe(df_hist, use_container_width=True, hide_index=True)
            else:
                st.info(f"Customer '{customer_info['name']}' has not placed any orders yet.")
