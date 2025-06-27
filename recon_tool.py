import streamlit as st
import pandas as pd
from fuzzywuzzy import fuzz
import openai # Note: openai is imported but not used in the reconciliation logic
import os
from dotenv import load_dotenv
import uuid
import io

# --- Configuration and Initial Setup ---

# Load environment variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Page config
st.set_page_config(page_title="CROWN Reconciliation Tool", layout="wide", initial_sidebar_state="expanded")

# Inject custom CSS (remains the same as your original)
st.markdown("""
    <style>
        /* Global Styles */
        body, .main {
            background: #f4f7fb;
            font-family: 'Segoe UI', sans-serif;
            color: #2c3e50;
        }

        /* Streamlit specific adjustments for the main content area */
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
            padding-left: 1rem;
            padding-right: 1rem;
        }

        /* Section Header */
        .section-header {
            font-size: 32px;
            font-weight: bold;
            color: #1e3050;
            margin-top: 20px;
            margin-bottom: 20px;
            text-align: center;
        }

        /* Title */
        .title {
            font-size: 36px;
            font-weight: 700;
            color: #2c3e50;
            margin-top: 20px;
            margin-bottom: 30px;
            text-align: center;
        }

        /* Upload Section Styling */
        .upload-section {
            display: flex;
            justify-content: center;
            align-items: flex-start;
            gap: 40px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }

        /* Style for the Streamlit file uploader itself */
        .stFileUploader {
            width: 100%;
        }
        .stFileUploader > div {
            border: 2px dashed #aeb8c4;
            border-radius: 12px;
            padding: 20px;
            background-color: #ffffff;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
            transition: box-shadow 0.2s ease-in-out;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
        }
        .stFileUploader > div:hover {
            box-shadow: 0 6px 16px rgba(0, 0, 0, 0.1);
        }
        .stFileUploader label {
            font-size: 18px;
            font-weight: 600;
            color: #34495e;
            margin-bottom: 10px;
        }
        .stFileUploader button {
            background-color: #1c2d5a;
            color: white;
            border-radius: 8px;
            padding: 8px 15px;
            font-weight: 600;
            border: none;
        }


        /* Card Grid for Totals */
        .card-grid {
            display: flex;
            justify-content: center;
            align-items: flex-start;
            gap: 40px;
            flex-wrap: wrap;
            margin-top: 20px;
            margin-bottom: 40px;
        }

        /* Stat Cards */
        .card-box {
            background: linear-gradient(145deg, #0a1d4e, #10256b);
            border-radius: 20px;
            box-shadow: 0 12px 24px rgba(0, 0, 0, 0.15);
            padding: 24px;
            width: 250px;
            color: white;
            transition: transform 0.2s ease-in-out;
            border: none;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
        }
        .card-box:hover {
            transform: translateY(-5px);
            box-shadow: 0 16px 36px rgba(0, 0, 0, 0.2);
        }
        .card-title {
            font-size: 20px;
            font-weight: 700;
            margin-bottom: 6px;
        }
        .card-sub {
            color: #e0e0e0;
            font-size: 14px;
            margin-bottom: 8px;
        }
        .card-total {
            font-size: 24px;
            font-weight: 700;
            color: #00e676;
            word-break: break-all;
        }

        /* Crown brand color highlights */
        .highlight-gold {
            color: #f0c419;
        }
        .highlight-blue {
            color: #1c2d5a;
        }

        /* Custom section divider */
        hr {
            border: none;
            height: 1px;
            background: linear-gradient(to right, transparent, #aaa, transparent);
            margin: 40px 0;
        }

        /* Table styling for dataframes */
        .stDataFrame {
            border: 1px solid #e0e6f1;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
        }
        .stDataFrame table {
            width: 100%;
            border-collapse: collapse;
        }
        .stDataFrame th {
            background-color: #e8edf4;
            color: #34495e;
            font-weight: 600;
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #dcdcdc;
        }
        .stDataFrame td {
            padding: 10px 15px;
            border-bottom: 1px solid #f0f0f0;
        }
        .stDataFrame tbody tr:last-child td {
            border-bottom: none;
        }
        .stDataFrame tbody tr:hover {
            background-color: #f8fbfd;
        }

        /* Expander styling for unmatched items */
        .stExpander {
            border: 1px solid #e0e6f1;
            border-radius: 10px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.03);
            margin-bottom: 20px;
            background-color: #ffffff;
        }
        .stExpander > div > div > button {
            font-weight: 600 !important;
            font-size: 18px !important;
            color: #34495e !important;
            padding: 15px 20px !important;
        }
        .stExpander .streamlit_expanderContent {
            padding-top: 10px;
            padding-bottom: 10px;
        }
        .total-amount-unmatched {
            font-size: 1.1em;
            font-weight: 700;
            color: #444;
            margin-top: 10px;
            text-align: right;
            padding-right: 15px;
            padding-bottom: 10px;
        }

        /* Info/Success messages inside expanders */
        .stAlert {
            margin: 10px 15px;
            border-radius: 8px;
        }

        /* Download button styling */
        .stDownloadButton button {
            background-color: #1c2d5a;
            color: white;
            padding: 10px 20px;
            border-radius: 8px;
            border: none;
            font-weight: 600;
            transition: background-color 0.2s ease-in-out;
        }
        .stDownloadButton button:hover {
            background-color: #2c4273;
        }
    </style>
""", unsafe_allow_html=True)


