import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client, Client

# Page Config
st.set_page_config(page_title="Dighasri Channel Center POS System", layout="wide")

# Supabase Credentials from Streamlit Secrets
@st.cache_resource
def init_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

try:
    supabase: Client = init_supabase()
except Exception as e:
    st.error(f"Supabase Connection Error: {e}")
    st.stop()

# Helper function to execute queries safely and reset index for neat 1, 2, 3... numbering
def get_data(table_name):
    try:
        res = supabase.table(table_name).select("*").order("id", desc=True).execute()
        df = pd.DataFrame(res.data)
        if not df.empty:
            df.index = range(1, len(df) + 1)  # Sets 1, 2, 3, 4... index numbering
        return df
    except Exception as e:
        st.warning(f"Error fetching {table_name}: {e}")
        return pd.DataFrame()

# Session State for Cart and User Login
if "logged_in" not in st.session_state:
    st.session_state.logged_in = True
    st.session_state.username = "admin"
    st.session_state.role = "Admin"

if "cart" not in st.session_state:
    st.session_state.cart = []

# Title & User Info Sidebar
st.sidebar.title(f"👤 User: {st.session_state.username}")
st.sidebar.write(f"Role: {st.session_state.role}")

st.title("🏥 Dighasri Channel Center POS System")

# Navigation Tabs
tab1, tab2, tab3, tab4 = st.tabs(["🛒 POS Billing", "📦 Master Settings & Inventory", "📊 Reports & Accounts", "⚙️ User Management"])

# --- TAB 1: POS BILLING ---
with tab1:
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("🛒 Current Order / Cart")
        patient_ref = st.text_input("Patient / Ref No", value="25")
        
        if not st.session_state.cart:
            st.info("Cart එක හිස්ව පවතී. දකුණු පසින් අවශ්‍ය අයිතම එකතු කරන්න.")
        else:
            cart_df = pd.DataFrame(st.session_state.cart)
            cart_df.index = range(1, len(cart_df) + 1)
            st.dataframe(cart_df, use_container_width=True)
            
            total_amt = sum(item["Price"] for item in st.session_state.cart)
            st.markdown(f"### Total: **LKR {total_amt:.2f}**")
            
            if st.button("💳 Print & Complete Sale", type="primary"):
                try:
                    supabase.table("sales").insert({
                        "ref_no": patient_ref,
                        "total_amount": total_amt,
                        "created_at": datetime.now().isoformat()
                    }).execute()
                    st.success("Sale Recorded Successfully to Cloud!")
                    st.session_state.cart = []
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to record sale: {e}")

    with col2:
        st.subheader("⚡ Quick Category Select")
        category = st.radio("Category", ["Laboratory", "Pharmacy", "OPD Procedures", "Channeling", "Scanning"], horizontal=True)
        
        if category == "Laboratory":
            lab_test = st.selectbox("Select Laboratory Test", ["Full Blood Count FBC", "Blood Sugar", "Lipid Profile"])
            fee = 400.00
            st.markdown(f"### Fee: **LKR {fee:.2f}**")
            
            if st.button("➕ Add Lab Test to Cart"):
                st.session_state.cart.append({"Item": lab_test, "Category": category, "Price": fee})
                st.success(f"Added {lab_test} to Cart!")
                st.rerun()

# --- TAB 2: INVENTORY ---
with tab2:
    st.subheader("📦 Inventory Management")
    st.write("Cloud Real-time Inventory Data")
    inv_df = get_data("inventory")
    st.dataframe(inv_df, use_container_width=True)

# --- TAB 3: REPORTS ---
with tab3:
    st.subheader("📊 Reports & Accounts")
    sales_df = get_data("sales")
    st.dataframe(sales_df, use_container_width=True)

# --- TAB 4: USERS ---
with tab4:
    st.subheader("⚙️ User Management")
    users_df = get_data("users")
    st.dataframe(users_df, use_container_width=True)
