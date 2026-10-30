"""Product Management UI: Add, edit, delete, search, filter, and adjust inventory levels."""
import streamlit as st
import pandas as pd
from services import product_service
import config


def render_products():
    """Render the Product & Inventory catalog management interface."""
    st.markdown("## 📦 Product & Inventory Catalog")
    st.caption("Manage product details, pricing, categories, and stock reorder levels.")

    tab_catalog, tab_add, tab_stock = st.tabs(["📋 Product Catalog", "➕ Add New Product", "🔄 Quick Stock Adjustment"])

    # ------------------ TAB 1: PRODUCT CATALOG ------------------
    with tab_catalog:
        col_s1, col_s2, col_s3 = st.columns([3, 2, 2])
        with col_s1:
            search_query = st.text_input("🔍 Search Products", placeholder="Search by name, SKU, or description...", key="prod_search")
        with col_s2:
            cat_filter = st.selectbox("Category Filter", ["All"] + config.PRODUCT_CATEGORIES, key="prod_cat_filter")
        with col_s3:
            stock_filter = st.selectbox("Stock Filter", ["All", "In Stock", "Low Stock", "Out of Stock"], key="prod_stock_filter")

        stock_param = stock_filter if stock_filter != "All" else None
        products = product_service.get_all_products(
            category=cat_filter,
            search_query=search_query,
            stock_status=stock_param
        )

        sym = config.CURRENCY_SYMBOL

        if products:
            # Metrics bar
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Shown", len(products))
            m2.metric("Total Units in Stock", sum(p["stock_quantity"] for p in products))
            m3.metric("Inventory Cost Value", f"{sym}{sum(p['stock_quantity'] * p['cost_price'] for p in products):,.2f}")
            m4.metric("Potential Retail Value", f"{sym}{sum(p['stock_quantity'] * p['selling_price'] for p in products):,.2f}")

            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

            # Products Table
            df = pd.DataFrame(products)[[
                "id", "sku", "name", "category", "cost_price", "selling_price", "stock_quantity", "low_stock_threshold"
            ]]
            df["profit_margin_%"] = ((df["selling_price"] - df["cost_price"]) / df["selling_price"] * 100).round(1)
            
            df.columns = ["ID", "SKU", "Product Name", "Category", f"Cost ({sym})", f"Price ({sym})", "Stock", "Min Alert", "Margin %"]
            st.dataframe(df, use_container_width=True, hide_index=True)

            # Export button
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Export Products to CSV",
                data=csv,
                file_name="products_inventory.csv",
                mime="text/csv"
            )

            st.divider()

            # Product Actions: Edit or Delete
            st.markdown("### ⚙️ Product Operations (Edit / Remove)")
            prod_options = {f"{p['sku']} - {p['name']} (ID: {p['id']})": p for p in products}
            selected_label = st.selectbox("Select Product to Modify:", list(prod_options.keys()), key="prod_selected_modify")
            selected_product = prod_options[selected_label]

            col_edit, col_del = st.columns([3, 2])

            with col_edit:
                with st.expander("✏️ Edit Product Details", expanded=False):
                    with st.form(key=f"edit_form_{selected_product['id']}"):
                        edit_name = st.text_input("Product Name", value=selected_product["name"])
                        edit_sku = st.text_input("SKU / Barcode", value=selected_product["sku"])
                        
                        cat_idx = config.PRODUCT_CATEGORIES.index(selected_product["category"]) if selected_product["category"] in config.PRODUCT_CATEGORIES else 0
                        edit_cat = st.selectbox("Category", config.PRODUCT_CATEGORIES, index=cat_idx)
                        
                        e_c1, e_c2 = st.columns(2)
                        with e_c1:
                            edit_cost = st.number_input("Cost Price", min_value=0.0, value=float(selected_product["cost_price"]), step=0.5, format="%.2f")
                        with e_c2:
                            edit_price = st.number_input("Selling Price", min_value=0.0, value=float(selected_product["selling_price"]), step=0.5, format="%.2f")

                        e_s1, e_s2 = st.columns(2)
                        with e_s1:
                            edit_stock = st.number_input("Current Stock", min_value=0, value=int(selected_product["stock_quantity"]), step=1)
                        with e_s2:
                            edit_low = st.number_input("Low Stock Threshold", min_value=0, value=int(selected_product["low_stock_threshold"]), step=1)

                        edit_desc = st.text_area("Description", value=selected_product.get("description") or "")
                        submit_edit = st.form_submit_button("💾 Save Changes", type="primary")

                        if submit_edit:
                            try:
                                product_service.update_product(
                                    product_id=selected_product["id"],
                                    sku=edit_sku,
                                    name=edit_name,
                                    category=edit_cat,
                                    cost_price=edit_cost,
                                    selling_price=edit_price,
                                    stock_quantity=edit_stock,
                                    low_stock_threshold=edit_low,
                                    description=edit_desc
                                )
                                st.success(f"Product '{edit_name}' updated successfully!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error updating product: {e}")

            with col_del:
                with st.expander("🗑️ Delete / Archive Product", expanded=False):
                    st.warning(f"You are selecting to delete: **{selected_product['name']}** ({selected_product['sku']}).")
                    st.caption("Note: Products with sales history will be safely archived to protect invoices.")
                    confirm_delete = st.checkbox("I understand and confirm this deletion.", key="chk_confirm_del")
                    
                    if st.button("Delete Product", type="secondary", disabled=not confirm_delete):
                        try:
                            res = product_service.delete_product(selected_product["id"])
                            st.success(res["message"])
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error deleting product: {e}")
        else:
            st.info("No products found matching the criteria. Use the 'Add New Product' tab to create products or load sample data from the sidebar.")

    # ------------------ TAB 2: ADD NEW PRODUCT ------------------
    with tab_add:
        st.markdown("### ➕ Register a New Product")
        st.caption("Add a new product item into the inventory database.")

        with st.form(key="add_product_form", clear_on_submit=True):
            f_col1, f_col2 = st.columns(2)
            with f_col1:
                p_name = st.text_input("Product Name *", placeholder="e.g. Ergonomic Bluetooth Mouse")
                p_sku = st.text_input("SKU / Barcode Code *", placeholder="e.g. ELEC-009")
                p_cat = st.selectbox("Product Category *", config.PRODUCT_CATEGORIES)

            with f_col2:
                p_cost = st.number_input(f"Cost Price ({sym}) *", min_value=0.0, value=10.0, step=0.5, format="%.2f")
                p_price = st.number_input(f"Selling Price ({sym}) *", min_value=0.0, value=19.99, step=0.5, format="%.2f")
                p_stock = st.number_input("Initial Stock Quantity *", min_value=0, value=25, step=1)
                p_threshold = st.number_input("Low Stock Alert Threshold", min_value=0, value=config.DEFAULT_LOW_STOCK_THRESHOLD, step=1)

            p_desc = st.text_area("Product Description", placeholder="Optional item details, model, specifications...")

            submit_product = st.form_submit_button("✨ Create Product", type="primary", use_container_width=True)

            if submit_product:
                try:
                    product_service.create_product(
                        sku=p_sku,
                        name=p_name,
                        category=p_cat,
                        cost_price=p_cost,
                        selling_price=p_price,
                        stock_quantity=p_stock,
                        low_stock_threshold=p_threshold,
                        description=p_desc
                    )
                    st.success(f"Successfully added product: **{p_name}** ({p_sku})")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    # ------------------ TAB 3: QUICK STOCK ADJUSTMENT ------------------
    with tab_stock:
        st.markdown("### 🔄 Quick Inventory Level Adjustment")
        st.caption("Quickly restock inventory or record write-offs/shrinkage.")

        all_prods = product_service.get_all_products()
        if not all_prods:
            st.info("No products in the catalog to adjust.")
        else:
            stock_map = {f"{p['sku']} - {p['name']} (Current Stock: {p['stock_quantity']})": p for p in all_prods}
            chosen_item = st.selectbox("Select Product to Adjust:", list(stock_map.keys()), key="quick_stock_prod")
            prod_data = stock_map[chosen_item]

            col_adj1, col_adj2 = st.columns(2)
            with col_adj1:
                adj_type = st.radio("Adjustment Type:", ["Restock / Add (+)", "Reduce / Write-Off (-)"], horizontal=True)
                qty_change = st.number_input("Quantity:", min_value=1, value=10, step=1)
            with col_adj2:
                reason = st.text_input("Reason / Note:", placeholder="e.g., Supplier shipment, Damaged goods, Stock audit")

            if st.button("Apply Stock Adjustment", type="primary"):
                effective_delta = qty_change if "Restock" in adj_type else -qty_change
                try:
                    res = product_service.adjust_stock(prod_data["id"], effective_delta, reason)
                    st.success(f"Stock for '{prod_data['name']}' updated from {res['previous_stock']} to {res['new_stock']} units!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Adjustment failed: {e}")