# --- Session State Initialization ---
if 'unmatched_bank_display' not in st.session_state:
    st.session_state.unmatched_bank_display = pd.DataFrame()
if 'unmatched_ledger_display' not in st.session_state:
    st.session_state.unmatched_ledger_display = pd.DataFrame()
if 'initial_unmatched_computed' not in st.session_state:
    st.session_state.initial_unmatched_computed = False
if 'bank_file_name' not in st.session_state:
    st.session_state.bank_file_name = None
if 'ledger_file_name' not in st.session_state:
    st.session_state.ledger_file_name = None
if 'bank_df_full' not in st.session_state:
    st.session_state.bank_df_full = pd.DataFrame()
if 'ledger_df_full' not in st.session_state:
    st.session_state.ledger_df_full = pd.DataFrame()
if 'selection_reset_counter' not in st.session_state: # Used to force reset of checkbox selections
    st.session_state.selection_reset_counter = 0

# --- Helper Functions ---

@st.cache_data(ttl=3600)
def find_closest_column(df_columns_list, target_name, threshold=80):
    cleaned_cols = {col: col.strip().lower() for col in df_columns_list}
    if not cleaned_cols:
        return None
    best_match = max(cleaned_cols.items(), key=lambda x: fuzz.ratio(x[1], target_name.lower()))
    if fuzz.ratio(best_match[1], target_name.lower()) >= threshold:
        return best_match[0]
    return None

@st.cache_data(ttl=3600)
def load_and_preprocess_file(file_content, file_name):
    try:
        if file_name.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(file_content))
        else:
            df = pd.read_excel(io.BytesIO(file_content))
    except Exception as e:
        st.error(f"Error reading file '{file_name}': {e}. Please ensure it's a valid CSV or Excel file.")
        st.stop()

    df.columns = [col.strip() for col in df.columns]

    date_col = find_closest_column(tuple(df.columns), "Date")
    name_col = find_closest_column(tuple(df.columns), "Name")
    memo_col = find_closest_column(tuple(df.columns), "Memo")
    amount_col = find_closest_column(tuple(df.columns), "Amount")
    debit_col = find_closest_column(tuple(df.columns), "Debit")
    credit_col = find_closest_column(tuple(df.columns), "Credit")

    missing_cols = []
    if not date_col: missing_cols.append("Date")
    if not name_col: missing_cols.append("Name")
    if not memo_col: missing_cols.append("Memo")

    if missing_cols:
        st.error(f"Missing one or more required columns: {', '.join(missing_cols)}. Please check your file headers.")
        st.stop()

    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=[date_col])

    if not amount_col:
        if credit_col and debit_col:
            df["debit"] = pd.to_numeric(df[debit_col], errors="coerce").fillna(0)
            df["credit"] = pd.to_numeric(df[credit_col], errors="coerce").fillna(0)
            df["amount"] = df["credit"] - df["debit"]
        else:
            st.error("Missing 'Amount' column and no usable 'Credit'/'Debit' columns to calculate it. Please ensure your file contains transaction amounts.")
            st.stop()
    else:
        df["amount"] = pd.to_numeric(df[amount_col], errors="coerce")

    df = df.dropna(subset=["amount"])
    df = df[df["amount"] != 0]

    df.rename(columns={date_col: "date", name_col: "name", memo_col: "memo"}, inplace=True)
    df["row_id"] = [str(uuid.uuid4()) for _ in range(len(df))]
    df["name_lower"] = df["name"].astype(str).str.lower().str.strip()

    return df[["row_id", "date", "name", "memo", "amount", "name_lower"]]

