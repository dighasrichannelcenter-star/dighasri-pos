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

# Local Database Connection
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

conn.commit()

# Initialize Session States
if 'pos_cart' not in st.session_state:
    st.session_state.pos_cart = []
if 'print_html' not in st.session_state:
    st.session_state.print_html = None
if 'user' not in st.session_state:
    st.session_state.user = None

def show_table(df, **kwargs):
    if not df.empty:
        df_copy = df.copy()
        df_copy.index = range(1, len(df_copy) + 1)
        st.dataframe(df_copy, **kwargs)
    else:
        st.dataframe(df, **kwargs)

# --- INSTANT PRINT SCRIPT ---
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
        **Default Passwords:**
        * **Admin:** `admin` / `admin123`
        * **Supervisor:** `supervisor` / `super123`
        * **Cashier:** `cashier` / `cashier123`
        """)
    st.stop()

# ---------------------------------------------------------
# MAIN INTERFACE
# ---------------------------------------------------------
st.sidebar.title(f"👤 User: {st.session_state.user['username']}")
st.sidebar.markdown(f"**Role:** `{st.session_state.user['role']}`")
if st.sidebar.button("🚪 Logout", use_container_width=True):
    st.session_state.user = None
    st.session_state.pos_cart = []
    st.rerun()

st.title("🏥 Dighasri Channel Center POS System")

user_role = st.session_state.user['role']

if user_role == "Admin":
    available_tabs = ["🛒 POS Billing", "📦 Master Settings & Inventory", "📊 Reports & Accounts", "⚙️ User Management"]
elif user_role == "Supervisor":
    available_tabs = ["🛒 POS Billing", "📦 Master Settings & Inventory", "📊 Reports & Accounts"]
else:
    available_tabs = ["🛒 POS Billing", "📊 Reports & Accounts"]

tabs = st.tabs(available_tabs)

# ---------------------------------------------------------
# TAB 1: POS BILLING
# ---------------------------------------------------------
with tabs[0]:
    col_left, col_right = st.columns([1.2, 1.8])
   
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
                paid_amt = st.number_input("Paid Amount (LKR):", min_value=0.0, value=float(subtotal), step=50.0)
            with col_p2:
                balance_amt = max(0.0, paid_amt - subtotal)
                st.metric("Balance", f"LKR {balance_amt:.2f}")
               
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
                       
                        dt_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
                    <div style="text-align: center;">{bill_items_html}</div>
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
            st.info("Cart එක හිස්ව පවතී.")

    with col_right:
        st.subheader("⚡ Quick Category Select")
        sub_tab1, sub_tab2, sub_tab3, sub_tab4, sub_tab5 = st.tabs(["🧪 Laboratory", "💊 Pharmacy", "🩺 OPD Procedures", "👨‍⚕️ Channeling", "🖥️ Scanning"])
       
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

        with sub_tab3:
            st.markdown("#### OPD Treatments & Presets")
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

            remove_doc_fee = st.checkbox("🚫 No Doctor Fee", value=False)
            col_of1, col_of2 = st.columns(2)
            with col_of1:
                opd_doc_fee = 0.0 if remove_doc_fee else st.number_input("Doctor Fee (LKR):", value=default_d_fee, step=50.0)
            with col_of2:
                opd_center_fee = st.number_input("Center Fee (LKR):", value=default_c_fee, step=50.0)
               
            tot_opd_fee = opd_doc_fee + opd_center_fee
            st.metric("Total Payable Amount", f"LKR {tot_opd_fee:.2f}")
               
            if st.button("➕ Add OPD Procedure to Cart", use_container_width=True):
                st.session_state.pos_cart.append({
                    'category': 'OPD',
                    'display_name': f"OPD: {selected_proc}",
                    'qty': 1,
                    'unit_price': float(tot_opd_fee),
                    'total_price': float(tot_opd_fee),
                    'doctor_name': "OPD Doctor",
                    'doc_fee': float(opd_doc_fee),
                    'center_profit': float(opd_center_fee)
                })
                st.success("Added to Cart!")
                st.rerun()

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

        with sub_tab5:
            docs_df = pd.read_sql_query("SELECT * FROM doctors", conn)
            if not docs_df.empty:
                scan_doc_sel = st.selectbox("Select Scanning Doctor:", docs_df['doc_name'].tolist(), key="scan_doc_select")
                sd_row = docs_df[docs_df['doc_name'] == scan_doc_sel].iloc[0]
                doc_scan_fee = float(sd_row.get('doc_scan_fee', 0.0))
                center_scan_fee = float(sd_row.get('center_scan_fee', 0.0))
                tot_scan_fee = doc_scan_fee + center_scan_fee
               
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
# TAB 2: MASTER SETTINGS
# ---------------------------------------------------------
if "📦 Master Settings & Inventory" in available_tabs:
    tab_index = available_tabs.index("📦 Master Settings & Inventory")
    with tabs[tab_index]:
        st.subheader("📦 Master Settings & Inventory Management")
        m_tab1, m_tab2, m_tab3, m_tab4 = st.tabs(["💊 Inventory", "🧪 Lab Tests", "🩺 OPD Procedures", "👨‍⚕️ Doctors"])
        
        with m_tab1:
            st.markdown("#### Manage Inventory Items")
            inv_all = pd.read_sql_query("SELECT * FROM inventory", conn)
            show_table(inv_all, use_container_width=True)

        with m_tab2:
            st.markdown("#### Manage Lab Tests")
            labs_all = pd.read_sql_query("SELECT * FROM lab_tests", conn)
            show_table(labs_all, use_container_width=True)

        with m_tab3:
            st.markdown("#### Manage OPD Procedures")
            opd_all = pd.read_sql_query("SELECT * FROM opd_procedures", conn)
            show_table(opd_all, use_container_width=True)

        with m_tab4:
            st.markdown("#### Manage Doctors")
            docs_all = pd.read_sql_query("SELECT * FROM doctors", conn)
            show_table(docs_all, use_container_width=True)

# ---------------------------------------------------------
# TAB 3: REPORTS & ACCOUNTS
# ---------------------------------------------------------
rep_tab_index = available_tabs.index("📊 Reports & Accounts")
with tabs[rep_tab_index]:
    st.subheader("📊 Reports & Inventory Tracking")
    
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
                            'status': str(row.get('status', 'COMPLETED'))
                        }
                        try:
                            supabase.table("sales_history").insert(data_dict).execute()
                            success_count += 1
                        except:
                            pass
                    st.success(f"✅ ගනුදෙනු {success_count} ක් Cloud එකට සාර්ථකව Sync විය!")
                else:
                    st.info("Sync කිරීමට ගනුදෙනු නොමැත හෝ Cloud Connection නොමැත.")
            except Exception as e:
                st.error(f"Sync Error: {e}")

    # FETCH FROM LOCAL DATABASE FIRST TO PRESERVE ALL PAST DATA ACCURATELY
    sales_full_df = pd.read_sql_query("SELECT * FROM sales_history ORDER BY id DESC", conn)
    if sales_full_df.empty and supabase:
        try:
            res = supabase.table("sales_history").select("*").order("id", desc=True).execute()
            if res.data:
                sales_full_df = pd.DataFrame(res.data)
        except Exception:
            pass

    main_rep_tab1, main_rep_tab2 = st.tabs(["💰 Financial Reports (ගිණුම් වාර්තා)", "⚠️ Expiry & Re-Order Tracking"])
   
    with main_rep_tab1:
        # DATE FILTER SECTION
        st.markdown("### 📅 Date Filter Options (දිනයන් අනුව වාර්තා තෝරන්න)")
        col_f1, col_f2, col_f3 = st.columns([1.5, 1.5, 1.5])
        
        with col_f1:
            time_filter = st.selectbox(
                "තෝරන්න (Range):", 
                ["සියල්ල (All Time)", "අද දින (Today)", "මෙම සතියේ (This Week)", "මෙම මාසයේ (This Month)", "දින සිට දින දක්වා (Custom Date)"]
            )

        start_date, end_date = None, None
        if time_filter == "දින සිට දින දක්වා (Custom Date)":
            with col_f2:
                start_date = st.date_input("ආරම්භක දිනය (From Date):", value=datetime.now().date())
            with col_f3:
                end_date = st.date_input("අවසාන දිනය (To Date):", value=datetime.now().date())

        # APPLY DATE FILTER SAFELY WITHOUT DROPPING OLD RECORDS
        sales_df = sales_full_df.copy()
        if not sales_df.empty and 'date' in sales_df.columns:
            sales_df['parsed_date'] = pd.to_datetime(sales_df['date'], errors='coerce')
            today = datetime.now().date()

            if time_filter == "අද දින (Today)":
                sales_df = sales_df[sales_df['parsed_date'].dt.date == today]
            elif time_filter == "මෙම සතියේ (This Week)":
                start_of_week = today - timedelta(days=today.weekday())
                sales_df = sales_df[sales_df['parsed_date'].dt.date >= start_of_week]
            elif time_filter == "මෙම මාසයේ (This Month)":
                sales_df = sales_df[(sales_df['parsed_date'].dt.month == today.month) & (sales_df['parsed_date'].dt.year == today.year)]
            elif time_filter == "දින සිට දින දක්වා (Custom Date)" and start_date and end_date:
                sales_df = sales_df[(sales_df['parsed_date'].dt.date >= start_date) & (sales_df['parsed_date'].dt.date <= end_date)]

        r_tab_summary, r_tab_sections, r_tab_all = st.tabs(["🌐 Grand Total Summary", "🏢 Section-Wise Breakdown", "🧾 All Transactions History"])
       
        # 1. GRAND TOTAL SUMMARY
        with r_tab_summary:
            st.markdown(f"### **🌐 Grand Total Summary ({time_filter})**")
            
            # INCLUDE ALL PAST COMPLETED / UNSTATED RECORDS
            if not sales_df.empty and 'status' in sales_df.columns:
                active_sales = sales_df[sales_df['status'].fillna('COMPLETED') != 'CANCELLED']
            else:
                active_sales = sales_df
           
            tot_revenue = active_sales['total_amount'].sum() if not active_sales.empty and 'total_amount' in active_sales.columns else 0.0
            tot_doc_pay = active_sales['doc_fee'].sum() if not active_sales.empty and 'doc_fee' in active_sales.columns else 0.0
            tot_lab_cost = active_sales['lab_cost'].sum() if not active_sales.empty and 'lab_cost' in active_sales.columns else 0.0
            tot_pharma_cost = active_sales['cost_price'].sum() if not active_sales.empty and 'cost_price' in active_sales.columns else 0.0
            tot_center_net_profit = active_sales['center_profit'].sum() if not active_sales.empty and 'center_profit' in active_sales.columns else 0.0
           
            col_g1, col_g2, col_g3 = st.columns(3)
            col_g1.metric("💰 Total Gross Revenue", f"LKR {tot_revenue:.2f}")
            col_g2.metric("💸 Direct Costs (Docs/Lab/Pharma)", f"LKR {(tot_doc_pay + tot_lab_cost + tot_pharma_cost):.2f}")
            col_g3.metric("📈 Center Net Profit", f"LKR {tot_center_net_profit:.2f}")
           
            st.markdown("---")
            if not active_sales.empty and 'bill_type' in active_sales.columns:
                dept_summary = active_sales.groupby('bill_type').agg(
                    Total_Revenue=('total_amount', 'sum'),
                    Doctor_Payable=('doc_fee', 'sum'),
                    Lab_Cost=('lab_cost', 'sum'),
                    Center_Profit=('center_profit', 'sum')
                ).reset_index()
                show_table(dept_summary, use_container_width=True)

        # 2. SECTION-WISE BREAKDOWN
        with r_tab_sections:
            st.markdown(f"### **🏢 Detailed Section-Wise Breakdown ({time_filter})**")
            if not sales_df.empty and 'status' in sales_df.columns:
                active_sales = sales_df[sales_df['status'].fillna('COMPLETED') != 'CANCELLED']
            else:
                active_sales = sales_df
           
            sec_lab, sec_pharma, sec_opd, sec_chan, sec_scan = st.tabs([
                "🧪 Laboratory", "💊 Pharmacy Profit", "🩺 OPD Income", "👨‍⚕️ Channeling Doc Fees", "🖥️ Scanning Report"
            ])
           
            def add_total_row(df_sec):
                if df_sec.empty:
                    return df_sec
                
                df_calc = df_sec.copy()
                total_row = {}
                
                for col in df_calc.columns:
                    if col in ['total_amount', 'doc_fee', 'lab_cost', 'center_profit', 'cost_price', 'discount']:
                        total_row[col] = df_calc[col].sum()
                    elif col in ['id', 'prescription_no', 'bill_type', 'doctor_name', 'status', 'parsed_date']:
                        total_row[col] = ""
                    elif col == 'bill_details':
                        total_row[col] = "TOTAL"
                    else:
                        total_row[col] = ""
                
                total_df = pd.DataFrame([total_row])
                return pd.concat([df_calc, total_df], ignore_index=True)

            with sec_lab:
                lab_sales = active_sales[active_sales['bill_type'] == 'Laboratory'] if not active_sales.empty and 'bill_type' in active_sales.columns else pd.DataFrame()
                show_table(add_total_row(lab_sales), use_container_width=True)

            with sec_pharma:
                pharma_sales = active_sales[active_sales['bill_type'] == 'Pharmacy'] if not active_sales.empty and 'bill_type' in active_sales.columns else pd.DataFrame()
                show_table(add_total_row(pharma_sales), use_container_width=True)

            with sec_opd:
                opd_sales = active_sales[active_sales['bill_type'].isin(['OPD', 'OPD Consultation', 'OPD Procedure'])] if not active_sales.empty and 'bill_type' in active_sales.columns else pd.DataFrame()
                show_table(add_total_row(opd_sales), use_container_width=True)

            with sec_chan:
                chan_sales = active_sales[active_sales['bill_type'] == 'Channeling'] if not active_sales.empty and 'bill_type' in active_sales.columns else pd.DataFrame()
                show_table(add_total_row(chan_sales), use_container_width=True)

            with sec_scan:
                scan_sales = active_sales[active_sales['bill_type'] == 'Scanning'] if not active_sales.empty and 'bill_type' in active_sales.columns else pd.DataFrame()
                show_table(add_total_row(scan_sales), use_container_width=True)

        # 3. TRANSACTIONS
        with r_tab_all:
            st.markdown(f"#### **All Transactions History ({time_filter})**")
            if not sales_df.empty:
                display_cols = [col for col in sales_df.columns if col != 'parsed_date']
                show_table(sales_df[display_cols], use_container_width=True)
            else:
                st.info("දත්ත නොමැත.")

    with main_rep_tab2:
        st.markdown("### **⚠️ Inventory Risk Reports**")
        inv_rep_df = pd.read_sql_query("SELECT * FROM inventory", conn)
        if not inv_rep_df.empty:
            inv_rep_df['expiry_dt'] = pd.to_datetime(inv_rep_df['expiry_date'], errors='coerce')
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
# TAB 4: USER MANAGEMENT
# ---------------------------------------------------------
if "⚙️ User Management" in available_tabs:
    user_tab_index = available_tabs.index("⚙️ User Management")
    with tabs[user_tab_index]:
        st.subheader("⚙️️ User Management & Passwords (Admin Only)")
        users_df = pd.read_sql_query("SELECT username, role FROM users", conn)
        show_table(users_df, use_container_width=True)
