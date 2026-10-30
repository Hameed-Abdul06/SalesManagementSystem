"""Main Application Entrypoint for the Sales Management System."""
import streamlit as st

# Streamlit Page Setup - Must be the very first Streamlit command
st.set_page_config(
    page_title="Apex Sales & Inventory Management System",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

from database.schema import init_db
from database.sample_data import seed_sample_data
from database.connection import get_db_cursor
from ui.styles import CUSTOM_CSS
from ui.dashboard import render_dashboard
from ui.products import render_products
from ui.customers import render_customers
from ui.orders import render_orders
from ui.history import render_history
from ui.reports import render_reports
import config

# Inject safe Custom CSS
if CUSTOM_CSS:
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# Ensure Database Tables Exist Safely
init_db()


def render_sidebar():
    """Render the navigation sidebar and utility actions."""
    with st.sidebar:
        st.markdown(f"## {config.APP_ICON} Apex Systems")
        st.caption(f"{config.APP_NAME} v1.0")
        st.markdown("---")

        navigation = st.radio(
            "Navigation Menu",
            [
                "📊 Dashboard",
                "🛒 Create New Order (POS)",
                "📦 Inventory & Products",
                "👥 Customers",
                "📜 Order History & Invoices",
                "📈 Analytics & Reports",
            ],
            index=0,
            key="app_nav_menu"
        )

        st.markdown("---")
        st.markdown("### 🛠️ Demo Tools & Settings")

        # Sample Data Loader
        if st.button("✨ Load Sample Demo Data", help="Populates products, customers, and historical sales"):
            result = seed_sample_data(force=False)
            if result.get("status") == "success":
                st.success(result["message"])
                st.rerun()
            else:
                st.info(result.get("message", "Database already initialized."))

        # Reset Database Option
        with st.expander("⚠️ Database Reset"):
            st.caption("Erase all products, customers, and orders to start clean.")
            confirm_reset = st.checkbox("Confirm complete database wipe", key="chk_wipe_db")
            if st.button("Erase All Data", type="secondary", disabled=not confirm_reset):
                with get_db_cursor() as cur:
                    cur.execute("DELETE FROM order_items")
                    cur.execute("DELETE FROM orders")
                    cur.execute("DELETE FROM products")
                    cur.execute("DELETE FROM customers")
                st.session_state.cart_items = []
                st.warning("Database completely wiped. Clean state initialized.")
                st.rerun()

        st.markdown("---")
        st.caption("🎓 **College Project Submission**  \nBuilt with Python, Streamlit, SQLite & Plotly.")

        return navigation


def main():
    """Application main routing controller."""
    # Prominent Header Banner visible on every screen
    h_col1, h_col2 = st.columns([5, 1])
    with h_col1:
        st.title(f"{config.APP_ICON} {config.APP_NAME}")
        st.caption(f"{config.APP_SUBTITLE} • Python, SQLite & Streamlit")
    with h_col2:
        st.write("")
        st.success("🟢 System Online")

    selected_page = render_sidebar()

    try:
        if selected_page == "📊 Dashboard":
            render_dashboard()
        elif selected_page == "🛒 Create New Order (POS)":
            render_orders()
        elif selected_page == "📦 Inventory & Products":
            render_products()
        elif selected_page == "👥 Customers":
            render_customers()
        elif selected_page == "📜 Order History & Invoices":
            render_history()
        elif selected_page == "📈 Analytics & Reports":
            render_reports()
    except Exception as err:
        st.error(f"An unexpected error occurred while rendering '{selected_page}': {err}")
        st.exception(err)


# Execute main controller
main()