@st.cache_data(ttl=3600)
def perform_automatic_reconciliation(bank_df, ledger_df):
    bank_df_copy = bank_df.copy()
    ledger_df_copy = ledger_df.copy()

    bank_df_copy["matched"] = False
    ledger_df_copy["matched"] = False

    bank_df_copy['amount_rounded'] = bank_df_copy['amount'].round(2)
    ledger_df_copy['amount_rounded'] = ledger_df_copy['amount'].round(2)

    bank_df_copy['date_str'] = bank_df_copy['date'].dt.strftime('%Y-%m-%d')
    ledger_df_copy['date_str'] = ledger_df_copy['date'].dt.strftime('%Y-%m-%d')

    merged_exact = pd.merge(
        bank_df_copy,
        ledger_df_copy,
        on=['date_str', 'amount_rounded'],
        suffixes=('_bank', '_ledger'),
        how='inner'
    )

    fuzzy_match_threshold = 80
    matched_bank_ids = set()
    matched_ledger_ids = set()

    for idx, row in merged_exact.iterrows():
        bank_id = row['row_id_bank']
        ledger_id = row['row_id_ledger']

        if bank_id in matched_bank_ids or ledger_id in matched_ledger_ids:
            continue

        bank_name = row['name_lower_bank']
        ledger_name = row['name_lower_ledger']

        if fuzz.partial_ratio(bank_name, ledger_name) > fuzzy_match_threshold:
            matched_bank_ids.add(bank_id)
            matched_ledger_ids.add(ledger_id)

    bank_df_copy.loc[bank_df_copy['row_id'].isin(matched_bank_ids), 'matched'] = True
    ledger_df_copy.loc[ledger_df_copy['row_id'].isin(matched_ledger_ids), 'matched'] = True

    unmatched_bank = bank_df_copy[~bank_df_copy["matched"]].drop(columns=["matched", "amount_rounded", "name_lower", "date_str"])
    unmatched_ledger = ledger_df_copy[~ledger_df_copy["matched"]].drop(columns=["matched", "amount_rounded", "name_lower", "date_str"])

    return unmatched_bank, unmatched_ledger

# Function to handle manual reconciliation (expects lists of row_ids)
def perform_manual_reconciliation(selected_bank_row_ids, selected_ledger_row_ids):
    bank_df_display = st.session_state.unmatched_bank_display
    ledger_df_display = st.session_state.unmatched_ledger_display

    if not selected_bank_row_ids or not selected_ledger_row_ids:
        st.warning("Please select at least one item from both Bank and Ledger to reconcile.")
        return

    bank_items = bank_df_display[bank_df_display['row_id'].isin(selected_bank_row_ids)]
    ledger_items = ledger_df_display[ledger_df_display['row_id'].isin(selected_ledger_row_ids)]

    if bank_items.empty or ledger_items.empty:
        st.error("One or more selected items were not found in the current list. They might have been reconciled or removed.")
        return

    bank_sum_amount = round(bank_items['amount'].sum(), 2)
    ledger_sum_amount = round(ledger_items['amount'].sum(), 2)

    if bank_sum_amount == ledger_sum_amount:
        st.session_state.unmatched_bank_display = st.session_state.unmatched_bank_display[
            ~st.session_state.unmatched_bank_display['row_id'].isin(selected_bank_row_ids)
        ].reset_index(drop=True)
        st.session_state.unmatched_ledger_display = st.session_state.unmatched_ledger_display[
            ~st.session_state.unmatched_ledger_display['row_id'].isin(selected_ledger_row_ids)
        ].reset_index(drop=True)

        st.success(
            f"Successfully reconciled {len(selected_bank_row_ids)} bank item(s) (Total: ${bank_sum_amount:,.2f}) "
            f"with {len(selected_ledger_row_ids)} ledger item(s) (Total: ${ledger_sum_amount:,.2f})! "
            f"Remaining unmatched: Bank ({len(st.session_state.unmatched_bank_display)}), "
            f"Ledger ({len(st.session_state.unmatched_ledger_display)})"
        )
        st.session_state.selection_reset_counter += 1
        st.rerun()
    else:
        st.error(
            f"Selected groups have different total amounts: Bank Total ${bank_sum_amount:,.2f} vs Ledger Total ${ledger_sum_amount:,.2f}. "
            "Sum of amounts must match for manual group reconciliation."
        )


# --- Streamlit UI Layout ---

