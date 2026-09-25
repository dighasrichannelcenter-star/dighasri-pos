import sqlite3
from datetime import datetime, timedelta
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from supabase import create_client

# ---------------------------------------------------------
# SUPABASE CLOUD CONNECTION
# ---------------------------------------------------------
SUPABASE_URL = "https://rpgidxxpobulzrqzwvnc.supabase.co"
SUPABASE_KEY = "sb_publishable_NW29EDWrexNancffxu3xow_E384sMq0"

try:
    if "SUPABASE_URL" in st.secrets:
        SUPABASE_URL = st.secrets["SUPABASE_URL"]
    if "SUPABASE_KEY" in st.secrets:
        SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except Exception:
    pass

@st.cache_resource
def init_supabase():
    try:
        if SUPABASE_URL and SUPABASE_KEY:
            return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception:
        return None
    return None

supabase = init_supabase()

def sync_to_cloud(data_dict):
    if supabase:
        try:
            supabase.table("sales_history").insert(data_dict).execute()
        except Exception:
            pass

# Database Connection
conn = sqlite3.connect('dighasri_hospital.db', check_same_thread=False)
c = conn.cursor()

# ---------------------------------------------------------
# DATABASE TABLES CREATION & MIGRATION
# ---------------------------------------------------------
c.execute('''CREATE TABLE IF NOT EXISTS users
             (username TEXT PRIMARY KEY, password TEXT, role TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS inventory
             (id INTEGER PRIMARY KEY AUTOINCREMENT, supplier_name TEXT, item_name TEXT, brand_name TEXT, category TEXT,
              dosage TEXT, cost_price REAL, unit_price REAL, profit_margin REAL,
              stock_qty INTEGER, expiry_date TEXT, reorder_level INTEGER, batch_no TEXT, barcode TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS lab_tests
             (id INTEGER PRIMARY KEY AUTOINCREMENT, test_name TEXT, patient_fee REAL, lab_cost REAL, center_commission REAL)''')

c.execute('''CREATE TABLE IF NOT EXISTS doctors
             (id INTEGER PRIMARY KEY AUTOINCREMENT, doc_name TEXT, designation TEXT, doc_fee REAL, center_fee REAL, doc_scan_fee REAL, center_scan_fee REAL)''')

c.execute('''CREATE TABLE IF NOT EXISTS opd_procedures
             (id INTEGER PRIMARY KEY AUTOINCREMENT, proc_name TEXT, default_doc_fee REAL, center_fee REAL)''')

c.execute('''CREATE TABLE IF NOT EXISTS preset_prescriptions
             (id INTEGER PRIMARY KEY AUTOINCREMENT, preset_name TEXT, items_json TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS sales_history
             (id INTEGER PRIMARY KEY AUTOINCREMENT, prescription_no TEXT, bill_type TEXT, doctor_name TEXT, bill_details TEXT,
              total_amount REAL, doc_fee REAL, lab_cost REAL, center_profit REAL, date TIMESTAMP, cost_price REAL DEFAULT 0.0, discount REAL DEFAULT 0.0, status TEXT DEFAULT 'COMPLETED')''')

def safe_add_column(table_name, column_def):
    try:
        c.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_def}")
    except sqlite3.OperationalError:
        pass

safe_add_column('inventory', "brand_name TEXT DEFAULT ''")
safe_add_column('sales_history', "status TEXT DEFAULT 'COMPLETED'")

# Seed Default Users if empty
c.execute("SELECT COUNT(*) FROM users")
if c.fetchone()[0] == 0:
    default_users = [
        ("admin", "admin123", "Admin"),
        ("supervisor", "super123", "Supervisor"),
        ("cashier", "cashier123", "Cashier")
    ]
    c.executemany("INSERT INTO users VALUES (?, ?, ?)", default_users)

# Seed Default OPD Procedures if empty
c.execute("SELECT COUNT(*) FROM opd_procedures")
if c.fetchone()[0] == 0:
    default_procs = [
        ("General OPD Consultation", 350.0, 150.0),
        ("ECG Test", 500.0, 500.0),
        ("Saline Administration", 400.0, 300.0),
        ("Dressing", 300.0, 200.0),
        ("Catheterization", 800.0, 400.0),
        ("Depo Injection", 300.0, 200.0),
        ("Toxoid Injection", 250.0, 150.0),
        ("Nebulization", 300.0, 200.0)
    ]
    c.executemany("INSERT INTO opd_procedures (proc_name, default_doc_fee, center_fee) VALUES (?, ?, ?)", default_procs)

conn.commit()

# Initialize Session States
if 'pos_cart' not in st.session_state:
    st.session_state.pos_cart = []
if 'print_html' not in st.session_state:
    st.session_state.print_html = None
if 'user' not in st.session_state:
    st.session_state.user = None

# Helper function to reset row index sequentially (1, 2, 3...)
def show_table(df, **kwargs):
    if not df.empty:
        df_copy = df.copy()
        df_copy.index = range(1, len(df_copy) + 1)
        st.dataframe(df_copy, **kwargs)
    else:
        st.dataframe(df, **kwargs)

# --- INSTANT PRINT SCRIPT (CENTER-ALIGNED FOR 58MM PRINTERS) ---
def trigger_instant_print(bill_html_content, unique_key):
    full_html = f"""
    <div id="printArea_{unique_key}" style="font-family: 'Courier New', Courier, monospace; font-size: 7.5pt; font-weight: bold; width: 140px; padding: 0px; margin: 0 auto; text-align: center; color: #000; line-height: 1.2; word-wrap: break-word;">
        {bill_html_content}
    </div>
    <script>
    setTimeout(function() {{
        var printContents = document.getElementById('printArea_{unique_key}').innerHTML;
        var frame = document.createElement('iframe');
        frame.name = "printFrame_{unique_key}";
        frame.style.position = "absolute";
        frame.style.top = "-10000px";
        document.body.appendChild(frame);
        var frameDoc = frame.contentWindow ? frame.contentWindow : frame.contentDocument.document ? frame.contentDocument.document : frame.contentDocument;
        frameDoc.document.open();
        frameDoc.document.write('<html><head><title>Print Receipt</title>');
        frameDoc.document.write('<style>@page {{ margin: 0px; size: 58mm auto; }} body {{ font-family: "Courier New", Courier, monospace; font-size: 7.5pt; font-weight: bold; width: 140px; margin: 0 auto; padding: 0; text-align: center; color: #000; word-wrap: break-word; }} hr {{ border: none; border-top: 1px dashed #000; margin: 3px 0; }}</style>');
        frameDoc.document.write('</head><body>');
        frameDoc.document.write(printContents);
        frameDoc.document.write('</body></html>');
        frameDoc.document.close();
        setTimeout(function() {{
            window.frames["printFrame_{unique_key}"].focus();
            window.frames["printFrame_{unique_key}"].print();
        }}, 500);
    }}, 200);
    </script>
    """
    components.html(full_html, height=100)

# ---------------------------------------------------------
# APPLICATION SETUP
# ---------------------------------------------------------
st.set_page_config(page_title="Dighasri Channel Center POS", page_icon="🏥", layout="wide")

