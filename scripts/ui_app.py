import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from db_manager import upsert_monitoring_settings, get_monitoring_settings

from db_manager import (
    create_db,
    add_customer,
    add_company,
    add_product,
    get_product_dashboard_rows,
)
from price_checker import run_price_check_with_detection


st.set_page_config(page_title="Price Monitoring Agent", layout="wide")


# ---------- Helpers ----------

def compute_next_check(frequency: str):
    now = datetime.now()

    if frequency == "Daily":
        return now + timedelta(days=1)
    elif frequency == "Weekly":
        return now + timedelta(weeks=1)
    elif frequency == "Monthly":
        return now + timedelta(days=30)

    return now + timedelta(days=1)


def initialize_session_state():
    defaults = {
        "monitoring_settings": {},  # keyed by product_name for now
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ---------- App Init ----------

create_db()
initialize_session_state()

st.title("Price Monitoring Agent")
st.caption("Track competitor pricing, monitor changes, and manage alert settings.")


# ---------- Sidebar ----------

st.sidebar.header("Actions")

if st.sidebar.button("Run Price Check Now", use_container_width=True):
    try:
        run_price_check_with_detection()
        st.sidebar.success("Price check completed.")
    except Exception as e:
        st.sidebar.error(f"Price check failed: {e}")


# ---------- Tabs ----------

tab1, tab2, tab3 = st.tabs(
    ["Add Products", "Monitoring Settings", "Dashboard"]
)


# ---------- Tab 1: Add Products ----------

with tab1:
    st.subheader("Add Customer, Company, and Product")

    with st.form("add_product_form"):
        customer_name = st.text_input("Customer Name", placeholder="Apex Nutrition")
        company_name = st.text_input("Company Name", placeholder="Huel")
        website = st.text_input("Company Website", placeholder="https://huel.com/")
        product_name = st.text_input("Product Name", placeholder="Huel Protein Powder")
        product_url = st.text_input(
            "Product URL",
            placeholder="https://huel.com/products/huel-complete-protein"
        )

        submitted = st.form_submit_button("Add Product")

        if submitted:
            if not all([customer_name, company_name, website, product_name, product_url]):
                st.error("Please complete all fields.")
            else:
                try:
                    cust_id = add_customer(customer_name)
                    company_id = add_company(cust_id, company_name, website)
                    add_product(company_id, product_name, product_url)
                    st.success(f"Added {product_name} for {company_name}.")
                except Exception as e:
                    st.error(f"Failed to add product: {e}")


# ---------- Tab 2: Monitoring Settings ----------

with tab2:
    st.subheader("Monitoring Settings")

    dashboard_rows = get_product_dashboard_rows()

    if not dashboard_rows:
        st.info("No products found yet. Add a product first.")
    else:
        product_map = {row["product_name"]: row for row in dashboard_rows}

        selected_product_name = st.selectbox(
            "Select Product",
            list(product_map.keys())
        )

        selected_product = product_map[selected_product_name]
        product_id = selected_product["product_id"]

        db_settings = get_monitoring_settings(product_id)

        if db_settings:
            existing_settings = {
                "alert_email": db_settings["alert_email"],
                "frequency": db_settings["check_frequency"],
                "threshold_pct": db_settings["alert_threshold_pct"],
                "next_check_at": db_settings["next_check_at"],
            }
        else:
            existing_settings = {
                "alert_email": "price.monitor.agent.hc@gmail.com",
                "frequency": "Daily",
                "threshold_pct": 5.0,
                "next_check_at": compute_next_check("Daily"),
            }

        with st.form("monitoring_settings_form"):
            alert_email = st.text_input(
                "Alert Email",
                value=existing_settings["alert_email"]
            )

            frequency = st.selectbox(
                "Check Frequency",
                ["Daily", "Weekly", "Monthly"],
                index=["Daily", "Weekly", "Monthly"].index(existing_settings["frequency"])
            )

            threshold_pct = st.number_input(
                "Alert Threshold (%)",
                min_value=0.0,
                value=float(existing_settings["threshold_pct"]),
                step=1.0
            )

            save_settings = st.form_submit_button("Save Settings")

            if save_settings:
                next_check_at = compute_next_check(frequency)

                st.session_state["monitoring_settings"][selected_product_name] = {
                    "alert_email": alert_email,
                    "frequency": frequency,
                    "threshold_pct": threshold_pct,
                    "next_check_at": next_check_at,
                }
                upsert_monitoring_settings(
                    product_id=product_id,
                    alert_email=alert_email,
                    check_frequency=frequency,
                    alert_threshold_pct=threshold_pct,
                    next_check_at=next_check_at,
                )
                st.success(f"Settings saved for {selected_product_name}.")

        current_settings = db_settings

        if current_settings:
            st.markdown("### Current Settings")

            # Handle datetime safely (SQLite may return string)
            next_check = current_settings["next_check_at"]

            if next_check and isinstance(next_check, str):
                try:
                    next_check = datetime.fromisoformat(next_check)
                except:
                    pass

            if hasattr(next_check, "strftime"):
                next_check_display = next_check.strftime("%Y-%m-%d %H:%M:%S")
            else:
                next_check_display = next_check

            st.write(f"**Alert Email:** {current_settings['alert_email']}")
            st.write(f"**Frequency:** {current_settings['check_frequency']}")
            st.write(f"**Threshold:** {current_settings['alert_threshold_pct']}%")
            st.write(f"**Next Check:** {next_check_display}")


# ---------- Tab 3: Dashboard ----------

with tab3:
    st.subheader("Tracked Products Dashboard")

    dashboard_rows = get_product_dashboard_rows()

    if not dashboard_rows:
        st.info("No tracked products yet.")
    else:
        df = pd.DataFrame(dashboard_rows)

        display_columns = [
            "company_name",
            "product_name",
            "latest_price",
            "previous_price",
            "change",
            "pct_change",
            "currency",
            "last_checked",
            "source",
            "product_url",
        ]

        available_columns = [col for col in display_columns if col in df.columns]
        df = df[available_columns]

        st.dataframe(df, use_container_width=True)

        st.markdown("### Summary")
        st.write(f"**Tracked Products:** {len(df)}")

        if "pct_change" in df.columns:
            changed_products = df["pct_change"].notna().sum()
            st.write(f"**Products with price history:** {changed_products}")