st.markdown('<div class="title">Reconciliation Dashboard</div>', unsafe_allow_html=True)

# --- Upload Section ---
col_upload_left_pad, col_upload_content_area, col_upload_right_pad = st.columns([1, 2, 1])

with col_upload_content_area:
    st.markdown('<div class="upload-section">', unsafe_allow_html=True)
    col_bank_uploader, col_ledger_uploader = st.columns(2)
    with col_bank_uploader:
        bank_file = st.file_uploader("📤 Upload Bank Statement (CSV or Excel)", type=["csv", "xlsx"], key="bank_file_uploader")
    with col_ledger_uploader:
        ledger_file = st.file_uploader("📤 Upload Ledger File (CSV or Excel)", type=["csv", "xlsx"], key="ledger_file_uploader")
    st.markdown('</div>', unsafe_allow_html=True)


# --- Conditional Data Processing and Display ---
if bank_file and ledger_file:
    current_bank_file_name = bank_file.name
    current_ledger_file_name = ledger_file.name

    if not st.session_state.initial_unmatched_computed or \
       st.session_state.bank_file_name != current_bank_file_name or \
       st.session_state.ledger_file_name != current_ledger_file_name:

        with st.spinner("Processing files and performing initial reconciliation..."):
            bank_df_loaded = load_and_preprocess_file(bank_file.getvalue(), current_bank_file_name)
            ledger_df_loaded = load_and_preprocess_file(ledger_file.getvalue(), current_ledger_file_name)

            computed_unmatched_bank, computed_unmatched_ledger = perform_automatic_reconciliation(bank_df_loaded, ledger_df_loaded)

            st.session_state.unmatched_bank_display = computed_unmatched_bank
            st.session_state.unmatched_ledger_display = computed_unmatched_ledger
            st.session_state.initial_unmatched_computed = True
            st.session_state.bank_file_name = current_bank_file_name
            st.session_state.ledger_file_name = current_ledger_file_name
            st.session_state.bank_df_full = bank_df_loaded
            st.session_state.ledger_df_full = ledger_df_loaded
            st.session_state.selection_reset_counter += 1

    # --- Card Grid (Total Boxes) ---
    col_card_left_pad, col_card_content_area, col_card_right_pad = st.columns([1, 2, 1])
    with col_card_content_area:
        st.markdown('<div class="card-grid">', unsafe_allow_html=True)
        card_col1, card_col2, card_col3 = st.columns(3)
        bank_total = st.session_state.bank_df_full['amount'].sum() if not st.session_state.bank_df_full.empty else 0.00
        ledger_total = st.session_state.ledger_df_full['amount'].sum() if not st.session_state.ledger_df_full.empty else 0.00
        difference = bank_total - ledger_total
        with card_col1:
            st.markdown(f"""<div class="card-box"><div class="card-title">🏦 Bank File</div><div class="card-sub">{current_bank_file_name}</div><div class="card-total">${bank_total:,.2f}</div></div>""", unsafe_allow_html=True)
        with card_col2:
            st.markdown(f"""<div class="card-box"><div class="card-title">📒 Ledger File</div><div class="card-sub">{current_ledger_file_name}</div><div class="card-total">${ledger_total:,.2f}</div></div>""", unsafe_allow_html=True)
        with card_col3:
            st.markdown(f"""<div class="card-box"><div class="card-title">🔍 Difference</div><div class="card-sub">Bank - Ledger</div><div class="card-total">${difference:,.2f}</div></div>""", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # --- Unmatched Items Section (with st.checkbox for multi-selection) ---
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown('<h3 class="section-header">Unmatched Items Overview</h3>', unsafe_allow_html=True)

    with st.form(key="reconciliation_form"):
        col_unmatched_bank, col_unmatched_ledger = st.columns(2)

        bank_checkbox_keys_map = {} 
        ledger_checkbox_keys_map = {}

        with col_unmatched_bank:
            st.subheader("📌 Unmatched Bank Items")
            st.dataframe(
                st.session_state.unmatched_bank_display[['date', 'name', 'memo', 'amount']],
                use_container_width=True, hide_index=True,
                column_config={
                    "date": st.column_config.DateColumn("Date", format="YYYY-MM-DD"),
                    "amount": st.column_config.NumberColumn("Amount", format="$%.2f"),
                    "name": "Name", "memo": "Memo"
                }
            )
            st.markdown(f"<p class='total-amount-unmatched'><strong>Total:</strong> ${st.session_state.unmatched_bank_display['amount'].sum():,.2f}</p>", unsafe_allow_html=True)
            st.markdown("---")
            st.markdown("**Select Bank Transaction(s) for Manual Reconciliation:**")
            if not st.session_state.unmatched_bank_display.empty:
                for _, row in st.session_state.unmatched_bank_display.iterrows():
                    item_label = f"{row['date'].strftime('%Y-%m-%d')} | {row['name']} | ${row['amount']:.2f}"
                    row_id = row['row_id']
                    checkbox_key = f"bank_cb_{row_id}_{st.session_state.selection_reset_counter}"
                    st.checkbox(item_label, key=checkbox_key) 
                    bank_checkbox_keys_map[row_id] = checkbox_key
            else:
                st.caption("No bank items to select.")
        
        with col_unmatched_ledger:
            st.subheader("📌 Unmatched Ledger Items")
            st.dataframe(
                st.session_state.unmatched_ledger_display[['date', 'name', 'memo', 'amount']],
                use_container_width=True, hide_index=True,
                column_config={
                    "date": st.column_config.DateColumn("Date", format="YYYY-MM-DD"),
                    "amount": st.column_config.NumberColumn("Amount", format="$%.2f"),
                    "name": "Name", "memo": "Memo"
                }
            )
            st.markdown(f"<p class='total-amount-unmatched'><strong>Total:</strong> ${st.session_state.unmatched_ledger_display['amount'].sum():,.2f}</p>", unsafe_allow_html=True)
            st.markdown("---")
            st.markdown("**Select Ledger Transaction(s) for Manual Reconciliation:**")
            if not st.session_state.unmatched_ledger_display.empty:
                for _, row in st.session_state.unmatched_ledger_display.iterrows():
                    item_label = f"{row['date'].strftime('%Y-%m-%d')} | {row['name']} | ${row['amount']:.2f}"
                    row_id = row['row_id']
                    checkbox_key = f"ledger_cb_{row_id}_{st.session_state.selection_reset_counter}"
                    st.checkbox(item_label, key=checkbox_key)
                    ledger_checkbox_keys_map[row_id] = checkbox_key
            else:
                st.caption("No ledger items to select.")

        st.markdown("<br>", unsafe_allow_html=True)
        reconcile_col1, reconcile_col2, reconcile_col3 = st.columns([1,1,1])
        with reconcile_col2:
            submitted = st.form_submit_button("✨ Reconcile Selected Groups", use_container_width=True)

        if submitted:
            selected_bank_ids = []
            for row_id, cb_key in bank_checkbox_keys_map.items():
                if st.session_state.get(cb_key, False): # Use .get for safety
                    selected_bank_ids.append(row_id)
            
            selected_ledger_ids = []
            for row_id, cb_key in ledger_checkbox_keys_map.items():
                if st.session_state.get(cb_key, False): # Use .get for safety
                    selected_ledger_ids.append(row_id)
            
            perform_manual_reconciliation(selected_bank_ids, selected_ledger_ids)

    st.markdown("<hr>", unsafe_allow_html=True)

    # Prepare data for download
    csv_unmatched_data = []
    if not st.session_state.unmatched_bank_display.empty:
        csv_unmatched_data.append(st.session_state.unmatched_bank_display.assign(source="BANK"))
    if not st.session_state.unmatched_ledger_display.empty:
        csv_unmatched_data.append(st.session_state.unmatched_ledger_display.assign(source="LEDGER"))

    if csv_unmatched_data:
        csv_unmatched = pd.concat(csv_unmatched_data)
        columns_to_drop = ['row_id']
        if 'name_lower' in csv_unmatched.columns: columns_to_drop.append('name_lower')
        csv_unmatched = csv_unmatched.drop(columns=columns_to_drop, errors='ignore')
    else:
        csv_unmatched = pd.DataFrame()

    col_download_left, col_download_center, col_download_right = st.columns([1, 1, 1])
    with col_download_center:
        if not csv_unmatched.empty:
            csv_bytes = csv_unmatched.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="⬇️ Download All Unmatched Items (CSV)", data=csv_bytes,
                file_name="unmatched_reconciliation_summary.csv", mime="text/csv",
                help="Download a combined CSV file of all unmatched bank and ledger transactions."
            )
        elif st.session_state.initial_unmatched_computed:
            st.success("🎉 All items reconciled! No unmatched items to download. Great job!")

elif not bank_file and not ledger_file:
    st.info("⬆️ Please upload your Bank Statement and Ledger File above to begin reconciliation.")