# Render Instant Print Script
if st.session_state.print_html:
    trigger_instant_print(st.session_state.print_html, "bill_print")
    st.session_state.print_html = None

# ---------------------------------------------------------
# LOGIN SYSTEM
# ---------------------------------------------------------
if st.session_state.user is None:
    st.title("🔐 Dighasri Hospital POS - User Login")
   
    col_l1, col_l2, col_l3 = st.columns([1, 1.5, 1])
    with col_l2:
        st.subheader("Login to Access System")
        u_name = st.text_input("Username (පරිශීලක නාමය):")
        u_pass = st.text_input("Password (මුරපදය):", type="password")
       
        if st.button("🔑 Login", type="primary", use_container_width=True):
            c.execute("SELECT username, role FROM users WHERE username=? AND password=?", (u_name, u_pass))
            res = c.fetchone()
            if res:
                st.session_state.user = {'username': res[0], 'role': res[1]}
                st.success(f"සාර්ථකව ප්‍රවේශ විය! (Role: {res[1]})")
                st.rerun()
            else:
                st.error("කරුණාකර නිවැරදි Username සහ Password ඇතුළත් කරන්න.")
       
        st.info("""
        **Default Passwords (මුලික මුරපද):**
        * **Admin:** `admin` / `admin123`
        * **Supervisor:** `supervisor` / `super123`
        * **Cashier:** `cashier` / `cashier123`
        """)
    st.stop()

# ---------------------------------------------------------
# MAIN INTERFACE (AFTER LOGIN)
# ---------------------------------------------------------
st.sidebar.title(f"👤 User: {st.session_state.user['username']}")
st.sidebar.markdown(f"**Role (තනතුර):** `{st.session_state.user['role']}`")
if st.sidebar.button("🚪 Logout (ඉවත් වන්න)", use_container_width=True):
    st.session_state.user = None
    st.session_state.pos_cart = []
    st.rerun()

st.title("🏥 Dighasri Channel Center POS System")

# Navigation Tabs according to Role
user_role = st.session_state.user['role']

if user_role == "Admin":
    available_tabs = ["🛒 POS Billing", "📦 Master Settings & Inventory", "📊 Reports & Accounts", "⚙️ User Management"]
elif user_role == "Supervisor":
    available_tabs = ["🛒 POS Billing", "📦 Master Settings & Inventory", "📊 Reports & Accounts"]
else:  # Cashier
    available_tabs = ["🛒 POS Billing", "📊 Reports & Accounts"]

tabs = st.tabs(available_tabs)

# ---------------------------------------------------------
# TAB 1: UNIFIED POS BILLING
# ---------------------------------------------------------
with tabs[0]:
    col_left, col_right = st.columns([1.2, 1.8])
   
    # LEFT PANEL: CART & PAYMENT
    with col_left:
        st.subheader("🛒 Current Order / Cart")
        ref_no = st.text_input("Patient / Ref No:", value="REF-1001")
       
        if st.session_state.pos_cart:
            cart_df = pd.DataFrame(st.session_state.pos_cart)
            show_table(cart_df[['display_name', 'qty', 'unit_price', 'total_price']], use_container_width=True)
           
            subtotal = cart_df['total_price'].sum()
            st.metric("Total Amount", f"LKR {subtotal:.2f}")
           
            st.markdown("---")
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                paid_amt = st.number_input("Paid Amount (ලැබුණු මුදල LKR):", min_value=0.0, value=float(subtotal), step=50.0)
            with col_p2:
                balance_amt = max(0.0, paid_amt - subtotal)
                st.metric("Balance (ඉතිරි මුදල)", f"LKR {balance_amt:.2f}")
               
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                if st.button("🗑️ Clear Cart", use_container_width=True):
                    st.session_state.pos_cart = []
                    st.rerun()
           
            with col_b2:
                if st.button("💾 Checkout & Print Bill", type="primary", use_container_width=True):
                    bill_items_html = ""
                    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                   
                    for item in st.session_state.pos_cart:
                        print_title = "Laboratory Charges" if item['category'] == "Laboratory" else item['display_name']
                        bill_items_html += f"<div>{print_title}<br>{item['qty']} x {item['unit_price']:.2f} = LKR {item['total_price']:.2f}</div>"
                       
                        dt_now = str(datetime.now())
                        if item['category'] == 'Pharmacy':
                            c.execute("UPDATE inventory SET stock_qty = stock_qty - ? WHERE id = ?", (item['qty'], item['id']))
                            cost_tot = item['qty'] * item.get('cost_price', 0.0)
                            c.execute("INSERT INTO sales_history (prescription_no, bill_type, doctor_name, bill_details, total_amount, doc_fee, lab_cost, center_profit, cost_price, date, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                      (ref_no, 'Pharmacy', '-', f"{item['id']}|{item['display_name']} x {item['qty']}", item['total_price'], 0.0, 0.0, item['total_price'] - cost_tot, cost_tot, dt_now, 'COMPLETED'))
                            sync_to_cloud({
                                'prescription_no': ref_no, 'bill_type': 'Pharmacy', 'doctor_name': '-',
                                'bill_details': f"{item['id']}|{item['display_name']} x {item['qty']}",
                                'total_amount': item['total_price'], 'doc_fee': 0.0, 'lab_cost': 0.0,
                                'center_profit': item['total_price'] - cost_tot, 'cost_price': cost_tot, 'date': dt_now, 'status': 'COMPLETED'
                            })
                       
                        elif item['category'] == 'Laboratory':
                            c.execute("INSERT INTO sales_history (prescription_no, bill_type, doctor_name, bill_details, total_amount, doc_fee, lab_cost, center_profit, date, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                      (ref_no, 'Laboratory', '-', item['display_name'], item['total_price'], 0.0, item['lab_cost'], item['center_comm'], dt_now, 'COMPLETED'))
                            sync_to_cloud({
                                'prescription_no': ref_no, 'bill_type': 'Laboratory', 'doctor_name': '-',
                                'bill_details': item['display_name'], 'total_amount': item['total_price'],
                                'doc_fee': 0.0, 'lab_cost': item['lab_cost'], 'center_profit': item['center_comm'], 'date': dt_now, 'status': 'COMPLETED'
                            })
                       
                        elif item['category'] in ['OPD', 'Channeling', 'Scanning']:
                            c.execute("INSERT INTO sales_history (prescription_no, bill_type, doctor_name, bill_details, total_amount, doc_fee, lab_cost, center_profit, date, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                      (ref_no, item['category'], item.get('doctor_name', '-'), item['display_name'], item['total_price'], item.get('doc_fee', 0.0), 0.0, item.get('center_profit', 0.0), dt_now, 'COMPLETED'))
                            sync_to_cloud({
                                'prescription_no': ref_no, 'bill_type': item['category'], 'doctor_name': item.get('doctor_name', '-'),
                                'bill_details': item['display_name'], 'total_amount': item['total_price'],
                                'doc_fee': item.get('doc_fee', 0.0), 'lab_cost': 0.0, 'center_profit': item.get('center_profit', 0.0), 'date': dt_now, 'status': 'COMPLETED'
                            })
                   
                    conn.commit()
                   
                    st.session_state.print_html = f"""
                    <div style="text-align: center;">
                        <b style="font-size: 8pt;">DIGHASRI CHANNEL CENTER</b><br>
                        <span>Official Receipt</span><br>
                        <small style="font-size: 6.5pt;">{now_str}</small>
                    </div>
                    <hr style="border: 1px dashed #000;">
                    <div style="text-align: center;">Ref No : {ref_no}</div>
                    <hr style="border: 1px dashed #000;">
                    <div style="text-align: center;">
                    {bill_items_html}
                    </div>
                    <hr style="border: 1px dashed #000;">
                    <div style="text-align: center;"><b>NET TOTAL : LKR {subtotal:.2f}</b></div>
                    <div style="text-align: center;">Paid Amt : LKR {paid_amt:.2f}</div>
                    <div style="text-align: center;">Balance  : LKR {balance_amt:.2f}</div>
                    <hr style="border: 1px dashed #000;">
                    <div style="text-align: center;"><small style="font-size: 6.5pt;">Thank You Come Again!</small></div>
                    """
                   
                    st.session_state.pos_cart = []
                    st.success("✅ Order Processed & Receipt Sent to Printer!")
                    st.rerun()
                   
        else:
            st.info("Cart එක හිස්ව පවතී. දකුණු පසින් අවශ්‍ය අයිතම එකතු කරන්න.")

    # RIGHT PANEL: QUICK CATEGORY SELECT
    with col_right:
        st.subheader("⚡ Quick Category Select")
       
        sub_tab1, sub_tab2, sub_tab3, sub_tab4, sub_tab5 = st.tabs(["🧪 Laboratory", "💊 Pharmacy", "🩺 OPD Procedures", "👨‍⚕️ Channeling", "🖥️ Scanning"])
       
        # 1. LAB SELECTION
        with sub_tab1:
            labs_df = pd.read_sql_query("SELECT * FROM lab_tests", conn)
            if not labs_df.empty:
                col_l1, col_l2 = st.columns([2, 1])
                with col_l1:
                    selected_test = st.selectbox("Select Laboratory Test:", labs_df['test_name'].tolist())
                with col_l2:
                    t_row = labs_df[labs_df['test_name'] == selected_test].iloc[0]
                    st.metric("Fee", f"LKR {t_row['patient_fee']:.2f}")
               
                if st.button("➕ Add Lab Test to Cart", use_container_width=True):
                    st.session_state.pos_cart.append({
                        'category': 'Laboratory',
                        'id': t_row['id'],
                        'display_name': f"Lab: {t_row['test_name']}",
                        'qty': 1,
                        'unit_price': float(t_row['patient_fee']),
                        'total_price': float(t_row['patient_fee']),
                        'lab_cost': float(t_row['lab_cost']),
                        'center_comm': float(t_row['center_commission'])
                    })
                    st.success(f"Added {t_row['test_name']} to Cart!")
                    st.rerun()
            else:
                st.warning("ලැබ් ටෙස්ට් සටහන් කර නොමැත.")

        # 2. PHARMACY SELECTION
        with sub_tab2:
            inv_df = pd.read_sql_query("SELECT * FROM inventory WHERE stock_qty > 0", conn)
            if not inv_df.empty:
                inv_df['display_label'] = inv_df['item_name'] + " (" + inv_df['brand_name'] + ")"
                col_p1, col_p2 = st.columns([2, 1])
                with col_p1:
                    selected_med_label = st.selectbox("Select Medicine / Item:", inv_df['display_label'].tolist())
                    m_row = inv_df[inv_df['display_label'] == selected_med_label].iloc[0]
                with col_p2:
                    med_qty = st.number_input(f"Qty (Max: {m_row['stock_qty']}):", min_value=1, max_value=int(m_row['stock_qty']), value=1)
               
                if st.button("➕ Add Medicine to Cart", use_container_width=True):
                    st.session_state.pos_cart.append({
                        'category': 'Pharmacy',
                        'id': m_row['id'],
                        'display_name': f"{m_row['item_name']} ({m_row['brand_name']})",
                        'qty': med_qty,
                        'unit_price': float(m_row['unit_price']),
                        'total_price': float(m_row['unit_price']) * med_qty,
                        'cost_price': float(m_row['cost_price'])
                    })
                    st.success(f"Added {m_row['item_name']} to Cart!")
                    st.rerun()
            else:
                st.warning("Pharmacy stock එකෙහි ඖෂධ නොමැත.")

        # 3. OPD PROCEDURES & PRESETS
        with sub_tab3:
            st.markdown("#### OPD Treatments & Presets")
           
            presets_df = pd.read_sql_query("SELECT * FROM preset_prescriptions", conn)
            if not presets_df.empty:
                st.markdown("##### **📦 OPD Medicine Presets (බෙහෙත් කට්ටල)**")
                col_p_sel, col_p_fee, col_p_btn = st.columns([2, 1.2, 1])
                with col_p_sel:
                    sel_preset_name = st.selectbox("Select Medicine Preset Pack:", presets_df['preset_name'].tolist())
                with col_p_fee:
                    opd_preset_doc_fee = st.number_input("OPD Doctor Fee (LKR):", value=350.0, step=50.0, key="preset_doc_fee")
                    add_doc_fee_preset = st.checkbox("Doctor Fee එකතු කරන්න", value=True, key="chk_preset_doc")
                with col_p_btn:
                    st.write("")
                    st.write("")
                    if st.button("➕ Add Preset to Cart", use_container_width=True):
                        p_row = presets_df[presets_df['preset_name'] == sel_preset_name].iloc[0]
                        items = eval(p_row['items_json'])
                        for it in items:
                            st.session_state.pos_cart.append(it)
                       
                        if add_doc_fee_preset and opd_preset_doc_fee > 0:
                            st.session_state.pos_cart.append({
                                'category': 'OPD',
                                'display_name': f"OPD Consultation Fee ({sel_preset_name})",
                                'qty': 1,
                                'unit_price': float(opd_preset_doc_fee),
                                'total_price': float(opd_preset_doc_fee),
                                'doctor_name': "OPD Doctor",
                                'doc_fee': float(opd_preset_doc_fee),
                                'center_profit': 0.0
                            })
                        st.success(f"Preset '{sel_preset_name}' Cart එකට එකතු විය!")
                        st.rerun()
           
            st.markdown("---")

            procs_df = pd.read_sql_query("SELECT * FROM opd_procedures", conn)
            if not procs_df.empty:
                selected_proc = st.selectbox("Select Procedure / Treatment:", procs_df['proc_name'].tolist())
                p_row = procs_df[procs_df['proc_name'] == selected_proc].iloc[0]
                default_d_fee = float(p_row['default_doc_fee'])
                default_c_fee = float(p_row['center_fee'])
            else:
                selected_proc = "General OPD Consultation"
                default_d_fee = 350.0
                default_c_fee = 150.0

            remove_doc_fee = st.checkbox("🚫 Doctor Fee එක එකතු කරන්න එපා (No Doctor Fee)", value=False)

            col_of1, col_of2 = st.columns(2)
            with col_of1:
                if remove_doc_fee:
                    opd_doc_fee = 0.0
                    st.info("Doctor Fee: LKR 0.00")
                else:
                    opd_doc_fee = st.number_input("Doctor Fee (LKR):", value=default_d_fee, step=50.0)
           
            with col_of2:
                opd_center_fee = st.number_input("Center Fee (LKR):", value=default_c_fee, step=50.0)
               
            tot_opd_fee = opd_doc_fee + opd_center_fee
            st.metric("Total Payable Amount", f"LKR {tot_opd_fee:.2f}")
               
            if st.button("➕ Add OPD Procedure to Cart", use_container_width=True):
                bill_display = "OPD Charges" if opd_doc_fee > 0 else f"OPD: {selected_proc}"
               
                st.session_state.pos_cart.append({
                    'category': 'OPD',
                    'display_name': bill_display,
                    'qty': 1,
                    'unit_price': float(tot_opd_fee),
                    'total_price': float(tot_opd_fee),
                    'doctor_name': "OPD Doctor",
                    'doc_fee': float(opd_doc_fee),
                    'center_profit': float(opd_center_fee)
                })
                st.success(f"Added {selected_proc} to Cart!")
                st.rerun()

        # 4. CHANNELING SELECTION
        with sub_tab4:
            docs_df = pd.read_sql_query("SELECT * FROM doctors", conn)
            if not docs_df.empty:
                doc_sel = st.selectbox("Select Channeling Doctor:", docs_df['doc_name'].tolist(), key="chan_doc_select")
                d_row = docs_df[docs_df['doc_name'] == doc_sel].iloc[0]
                tot_chan_fee = float(d_row['doc_fee']) + float(d_row['center_fee'])
                st.metric("Total Channeling Fee", f"LKR {tot_chan_fee:.2f}")
               
                if st.button("➕ Add Channeling to Cart", use_container_width=True):
                    st.session_state.pos_cart.append({
                        'category': 'Channeling',
                        'display_name': f"Channeling - {d_row['doc_name']}",
                        'qty': 1,
                        'unit_price': tot_chan_fee,
                        'total_price': tot_chan_fee,
                        'doctor_name': d_row['doc_name'],
                        'doc_fee': float(d_row['doc_fee']),
                        'center_profit': float(d_row['center_fee'])
                    })
                    st.success("Added Channeling to Cart!")
                    st.rerun()

        # 5. SCANNING SELECTION
        with sub_tab5:
            docs_df = pd.read_sql_query("SELECT * FROM doctors", conn)
            if not docs_df.empty:
                scan_doc_sel = st.selectbox("Select Scanning Doctor:", docs_df['doc_name'].tolist(), key="scan_doc_select")
                sd_row = docs_df[docs_df['doc_name'] == scan_doc_sel].iloc[0]
               
                doc_scan_fee = float(sd_row.get('doc_scan_fee', 0.0))
                center_scan_fee = float(sd_row.get('center_scan_fee', 0.0))
                tot_scan_fee = doc_scan_fee + center_scan_fee
               
                col_s1, col_s2, col_s3 = st.columns(3)
                col_s1.metric("Doctor Scan Fee", f"LKR {doc_scan_fee:.2f}")
                col_s2.metric("Center Fee", f"LKR {center_scan_fee:.2f}")
                col_s3.metric("Total Scan Fee", f"LKR {tot_scan_fee:.2f}")
               
                if st.button("➕ Add Scanning to Cart", use_container_width=True):
                    st.session_state.pos_cart.append({
                        'category': 'Scanning',
                        'display_name': f"Scanning - {sd_row['doc_name']}",
                        'qty': 1,
                        'unit_price': tot_scan_fee,
                        'total_price': tot_scan_fee,
                        'doctor_name': sd_row['doc_name'],
                        'doc_fee': doc_scan_fee,
                        'center_profit': center_scan_fee
                    })
                    st.success("Added Scanning to Cart!")
                    st.rerun()

# ---------------------------------------------------------
# TAB 2: MASTER SETTINGS (ADMIN & SUPERVISOR ONLY)
# ---------------------------------------------------------
if "📦 Master Settings & Inventory" in available_tabs:
    tab_index = available_tabs.index("📦 Master Settings & Inventory")
    with tabs[tab_index]:
        st.subheader("📦 Master Settings & Inventory Management")
        st_tab1, st_tab2, st_tab3, st_tab4, st_tab5 = st.tabs([
            "💊 Pharmacy Stock", "🧪 Lab Tests", "👨‍⚕️ Doctor Profiles", "🩺 OPD Procedures", "📦 OPD Medicine Presets"
        ])
       
        # 1. PHARMACY MASTER
        with st_tab1:
            st.markdown("#### **Pharmacy Stock Management**")
            inv_full_df = pd.read_sql_query("SELECT * FROM inventory", conn)
            show_table(inv_full_df, use_container_width=True)
           
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                with st.expander("➕ Add New Stock / Medicine", expanded=True):
                    with st.form("add_inv_form"):
                        supplier = st.text_input("Supplier Name:")
                        item_name = st.text_input("Medicine Generic Name:")
                        brand_name = st.text_input("Brand Name:")
                        category = st.selectbox("Category:", ["Tablet", "Syrup", "Injection", "Ointment", "Other"])
                        dosage = st.text_input("Dosage:")
                        cost_p = st.number_input("Cost Price (LKR):", min_value=0.0, step=10.0)
                        unit_p = st.number_input("Unit Selling Price (LKR):", min_value=0.0, step=10.0)
                        stock_qty = st.number_input("Stock Quantity:", min_value=1, step=1)
                        expiry = st.date_input("Expiry Date:")
                        reorder = st.number_input("Reorder Level:", min_value=1, value=10)
                        batch = st.text_input("Batch No:")
                        barcode = st.text_input("Barcode:")
                       
                        if st.form_submit_button("Save Medicine Item"):
                            margin = ((unit_p - cost_p) / unit_p * 100) if unit_p > 0 else 0
                            c.execute("""INSERT INTO inventory (supplier_name, item_name, brand_name, category, dosage, cost_price, unit_price, profit_margin, stock_qty, expiry_date, reorder_level, batch_no, barcode)
                                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                                      (supplier, item_name, brand_name, category, dosage, cost_p, unit_p, margin, stock_qty, str(expiry), reorder, batch, barcode))
                            conn.commit()
                            st.success("Item Saved!")
                            st.rerun()

            with col_m2:
                with st.expander("✏️ Edit / Delete Medicine Item"):
                    if not inv_full_df.empty:
                        item_to_mod = st.selectbox("Select Item to Modify/Delete:", inv_full_df['item_name'].tolist())
                        selected_item_row = inv_full_df[inv_full_df['item_name'] == item_to_mod].iloc[0]
                        item_id = int(selected_item_row['id'])
                       
                        edit_brand = st.text_input("Brand Name:", value=str(selected_item_row.get('brand_name', '')), key="e_brand")
                        edit_cost = st.number_input("Cost Price:", value=float(selected_item_row['cost_price']), key="e_cost")
                        edit_unit = st.number_input("Selling Price:", value=float(selected_item_row['unit_price']), key="e_unit")
                        edit_stock = st.number_input("Stock Qty:", value=int(selected_item_row['stock_qty']), key="e_stock")
                       
                        col_act1, col_act2 = st.columns(2)
                        with col_act1:
                            if st.button("Update Item"):
                                c.execute("UPDATE inventory SET brand_name=?, cost_price=?, unit_price=?, stock_qty=? WHERE id=?", (edit_brand, edit_cost, edit_unit, edit_stock, item_id))
                                conn.commit()
                                st.success("Item Updated Successfully!")
                                st.rerun()
                        with col_act2:
                            if user_role == "Admin":
                                if st.button("🗑️ Delete Item", type="primary"):
                                    c.execute("DELETE FROM inventory WHERE id=?", (item_id,))
                                    conn.commit()
                                    st.warning("Item Deleted!")
                                    st.rerun()
                            else:
                                st.caption("🔒 Deletion allowed for Admin only.")

        # 2. LAB MASTER
        with st_tab2:
            st.markdown("#### **Lab Tests Management**")
            labs_all_df = pd.read_sql_query("SELECT * FROM lab_tests", conn)
            show_table(labs_all_df, use_container_width=True)
           
            col_l1, col_l2 = st.columns(2)
            with col_l1:
                with st.expander("➕ Add New Lab Test"):
                    with st.form("add_lab_form"):
                        t_name = st.text_input("Test Name:")
                        p_fee = st.number_input("Patient Fee (LKR):", value=1000.0)
                        l_cost = st.number_input("Lab Cost Payable (LKR):", value=600.0)
                        c_comm = st.number_input("Center Commission (LKR):", value=400.0)
                        if st.form_submit_button("Save Lab Test"):
                            c.execute("INSERT INTO lab_tests (test_name, patient_fee, lab_cost, center_commission) VALUES (?, ?, ?, ?)",
                                      (t_name, p_fee, l_cost, c_comm))
                            conn.commit()
                            st.success("Lab Test Added!")
                            st.rerun()
            with col_l2:
                with st.expander("✏️ Edit / Delete Lab Test"):
                    if not labs_all_df.empty:
                        lab_to_mod = st.selectbox("Select Test to Modify/Delete:", labs_all_df['test_name'].tolist())
                        l_row = labs_all_df[labs_all_df['test_name'] == lab_to_mod].iloc[0]
                        l_id = int(l_row['id'])
                       
                        edit_p_fee = st.number_input("Patient Fee:", value=float(l_row['patient_fee']), key="el_pfee")
                        edit_l_cost = st.number_input("Lab Cost:", value=float(l_row['lab_cost']), key="el_lcost")
                        edit_c_comm = st.number_input("Center Comm:", value=float(l_row['center_commission']), key="el_ccomm")
                       
                        col_la1, col_la2 = st.columns(2)
                        with col_la1:
                            if st.button("Update Lab Test"):
                                c.execute("UPDATE lab_tests SET patient_fee=?, lab_cost=?, center_commission=? WHERE id=?", (edit_p_fee, edit_l_cost, edit_c_comm, l_id))
                                conn.commit()
                                st.success("Lab Test Updated!")
                                st.rerun()
                        with col_la2:
                            if user_role == "Admin":
                                if st.button("🗑️ Delete Lab Test", type="primary"):
                                    c.execute("DELETE FROM lab_tests WHERE id=?", (l_id,))
                                    conn.commit()
                                    st.warning("Lab Test Deleted!")
                                    st.rerun()

        # 3. DOCTOR MASTER
        with st_tab3:
            st.markdown("#### **Doctor Profiles Management**")
            docs_all_df = pd.read_sql_query("SELECT * FROM doctors", conn)
            show_table(docs_all_df, use_container_width=True)
           
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                with st.expander("➕ Add Doctor Profile"):
                    with st.form("add_doc_form"):
                        d_name = st.text_input("Doctor Name:")
                        d_desig = st.text_input("Designation:")
                        d_fee = st.number_input("Channeling Doc Fee (LKR):", value=2000.0)
                        c_fee = st.number_input("Channeling Center Fee (LKR):", value=500.0)
                        d_scan = st.number_input("Scan Doc Fee (LKR):", value=1500.0)
                        c_scan = st.number_input("Scan Center Fee (LKR):", value=500.0)
                       
                        if st.form_submit_button("Save Doctor Profile"):
                            c.execute("INSERT INTO doctors (doc_name, designation, doc_fee, center_fee, doc_scan_fee, center_scan_fee) VALUES (?, ?, ?, ?, ?, ?)",
                                      (d_name, d_desig, d_fee, c_fee, d_scan, c_scan))
                            conn.commit()
                            st.success("Doctor Saved!")
                            st.rerun()

            with col_d2:
                with st.expander("✏️ Edit / Delete Doctor Profile"):
                    if not docs_all_df.empty:
                        doc_to_mod = st.selectbox("Select Doctor:", docs_all_df['doc_name'].tolist())
                        doc_row = docs_all_df[docs_all_df['doc_name'] == doc_to_mod].iloc[0]
                        doc_id = int(doc_row['id'])
                       
                        e_d_fee = st.number_input("Channeling Doc Fee:", value=float(doc_row['doc_fee']), key="ed_fee")
                        e_c_fee = st.number_input("Channeling Center Fee:", value=float(doc_row['center_fee']), key="ec_fee")
                        e_s_doc = st.number_input("Scan Doc Fee:", value=float(doc_row.get('doc_scan_fee', 0)), key="es_doc")
                        e_s_center = st.number_input("Scan Center Fee:", value=float(doc_row.get('center_scan_fee', 0)), key="es_cen")
                       
                        col_da1, col_da2 = st.columns(2)
                        with col_da1:
                            if st.button("Update Doctor Profile"):
                                c.execute("UPDATE doctors SET doc_fee=?, center_fee=?, doc_scan_fee=?, center_scan_fee=? WHERE id=?",
                                          (e_d_fee, e_c_fee, e_s_doc, e_s_center, doc_id))
                                conn.commit()
                                st.success("Doctor Profile Updated!")
                                st.rerun()
                        with col_da2:
                            if user_role == "Admin":
                                if st.button("🗑️ Delete Doctor", type="primary"):
                                    c.execute("DELETE FROM doctors WHERE id=?", (doc_id,))
                                    conn.commit()
                                    st.warning("Doctor Deleted!")
                                    st.rerun()

        # 4. OPD PROCEDURES MASTER
        with st_tab4:
            st.markdown("#### **OPD Procedures Management**")
            opd_proc_all = pd.read_sql_query("SELECT * FROM opd_procedures", conn)
            show_table(opd_proc_all, use_container_width=True)
           
            col_op1, col_op2 = st.columns(2)
            with col_op1:
                with st.expander("➕ Add New OPD Procedure"):
                    with st.form("add_opd_proc_form"):
                        p_name = st.text_input("Procedure Name:")
                        p_doc_fee = st.number_input("Default Doctor Fee (LKR):", value=300.0)
                        p_center_fee = st.number_input("Center Fee (LKR):", value=200.0)
                       
                        if st.form_submit_button("Save Procedure"):
                            c.execute("INSERT INTO opd_procedures (proc_name, default_doc_fee, center_fee) VALUES (?, ?, ?)",
                                      (p_name, p_doc_fee, p_center_fee))
                            conn.commit()
                            st.success("Procedure added successfully!")
                            st.rerun()

            with col_op2:
                with st.expander("✏️ Edit / Delete OPD Procedure"):
                    if not opd_proc_all.empty:
                        proc_to_mod = st.selectbox("Select Procedure:", opd_proc_all['proc_name'].tolist())
                        proc_row = opd_proc_all[opd_proc_all['proc_name'] == proc_to_mod].iloc[0]
                        proc_id = int(proc_row['id'])
                       
                        ep_doc = st.number_input("Doctor Fee:", value=float(proc_row['default_doc_fee']), key="ep_doc")
                        ep_center = st.number_input("Center Fee:", value=float(proc_row['center_fee']), key="ep_cen")
                       
                        col_pa1, col_pa2 = st.columns(2)
                        with col_pa1:
                            if st.button("Update Procedure"):
                                c.execute("UPDATE opd_procedures SET default_doc_fee=?, center_fee=? WHERE id=?", (ep_doc, ep_center, proc_id))
                                conn.commit()
                                st.success("Procedure Updated!")
                                st.rerun()
                        with col_pa2:
                            if user_role == "Admin":
                                if st.button("🗑️ Delete Procedure", type="primary"):
                                    c.execute("DELETE FROM opd_procedures WHERE id=?", (proc_id,))
                                    conn.commit()
                                    st.warning("Procedure Deleted!")
                                    st.rerun()

        # 5. PRESET PRESCRIPTIONS MASTER
        with st_tab5:
            st.markdown("#### **Manage OPD Medicine Presets**")
            all_presets_df = pd.read_sql_query("SELECT * FROM preset_prescriptions", conn)
            show_table(all_presets_df[['id', 'preset_name']], use_container_width=True)
           
            col_pr1, col_pr2 = st.columns(2)
            with col_pr1:
                with st.expander("➕ Add New Medicine Preset", expanded=True):
                    inv_df_preset = pd.read_sql_query("SELECT * FROM inventory", conn)
                    if not inv_df_preset.empty:
                        inv_df_preset['p_label'] = inv_df_preset['item_name'] + " (" + inv_df_preset['brand_name'] + ")"
                        preset_title = st.text_input("Preset Name:", key="new_preset_title")
                        selected_med_labels = st.multiselect("Select Medicines for Preset:", inv_df_preset['p_label'].tolist())
                       
                        if st.button("💾 Save Medicine Preset") and preset_title and selected_med_labels:
                            items_to_save = []
                            for med_lbl in selected_med_labels:
                                m_row = inv_df_preset[inv_df_preset['p_label'] == med_lbl].iloc[0]
                                items_to_save.append({
                                    'category': 'Pharmacy',
                                    'id': int(m_row['id']),
                                    'display_name': f"{m_row['item_name']} ({m_row['brand_name']})",
                                    'qty': 1,
                                    'unit_price': float(m_row['unit_price']),
                                    'total_price': float(m_row['unit_price']),
                                    'cost_price': float(m_row['cost_price'])
                                })
                           
                            c.execute("INSERT INTO preset_prescriptions (preset_name, items_json) VALUES (?, ?)", (preset_title, str(items_to_save)))
                            conn.commit()
                            st.success(f"Preset '{preset_title}' Saved!")
                            st.rerun()

            with col_pr2:
                with st.expander("🗑️ Delete Preset"):
                    if not all_presets_df.empty:
                        del_p_name = st.selectbox("Select Preset to Delete:", all_presets_df['preset_name'].tolist())
                        if user_role == "Admin":
                            if st.button("🗑️ Delete Selected Preset", type="primary"):
                                c.execute("DELETE FROM preset_prescriptions WHERE preset_name=?", (del_p_name,))
                                conn.commit()
                                st.warning(f"Preset '{del_p_name}' Deleted!")
                                st.rerun()

# ---------------------------------------------------------
# TAB 3: REPORTS & ACCOUNTS (WITH ONE-CLICK CLOUD SYNC)
# ---------------------------------------------------------
rep_tab_index = available_tabs.index("📊 Reports & Accounts")
with tabs[rep_tab_index]:
    st.subheader("📊 Reports & Inventory Tracking")
    
    # ONE-CLICK MANUAL CLOUD SYNC BUTTON
    col_sync1, col_sync2 = st.columns([1, 2])
    with col_sync1:
        if st.button("🔄 Sync All Local Data to Cloud", type="primary", use_container_width=True):
            try:
                local_sales = pd.read_sql_query("SELECT * FROM sales_history", conn)
                if not local_sales.empty and supabase:
                    success_count = 0
                    for _, row in local_sales.iterrows():
                        data_dict = {
                            'prescription_no': str(row['prescription_no']),
                            'bill_type': str(row['bill_type']),
                            'doctor_name': str(row['doctor_name']),
                            'bill_details': str(row['bill_details']),
                            'total_amount': float(row['total_amount']),
                            'doc_fee': float(row['doc_fee']),
                            'lab_cost': float(row['lab_cost']),
                            'center_profit': float(row['center_profit']),
                            'cost_price': float(row['cost_price']),
                            'date': str(row['date']),
                            'status': str(row['status'])
                        }
                        try:
                            supabase.table("sales_history").insert(data_dict).execute()
                            success_count += 1
                        except:
                            pass
                    st.success(f"✅ ගනුදෙනු {success_count} ක් Cloud එකට සාර්ථකව Sync විය!")
                    st.rerun()
                else:
                    st.info("Sync කිරීමට ගනුදෙනු නොමැත හෝ Cloud Connection නොමැත.")
            except Exception as e:
                st.error(f"Sync Error: {e}")

    sales_full_df = pd.DataFrame()
    if supabase:
        try:
            res = supabase.table("sales_history").select("*").execute()
            if res.data:
                sales_full_df = pd.DataFrame(res.data)
                sales_full_df = sales_full_df.sort_values(by="id", ascending=False)
        except Exception:
            pass

    if sales_full_df.empty:
        sales_full_df = pd.read_sql_query("SELECT * FROM sales_history ORDER BY id DESC", conn)
   
    main_rep_tab1, main_rep_tab2 = st.tabs(["💰 Financial Reports (ගිණුම් වාර්තා)", "⚠️ Expiry & Re-Order Tracking"])
   
    with main_rep_tab1:
        rep_period = st.radio("තෝරන්න (Select Time Period):", ["Daily (දිනපතා)", "Weekly (සතිපතා)", "Monthly (මාසිකව)"], horizontal=True)
       
        if not sales_full_df.empty:
            sales_full_df['date_dt'] = pd.to_datetime(sales_full_df['date'])
            now = datetime.now()
           
            if "Daily" in rep_period:
                sel_d = st.date_input("Select Date:", now.date())
                filtered_df = sales_full_df[sales_full_df['date_dt'].dt.date == sel_d]
            elif "Weekly" in rep_period:
                start_w = now - timedelta(days=7)
                filtered_df = sales_full_df[sales_full_df['date_dt'] >= start_w]
            else:
                filtered_df = sales_full_df[(sales_full_df['date_dt'].dt.month == now.month) & (sales_full_df['date_dt'].dt.year == now.year)]
               
            r_tab_summary, r_tab_sections, r_tab_all = st.tabs(["🌐 Grand Total Summary", "🏢 Section-Wise Breakdown", "🧾 Transactions & Refund / Re-Print"])
           
            # 1. GRAND TOTAL SUMMARY
            with r_tab_summary:
                active_sales = filtered_df[filtered_df['status'] == 'COMPLETED']
                st.markdown(f"### **🌐 Active Grand Total Summary ({rep_period})**")
               
                tot_revenue = active_sales['total_amount'].sum() if not active_sales.empty else 0.0
                tot_doc_pay = active_sales['doc_fee'].sum() if not active_sales.empty else 0.0
                tot_lab_cost = active_sales['lab_cost'].sum() if not active_sales.empty else 0.0
                tot_pharma_cost = active_sales['cost_price'].sum() if not active_sales.empty else 0.0
                tot_center_net_profit = active_sales['center_profit'].sum() if not active_sales.empty else 0.0
               
                col_g1, col_g2, col_g3 = st.columns(3)
                col_g1.metric("💰 Total Gross Revenue", f"LKR {tot_revenue:.2f}")
                col_g2.metric("💸 Direct Costs (Docs/Lab/Pharma)", f"LKR {(tot_doc_pay + tot_lab_cost + tot_pharma_cost):.2f}")
                col_g3.metric("📈 Center Net Profit", f"LKR {tot_center_net_profit:.2f}")
               
                st.markdown("---")
                if not active_sales.empty:
                    dept_summary = active_sales.groupby('bill_type').agg(
                        Total_Revenue=('total_amount', 'sum'),
                        Doctor_Payable=('doc_fee', 'sum'),
                        Lab_Cost=('lab_cost', 'sum'),
                        Medicine_Cost=('cost_price', 'sum'),
                        Center_Profit=('center_profit', 'sum')
                    ).reset_index()
                    show_table(dept_summary, use_container_width=True)

            # 2. SECTION-WISE BREAKDOWN
            with r_tab_sections:
                st.markdown(f"### **🏢 Detailed Section-Wise Breakdown ({rep_period})**")
                active_sales = filtered_df[filtered_df['status'] == 'COMPLETED']
               
                sec_lab, sec_pharma, sec_opd, sec_chan, sec_scan = st.tabs([
                    "🧪 Laboratory", "💊 Pharmacy Profit", "🩺 OPD Income", "👨‍⚕️ Channeling Doc Fees", "🖥️ Scanning Report"
                ])
               
                with sec_lab:
                    lab_sales = active_sales[active_sales['bill_type'] == 'Laboratory']
                    show_table(lab_sales[['date', 'prescription_no', 'bill_details', 'total_amount', 'lab_cost', 'center_profit']], use_container_width=True)
                    st.markdown("---")
                    col_l_t1, col_l_t2, col_l_t3 = st.columns(3)
                    col_l_t1.metric("💵 Lab Total Revenue", f"LKR {lab_sales['total_amount'].sum():.2f}")
                    col_l_t2.metric("🧪 Lab Payable Cost", f"LKR {lab_sales['lab_cost'].sum():.2f}")
                    col_l_t3.metric("📈 Center Profit", f"LKR {lab_sales['center_profit'].sum():.2f}")

                with sec_pharma:
                    pharma_sales = active_sales[active_sales['bill_type'] == 'Pharmacy']
                    show_table(pharma_sales[['date', 'prescription_no', 'bill_details', 'total_amount', 'cost_price', 'center_profit']], use_container_width=True)
                    st.markdown("---")
                    col_p_t1, col_p_t2, col_p_t3 = st.columns(3)
                    col_p_t1.metric("💵 Total Pharmacy Sales", f"LKR {pharma_sales['total_amount'].sum():.2f}")
                    col_p_t2.metric("📦 Total Medicine Cost", f"LKR {pharma_sales['cost_price'].sum():.2f}")
                    col_p_t3.metric("📈 Pharmacy Net Profit", f"LKR {pharma_sales['center_profit'].sum():.2f}")

                with sec_opd:
                    opd_sales = active_sales[active_sales['bill_type'] == 'OPD']
                    show_table(opd_sales[['date', 'prescription_no', 'bill_details', 'doc_fee', 'center_profit', 'total_amount']], use_container_width=True)
                    st.markdown("---")
                    col_o_t1, col_o_t2, col_o_t3 = st.columns(3)
                    col_o_t1.metric("💵 Total OPD Revenue", f"LKR {opd_sales['total_amount'].sum():.2f}")
                    col_o_t2.metric("👨‍⚕️ Doctor Fees Total", f"LKR {opd_sales['doc_fee'].sum():.2f}")
                    col_o_t3.metric("📈 Center Net Income", f"LKR {opd_sales['center_profit'].sum():.2f}")

                with sec_chan:
                    chan_sales = active_sales[active_sales['bill_type'] == 'Channeling']
                    show_table(chan_sales[['date', 'prescription_no', 'doctor_name', 'doc_fee', 'center_profit', 'total_amount']], use_container_width=True)
                    st.markdown("---")
                    col_c_t1, col_c_t2, col_c_t3 = st.columns(3)
                    col_c_t1.metric("💵 Total Channeling Revenue", f"LKR {chan_sales['total_amount'].sum():.2f}")
                    col_c_t2.metric("👨‍⚕️ Doctor Payable Total", f"LKR {chan_sales['doc_fee'].sum():.2f}")
                    col_c_t3.metric("📈 Center Profit Total", f"LKR {chan_sales['center_profit'].sum():.2f}")

                with sec_scan:
                    scan_sales = active_sales[active_sales['bill_type'] == 'Scanning']
                    show_table(scan_sales[['date', 'prescription_no', 'doctor_name', 'doc_fee', 'center_profit', 'total_amount']], use_container_width=True)
                    st.markdown("---")
                    col_s_t1, col_s_t2, col_s_t3 = st.columns(3)
                    col_s_t1.metric("💵 Total Scanning Revenue", f"LKR {scan_sales['total_amount'].sum():.2f}")
                    col_s_t2.metric("👨‍⚕️ Scanning Doctor Fees", f"LKR {scan_sales['doc_fee'].sum():.2f}")
                    col_s_t3.metric("📈 Center Profit Total", f"LKR {scan_sales['center_profit'].sum():.2f}")

            # 3. TRANSACTIONS & REFUND/REPRINT
            with r_tab_all:
                st.markdown("#### **All Sales, Re-Print Bill & Refund Management**")
                if not filtered_df.empty:
                    show_table(filtered_df[['id', 'date', 'prescription_no', 'bill_type', 'bill_details', 'total_amount', 'status']], use_container_width=True)
                   
                    st.markdown("---")
                    col_act_left, col_act_right = st.columns(2)
                   
                    with col_act_left:
                        st.markdown("##### **🖨️ Re-Print Previous Bill**")
                        reprint_id = st.number_input("Enter Sale ID to Re-Print:", min_value=1, step=1, key="reprint_id_input")
                        if st.button("🖨️ Re-Print Bill", type="primary"):
                            rp_row = sales_full_df[sales_full_df['id'] == reprint_id]
                            if not rp_row.empty:
                                r_data = rp_row.iloc[0]
                                rp_details = str(r_data['bill_details'])
                                if '|' in rp_details:
                                    rp_details = rp_details.split('|')[1]
                                   
                                reprint_html = f"""
                                <div style="text-align: center;">
                                    <b style="font-size: 8pt;">DIGHASRI CHANNEL CENTER</b><br>
                                    <span>[RE-PRINT RECEIPT]</span><br>
                                    <small style="font-size: 6.5pt;">{r_data['date']}</small>
                                </div>
                                <hr style="border: 1px dashed #000;">
                                <div style="text-align: center;">Ref No : {r_data['prescription_no']}</div>
                                <div style="text-align: center;">Type   : {r_data['bill_type']}</div>
                                <hr style="border: 1px dashed #000;">
                                <div style="text-align: center;">{rp_details}</div>
                                <hr style="border: 1px dashed #000;">
                                <div style="text-align: center;"><b>TOTAL : LKR {r_data['total_amount']:.2f}</b></div>
                                <hr style="border: 1px dashed #000;">
                                <div style="text-align: center;"><small style="font-size: 6.5pt;">Thank You Come Again!</small></div>
                                """
                                trigger_instant_print(reprint_html, f"reprint_{reprint_id}")
                                st.success(f"Receipt ID {reprint_id} Sent to Printer!")

                    with col_act_right:
                        st.markdown("##### **❌ Cancel & Refund Transaction**")
                        cancel_id = st.number_input("Enter Sale ID to Cancel / Void:", min_value=1, step=1, key="cancel_id_input")
                        if st.button("❌ Void & Refund Transaction"):
                            if user_role in ["Admin", "Supervisor"]:
                                s_row = sales_full_df[sales_full_df['id'] == cancel_id]
                                if not s_row.empty:
                                    curr_status = s_row.iloc[0]['status']
                                    if curr_status == 'CANCELLED':
                                        st.warning("මෙම ගනුදෙනුව මීට පෙර අවලංගු කර ඇත!")
                                    else:
                                        b_type = s_row.iloc[0]['bill_type']
                                        b_det = str(s_row.iloc[0]['bill_details'])
                                       
                                        if b_type == 'Pharmacy' and '|' in b_det:
                                            try:
                                                item_id_str = b_det.split('|')[0]
                                                qty_str = b_det.split('x')[1].strip()
                                                c.execute("UPDATE inventory SET stock_qty = stock_qty + ? WHERE id = ?", (int(qty_str), int(item_id_str)))
                                            except:
                                                pass
                                               
                                        c.execute("UPDATE sales_history SET status='CANCELLED', total_amount=0.0, doc_fee=0.0, lab_cost=0.0, center_profit=0.0, cost_price=0.0 WHERE id=?", (cancel_id,))
                                        conn.commit()
                                        st.success(f"Transaction ID {cancel_id} Cancelled!")
                                        st.rerun()
                            else:
                                st.error("🔒 අවලංගු කිරීම් Admin හෝ Supervisor ට පමණක් සිදුකල හැක.")

    with main_rep_tab2:
        st.markdown("### **⚠️ Inventory Risk Reports**")
        inv_rep_df = pd.read_sql_query("SELECT * FROM inventory", conn)
        if not inv_rep_df.empty:
            inv_rep_df['expiry_dt'] = pd.to_datetime(inv_rep_df['expiry_date'])
            today = pd.to_datetime(datetime.now().date())
            three_months = today + pd.DateOffset(months=3)
           
            col_exp1, col_exp2 = st.columns(2)
            with col_exp1:
                st.markdown("#### **📦 Re-Order Needed Items**")
                reorder_df = inv_rep_df[inv_rep_df['stock_qty'] <= inv_rep_df['reorder_level']]
                show_table(reorder_df[['supplier_name', 'item_name', 'brand_name', 'stock_qty', 'reorder_level']], use_container_width=True)
                   
            with col_exp2:
                st.markdown("#### **⏰ Expired or Expiring Soon**")
                expiring_df = inv_rep_df[inv_rep_df['expiry_dt'] <= three_months]
                show_table(expiring_df[['item_name', 'brand_name', 'batch_no', 'stock_qty', 'expiry_date']], use_container_width=True)

# ---------------------------------------------------------
# TAB 4: USER MANAGEMENT (ADMIN ONLY)
# ---------------------------------------------------------
if "⚙️ User Management" in available_tabs:
    user_tab_index = available_tabs.index("⚙️ User Management")
    with tabs[user_tab_index]:
        st.subheader("⚙️ User Management & Passwords (Admin Only)")
       
        users_df = pd.read_sql_query("SELECT username, role FROM users", conn)
        show_table(users_df, use_container_width=True)
       
        col_u1, col_u2 = st.columns(2)
        with col_u1:
            with st.expander("➕ Add New User", expanded=True):
                with st.form("add_user_form"):
                    new_u = st.text_input("Username:")
                    new_p = st.text_input("Password:", type="password")
                    new_r = st.selectbox("Role:", ["Admin", "Supervisor", "Cashier"])
                    if st.form_submit_button("Create User"):
                        try:
                            c.execute("INSERT INTO users VALUES (?, ?, ?)", (new_u, new_p, new_r))
                            conn.commit()
                            st.success(f"User '{new_u}' successfully created!")
                            st.rerun()
                        except:
                            st.error("මෙම Username එක මීට පෙර භාවිතා කර ඇත.")

        with col_u2:
            with st.expander("🔑 Reset Password / Delete User"):
                sel_u = st.selectbox("Select User:", users_df['username'].tolist())
                reset_p = st.text_input("New Password:", type="password", key="reset_p_input")
               
                col_ua1, col_ua2 = st.columns(2)
                with col_ua1:
                    if st.button("Update Password"):
                        c.execute("UPDATE users SET password=? WHERE username=?", (reset_p, sel_u))
                        conn.commit()
                        st.success(f"Password updated for {sel_u}!")
                with col_ua2:
                    if st.button("🗑️ Delete User", type="primary"):
                        if sel_u != "admin":
                            c.execute("DELETE FROM users WHERE username=?", (sel_u,))
                            conn.commit()
                            st.warning(f"User {sel_u} deleted!")
                            st.rerun()
                        else:
                            st.error("Admin user ව Delete කිරීමට නොහැකිය.")
