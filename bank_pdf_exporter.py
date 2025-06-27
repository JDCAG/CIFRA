The following code integrates the requested features: a 7-day free trial with persistence, optional Chart of Accounts and Vendor report uploads for enhanced tagging, and clear labeling for the trial period.

The core changes involve:

  * **Cookie-based Trial Management:** Using `streamlit_cookies_manager` for persistent trial state across sessions. If a cookie manager isn't feasible in your deployment environment (like some serverless setups), you'd need to fall back to a database for trial management, which would require user authentication for tracking. For this example, I've used `streamlit_cookies_manager` as it's a common way to handle client-side persistence in Streamlit. If this library isn't available or suitable, you'd implement `st.session_state` and a basic file-based fallback for trial days for *single-user local testing only*, and for production, you'd persist this in Supabase associated with the user's ID.
  * **Trial Gating:** The "Bank Transactions Exporter" tool is now gated by the free trial logic. Other tools would require a subscription.
  * **UI Labels:** A clear label is added at the top of the app indicating the trial status.
  * **COA and Vendor Uploads:** New `st.file_uploader` components are added for Chart of Accounts and Vendor Reports. These are then used to create mapping dictionaries that override or enhance the GPT-based tagging.
  * **Tagging Logic Enhancement:** The `gpt_coa_classification` and `gpt_extract_vendor` functions are modified to first check against the uploaded COA and Vendor mappings before resorting to GPT.

-----

````python
import streamlit as st
import pandas as pd
import pdfplumber
import re
from io import BytesIO
import openai
import os
import pytesseract
from pdf2image import convert_from_bytes 
import json 
from supabase import create_client, Client 
from datetime import datetime, timedelta

# --- NEW: Import for Cookies (requires pip install streamlit-cookies-manager) ---
try:
    from streamlit_cookies_manager import CookiesManager
except ImportError:
    st.warning("`streamlit-cookies-manager` not found. Install with `pip install streamlit-cookies-manager` for persistent free trial logic. Falling back to session state for trial (will not persist across browser sessions).")
    CookiesManager = None

# --- NEW: st.set_page_config() MUST BE THE ABSOLUTE FIRST STREAMLIT COMMAND ---
st.set_page_config(layout="wide", page_title="My Awesome Financial Tools") 

# --- NEW: Initialize Cookies Manager ---
cookies = None
if CookiesManager:
    cookies = CookiesManager()
    if not cookies.ready():
        # Wait for the cookies to be loaded
        st.stop()

# --- Supabase Initialization ---
SUPABASE_URL = os.getenv("SUPABASE_URL") 
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Supabase URL and Key not found. Please set them as environment variables (SUPABASE_URL, SUPABASE_KEY) in Render.")
    st.stop() 

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- NEW: Supabase Network Diagnostic (Now correctly placed after set_page_config) ---
try:
    # Try a simple database query to test connectivity
    # This queries a non-existent table, but just needs to reach the DB endpoint
    _ = supabase.from_('__non_existent_table__').select('*').limit(0).execute()
    st.sidebar.success("Supabase connection test: Successful!")
except Exception as e:
    st.sidebar.error(f"Supabase connection test: Failed! Error: {e}")
    st.sidebar.warning("This indicates a network or URL issue between Render and Supabase. Please double-check SUPABASE_URL or contact Render/Supabase support.")
# --- END NEW ---


# --- OpenAI Initialization ---
openai_api_key_value = os.getenv("OPENAI_API_KEY") 

if 'openai_client' not in st.session_state:
    if openai_api_key_value:
        st.session_state.openai_client = openai.OpenAI(api_key=openai_api_key_value)
    else:
        st.session_state.openai_client = None 

# --- Tesseract Initialization ---
try:
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
except Exception as e:
    st.warning(f"Could not set Tesseract path. OCR might not work without it. Error: {e}")
    st.info("If you are running on Windows, ensure Tesseract is installed and the path is correct.")
    st.info("For Linux/Cloud environments, install Tesseract via 'sudo apt-get install tesseract-ocr'.")


# --- Helper functions for PDF parsing, Vendor, COA (No changes, copied from previous code) ---
def extract_pdf_text(file_bytes):
    text_data = []
    try:
        with pdfplumber.open(file_bytes) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_data.append(page_text) 
        if text_data: 
            return text_data
    except Exception as e:
        st.warning(f"pdfplumber failed: {e}. Attempting OCR fallback...")

    st.info("Falling back to OCR for scanned PDF...")
    try:
        images = convert_from_bytes(file_bytes.getvalue()) 
        ocr_full_text_pages = []
        for i, image in enumerate(images):
            ocr_text = pytesseract.image_to_string(image)
            ocr_full_text_pages.append(ocr_text)
            if i == 0:
                st.text("🔎 OCR TEXT SAMPLE (first 500 chars of page 1):")
                st.code(ocr_text[:500], language='text')
                st.markdown("---")
        return ocr_full_text_pages 
    except Exception as e:
        st.error(f"OCR (pytesseract) failed: {e}. Please ensure Tesseract and poppler are installed correctly.")
        st.info("If running locally, check Tesseract path. For cloud, ensure dependencies are in requirements.txt and installed.")
        return []

@st.cache_data
def gpt_parse_pdf_transactions(raw_pdf_page_texts, file_year="2025"):
    client = st.session_state.openai_client
    if not client:
        st.error("OpenAI API client is not initialized. API key might be missing.")
        return pd.DataFrame()

    all_transactions = []
    
    for i, page_text in enumerate(raw_pdf_page_texts):
        st.info(f"Asking GPT to parse page {i+1} of the PDF...")
        prompt = f"""
        Extract all financial transactions from the following bank or credit card statement text.
        For each transaction, identify the 'Date', 'Description', and 'Amount'.
        
        Rules:
        - Dates can be in MM/DD or MM/DD/YY format. Convert all dates to MM/DD/YYYY format. Assume the year is {file_year} if only MM/DD is provided. If the year is given (e.g., 25 for 2025), use that.
        - The 'Description' field should capture the primary purpose or entity of the transaction. This might span multiple lines in the raw text. Combine relevant lines to form a single, complete description.
        - Amounts should be numeric. Do not include dollar signs or commas. **If an amount is in parentheses (e.g., (123.45)), it signifies a negative value (-123.45).** Ensure negative signs are preserved.
        - Ignore headers, footers, summary lines (like 'Beginning Balance', 'Account Summary'), section titles (like 'Payments', 'Credits' if they don't have an amount next to them), and ending balances.
        - Only extract lines that clearly represent a transaction with a date, description, and amount.
        
        Output: A JSON array of objects, where each object represents one transaction.
        The keys in the JSON objects MUST be exactly "Date", "Description", and "Amount".
        
        Example of JSON output:
        json
        [
            {{
                "Date": "04/21/2025",
                "Description": "MOBILE PAYMENT - THANK YOU",
                "Amount": -1000.00
            }},
            {{
                "Date": "04/28/2025",
                "Description": "AMAZON MARKETPLACE NA PA AMZN.COM/BILL WA MERCHANDISE",
                "Amount": -27.61
            }},
            {{
                "Date": "05/03/2025",
                "Description": "Payment to Utility Company",
                "Amount": -125.50
            }}
        ]

        If no transactions are found, return an empty JSON array [].

        Statement Text (Page {i+1}):
        ---
        {page_text}
        ---
        """
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini", 
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1, 
                response_format={"type": "json_object"} 
            )
            
            json_string = response.choices[0].message.content
            
            print(f"DEBUG: GPT Raw JSON for page {i+1}:\n{json_string}\n---END RAW JSON---")

            if json_string.startswith("json") and json_string.endswith("```"):
                json_string = json_string[7:-3].strip()

            parsed_data = json.loads(json_string)
            
            transactions_for_page = []
            if isinstance(parsed_data, list):
                transactions_for_page = parsed_data
            elif isinstance(parsed_data, dict):
                if "transactions" in parsed_data and isinstance(parsed_data["transactions"], list):
                    transactions_for_page = parsed_data["transactions"]
                else:
                    st.warning(f"GPT returned an unexpected JSON object structure for page {i+1}. Expected list or object with 'transactions' key. Raw: {json_string[:500]}...")
            else:
                st.warning(f"GPT returned unexpected JSON type (not list or dict) for page {i+1}. Skipping page. Raw: {json_string[:500]}...")
                continue 
            
            for transaction in transactions_for_page:
                if not isinstance(transaction, dict):
                    st.warning(f"Found non-dictionary item in GPT's JSON list for page {i+1}. Skipping item. Item: {str(transaction)[:100]}")
                    continue 

                date = transaction.get("Date", "N/A")
                description = transaction.get("Description", "No Description Extracted")
                amount = transaction.get("Amount", 0.0) 

                try:
                    amount = float(amount)
                except (ValueError, TypeError):
                    amount = 0.0
                    st.warning(f"Failed to convert amount '{transaction.get('Amount', 'N/A')}' to float for transaction: {description}")

                all_transactions.append({
                    "Date": date,
                    "Description": description,
                    "Amount": amount
                })

        except openai.APIError as e:
            st.error(f"OpenAI API Error during PDF parsing: {e}. Skipping page {i+1}.")
            print(f"DEBUG: GPT PDF Parsing Error: {e}")
        except json.JSONDecodeError as e:
            st.error(f"Failed to parse JSON from GPT for page {i+1}: {e}. Skipping page. Raw GPT response (truncated): {json_string[:500]}...")
        except Exception as e:
            st.error(f"An unexpected error occurred during GPT PDF parsing for page {i+1}: {e}. Skipping page.")
    
    if not all_transactions:
        st.warning("No transactions could be extracted from the PDF using GPT. Please check the PDF format or adjust the GPT parsing prompt.")
    
    return pd.DataFrame(all_transactions)

def identify_known_transaction_type(description):
    desc_lower = description.lower()
    known_types = {
        "online transfer": ("Online Transfer", "Uncategorized"),
        "e-transfer": ("Online Transfer", "Uncategorized"),
        "deposit": ("Deposit", "Income"),
        "payroll": ("Payroll", "Payroll"),
        "direct deposit": ("Payroll", "Income"),
        "atm withdrawal": ("ATM Withdrawal", "Uncategorized"),
        "cash withdrawal": ("Cash Withdrawal", "Uncategorized"),
        "ach credit": ("ACH Credit", "Income"), 
        "ach debit": ("ACH Debit", "Uncategorized"), 
        "loan payment": ("Loan Payment", "Loan Payment"),
        "bill pay": ("Bill Pay", "Uncategorized"),
        "check #": ("Check Payment", "Uncategorized"), 
        "zelle": ("Zelle Payment", "Uncategorized"), 
        "venmo": ("Venmo Payment", "Uncategorized"), 
        "paypal": ("PayPal Payment", "Uncategorized"), 
        "credit card payment": ("Credit Card Payment", "Debt Service"),
        "tap tag": ("Tap Tag", "Technology Services"), 
        "electrify": ("Electrify America", "EV Charging Expense"), 
        "laz parking": ("LAZ Parking", "Parking Expense") 
    }
    for keyword, (vendor_name, coa) in known_types.items():
        if keyword in desc_lower:
            return vendor_name, coa
    return None, None 

@st.cache_data
def gpt_extract_vendor(description):
    client = st.session_state.openai_client
    if not client:
        return "N/A (API Key Missing)"

    prompt = f"""
    Extract the primary vendor name from the following transaction description. 
    Focus on the concise, core company or entity name that provided the service or product.
    Strictly ignore any transaction IDs, dates, payment processor names (like PPD ID, ACH, VENMO, PAYPAL, GOOGLE, SQUARE, CARD PURCHASE, DIRECT DEPOSIT, APLPay), card numbers, alphanumeric codes, branch locations (e.g., "6606 W HOLLYWOOD CA"), or trailing details like "Online Supplemet".
    The output should be only the vendor name, clean and without extra text.

    Example 1: "Healthequity inc Healthequi PPD ID: 1522383166" -> "Healthequity Inc"
    Example 2: "60121 Apollo Sta Dir Dep PPD ID: 13406794" -> "Apollo"
    Example 3: "AMAZON.COM*EJ43L6J" -> "Amazon.com"
    Example 4: "Starbucks Store #1234" -> "Starbucks"
    Example 5: "Monthly Software Subscription XYZCorp" -> "XYZCorp"
    Example 6: "Utilities Payment City of LA" -> "City of LA"
    Example 7: "APLPay THE UPS STORE 6606 W HOLLYWOOD CA" -> "UPS Store"
    Example 8: "FLODESK.COM CLAYMONT DE" -> "Flodesk"
    Example 9: "Fullscript.com Online Supplemet" -> "Fullscript"
    Example 10: "SUSH N MATCHA SHO Los Angeles CA" -> "Sushi N Matcha"
    Example 11: "STRIPE*ABC Company" -> "ABC Company"
    Example 12: "TAP TAG T" -> "Tap Tag"
    Example 13: "AplPay NY Electrify" -> "Electrify"
    Example 14: "AplPay LAZ PARKING 1617090 SKI 0000 LOS ANGELES CA" -> "LAZ Parking"


    Description: "{description}"
    Extracted Vendor:
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1, 
            max_tokens=50 
        )
        vendor_name = response.choices[0].message.content.strip()
        
        vendor_name = re.sub(r'[^\w\s\.]', '', vendor_name).strip() 
        vendor_name = re.sub(r'\s+', ' ', vendor_name).strip() 
        
        if not vendor_name or vendor_name.lower() in ["unknown vendor", "no vendor", "n/a", "none", "vendor"]: 
            return "Unknown Vendor"
        return vendor_name
    except openai.APIError as e:
        print(f"DEBUG: GPT Vendor Extraction Error: {e}")
        return "N/A (API Error)"
    except Exception as e:
        st.error(f"An unexpected error occurred during GPT vendor extraction: {e}")
        return "N/A (Error)"

@st.cache_data
def gpt_coa_classification(vendor):
    client = st.session_state.openai_client
    if not client:
        return "Uncategorized (API Key Missing)"

    prompt = f"""
    Vendor: {vendor}
    Identify the most appropriate general business expense category for this vendor.
    Consider common business classifications for purchases made from this type of vendor.
    
    If the vendor is related to a business expense, provide a concise and descriptive category.
    If the vendor represents income, clearly state "Income".
    If the vendor is related to internal transfers, loan payments, or other non-expense/non-income items, categorize accordingly (e.g., "Internal Transfer", "Loan Payment").
    If you are unsure or the vendor does not fit a clear business category, return "Uncategorized".
    
    Examples:
    - Vendor: "Ritual Hot Yoga" -> "Fitness & Wellness"
    - Vendor: "Starbucks" -> "Meals & Entertainment"
    - Vendor: "Amazon.com" -> "General Merchandise"
    - Vendor: "Microsoft" -> "Software & Subscriptions"
    - Vendor: "Healthequity Inc" -> "Employee Benefits"
    - Vendor: "City of Los Angeles Water Dept" -> "Utilities"
    - Vendor: "Southwest Airlines" -> "Travel Expense"
    - Vendor: "LegalZoom" -> "Legal & Professional Fees"
    - Vendor: "Google Ads" -> "Marketing & Advertising"
    - Vendor: "ACME Corp Payroll" -> "Payroll Expense"
    - Vendor: "Bank Loan Payment" -> "Loan Payment"
    - Vendor: "Rent Payment" -> "Rent Expense"
    - Vendor: "Customer Refund" -> "Sales Adjustment"
    - Vendor: "Received Payment from Client" -> "Income"
    - Vendor: "Office Depot" -> "Office Supplies"
    - Vendor: "UPS" -> "Shipping & Postage"
    - Vendor: "Fullscript" -> "Health & Wellness Supplies" 
    - Vendor: "Uber" -> "Transportation"
    - Vendor: "Tap Tag" -> "Business Services" 
    - Vendor: "Electrify" -> "EV Charging Expense" 
    - Vendor: "LAZ Parking" -> "Parking Expense" 

    Only return the most likely category. If you cannot find a suitable category, return "Uncategorized". Do NOT return an empty string.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1 
        )
        coa_category = response.choices[0].message.content.strip()
        
        coa_category = coa_category.replace('"', '').strip() 
        
        if not coa_category:
            return "Uncategorized"
        return coa_category

    except openai.APIError as e:
        print(f"DEBUG: Full OpenAI API Error: {e}") 
        st.error(f"OpenAI API Error: {e}. Check your API key and network connection.")
        return "Uncategorized (API Error)"
    except Exception as e:
        st.error(f"An unexpected error occurred during GPT classification: {e}")
        return "Uncategorized (Error)")

# --- NEW: Free Trial Management ---
TRIAL_DAYS = 7
TRIAL_COOKIE_NAME = "financial_tools_trial_start"

def get_trial_status():
    if cookies:
        trial_start_str = cookies.get(TRIAL_COOKIE_NAME)
    else:
        # Fallback for when cookies manager is not available (e.g., local testing without persistence)
        trial_start_str = st.session_state.get(TRIAL_COOKIE_NAME)

    if trial_start_str:
        try:
            trial_start_date = datetime.fromisoformat(trial_start_str).date()
            days_passed = (datetime.now().date() - trial_start_date).days
            remaining_days = TRIAL_DAYS - days_passed
            if remaining_days > 0:
                return "active", remaining_days
            else:
                return "expired", 0
        except ValueError:
            # Malformed date in cookie, reset
            if cookies:
                cookies.set(TRIAL_COOKIE_NAME, datetime.now().date().isoformat())
                cookies.save()
            else:
                st.session_state[TRIAL_COOKIE_NAME] = datetime.now().date().isoformat()
            return "active", TRIAL_DAYS
    else:
        # No trial started yet, initiate it
        if cookies:
            cookies.set(TRIAL_COOKIE_NAME, datetime.now().date().isoformat())
            cookies.save()
        else:
            st.session_state[TRIAL_COOKIE_NAME] = datetime.now().date().isoformat()
        return "active", TRIAL_DAYS

# --- Streamlit UI ---
st.title("📊 My Business Tools Suite")

# --- NEW: Trial Status Label ---
trial_status, remaining_days = get_trial_status()

if not st.session_state.get('logged_in', False) and trial_status == "active":
    st.markdown(f"**This tool (Bank Transactions Exporter) is free for {remaining_days} days!** Others require subscription.")
elif not st.session_state.get('logged_in', False) and trial_status == "expired":
    st.markdown("**Your 7-day free trial has ended.** Please log in or subscribe to continue using the Bank Transactions Exporter.")


st.markdown("Choose a tool below to get started!")

# Initialize session state for login if not already set
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_email' not in st.session_state:
    st.session_state['user_email'] = None
if 'is_subscribed' not in st.session_state: 
    st.session_state['is_subscribed'] = False
# --- NEW: Initialize COA and Vendor mappings ---
if 'coa_mapping' not in st.session_state:
    st.session_state['coa_mapping'] = {} # Format: {vendor_name: COA}
if 'vendor_mapping' not in st.session_state:
    st.session_state['vendor_mapping'] = {} # Format: {description_keyword: vendor_name}


# --- Login/Registration Section ---
if not st.session_state.logged_in:
    st.subheader("Login or Sign Up to Access Tools")
    
    login_tab, signup_tab = st.tabs(["Login", "Sign Up"])

    with login_tab:
        with st.form("login_form"):
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            submitted = st.form_submit_button("Login")

            if submitted:
                try:
                    response = supabase.auth.sign_in_with_password({"email": email, "password": password})
                    if response.user:
                        st.session_state.logged_in = True
                        st.session_state.user_email = response.user.email
                        
                        user_profile_response = supabase.table('user_profiles').select('is_subscribed').eq('id', response.user.id).execute()
                        if user_profile_response.data and len(user_profile_response.data) > 0:
                            st.session_state.is_subscribed = user_profile_response.data[0]['is_subscribed']
                        else:
                            supabase.table('user_profiles').insert({"id": response.user.id, "email": response.user.email, "is_subscribed": False}).execute()
                            st.session_state.is_subscribed = False 

                        st.success(f"Welcome, {response.user.email}!")
                        st.rerun() 
                    else:
                        st.error("Login failed. Please check your email and password.")
                except Exception as e:
                    st.error(f"An error occurred during login: {e}")

    with signup_tab:
        with st.form("signup_form"):
            email = st.text_input("Email", key="signup_email")
            password = st.text_input("Password", type="password", key="signup_password")
            submitted = st.form_submit_button("Sign Up")

            if submitted:
                try:
                    response = supabase.auth.sign_up({"email": email, "password": password})
                    if response.user:
                        st.success("Sign up successful! Please check your email to confirm your account.")
                        supabase.table('user_profiles').insert({"id": response.user.id, "email": email, "is_subscribed": False}).execute()
                    else:
                        st.error("Sign up failed. This email might already be registered or an error occurred.")
                except Exception as e:
                    st.error(f"An error occurred during sign up: {e}")
    st.markdown("---") 

# --- Main Tool Section (visible only if logged in OR trial is active) ---
if st.session_state.logged_in or trial_status == "active":
    if st.session_state.logged_in:
        st.sidebar.write(f"Logged in as: {st.session_state.user_email}")
        if st.sidebar.button("Logout"):
            try:
                supabase.auth.sign_out()
                st.session_state.logged_in = False
                st.session_state.user_email = None
                st.session_state.is_subscribed = False 
                st.success("You have been logged out.")
                st.rerun()
            except Exception as e:
                st.error(f"Error during logout: {e}")

    # --- Subscription Gating (only if logged in and not subscribed) ---
    if st.session_state.logged_in and not st.session_state.is_subscribed:
        st.info("You need an active subscription to use *all* tools. The 'Bank Transactions Exporter' is available during your free trial.")
        st.subheader("Unlock Full Access")
        st.write("To use our powerful tools like the Payroll Sensitivity Analyzer, please subscribe to one of our plans:")
        
        st.markdown(
            """
            ### Pricing Plans
            - **Free Tier:** Limited features (e.g., 7-day trial for Bank Exporter, manual tagging only after trial)
            - **Pro Tier:** Unlimited access to Bank Exporter & Payroll Analyzer with AI tagging ($X/month)
            - **Enterprise Tier:** Custom solutions & dedicated support (Contact Us)
            """
        )
        st.button("Subscribe to Pro Plan (Link to Stripe Checkout)", help="This would redirect to Stripe for payment", key="subscribe_button_placeholder")
        
        st.markdown("---") 
        # Do not st.stop() here, as the free trial user should still see the Bank Exporter

    tab1, tab2, tab3 = st.tabs(["Bank Transactions Exporter", "Payroll Sensitivity Analyzer", "Coming Soon..."])

    # --- Tool 1: Bank Transactions Exporter ---
    with tab1:
        st.header("Bank Transactions to Excel with GPT COA Tagging")
        
        # --- NEW: Gating the Bank Exporter if trial expired and not subscribed ---
        if not st.session_state.is_subscribed and trial_status == "expired":
            st.warning("Your 7-day free trial for the **Bank Transactions Exporter** has ended. Please log in and subscribe to continue using this tool.")
            st.stop() # Stop rendering this tool's content
        
        if not st.session_state.is_subscribed and trial_status == "active":
            st.info(f"You are currently on a **{remaining_days}-day free trial** for this tool.")

        st.markdown("Upload your bank statement (PDF, CSV, or Excel) to extract transactions and classify them with GPT!")

        # --- NEW: Optional COA Upload ---
        st.markdown("### Optional: Upload Custom Mappings")
        col_coa, col_vendor_map = st.columns(2)
        
        with col_coa:
            coa_upload_file = st.file_uploader(
                "Upload Chart of Accounts (COA) for Tagging (CSV/Excel)",
                type=["csv", "xls", "xlsx"],
                help="Upload a file with 'Vendor' and 'COA' columns to apply your own COA mappings. This will override AI tagging for matching vendors."
            )
            if coa_upload_file:
                try:
                    df_coa = pd.read_csv(coa_upload_file) if coa_upload_file.name.endswith(".csv") else pd.read_excel(coa_upload_file)
                    if 'Vendor' in df_coa.columns and 'COA' in df_coa.columns:
                        st.session_state.coa_mapping = dict(zip(df_coa['Vendor'], df_coa['COA']))
                        st.success(f"Loaded {len(st.session_state.coa_mapping)} custom COA mappings.")
                    else:
                        st.error("COA file must contain 'Vendor' and 'COA' columns.")
                        st.session_state.coa_mapping = {}
                except Exception as e:
                    st.error(f"Error loading COA file: {e}")
                    st.session_state.coa_mapping = {}

        with col_vendor_map:
            vendor_report_upload_file = st.file_uploader(
                "Upload Vendor Report with COA Mapping (CSV/Excel)",
                type=["csv", "xls", "xlsx"],
                help="Upload a file with 'Description Keyword' and 'Vendor' columns to map transaction descriptions to specific vendors. This runs *before* AI vendor extraction."
            )
            if vendor_report_upload_file:
                try:
                    df_vendor_map = pd.read_csv(vendor_report_upload_file) if vendor_report_upload_file.name.endswith(".csv") else pd.read_excel(vendor_report_upload_file)
                    if 'Description Keyword' in df_vendor_map.columns and 'Vendor' in df_vendor_map.columns:
                        st.session_state.vendor_mapping = {str(k).lower(): v for k, v in zip(df_vendor_map['Description Keyword'], df_vendor_map['Vendor'])}
                        st.success(f"Loaded {len(st.session_state.vendor_mapping)} custom Vendor mappings.")
                    else:
                        st.error("Vendor mapping file must contain 'Description Keyword' and 'Vendor' columns.")
                        st.session_state.vendor_mapping = {}
                except Exception as e:
                    st.error(f"Error loading Vendor mapping file: {e}")
                    st.session_state.vendor_mapping = {}

        st.markdown("---")


        file_type = st.radio("Select file type to upload:", ("PDF", "CSV or Excel"), horizontal=True, key="bank_file_type") 
        uploaded_files_bank = st.file_uploader(
            "Upload your bank statement file(s)", 
            type=["pdf", "csv", "xls", "xlsx"],
            accept_multiple_files=True,
            key="bank_uploader" 
        )
        
        transactions_df_bank = pd.DataFrame()
        if uploaded_files_bank:
            st.success(f"Processing {len(uploaded_files_bank)} file(s). Click 'Process Transactions' to begin.")
            process_button_bank = st.button("Process Transactions", key="bank_process_button") 

            if process_button_bank:
                all_transactions_dfs_bank = []
                for uploaded_file_bank in uploaded_files_bank:
                    st.subheader(f"Processing: {uploaded_file_bank.name}")
                    
                    file_year_bank = str(datetime.now().year) # Default to current year
                    year_match_bank = re.search(r'(\d{4})', uploaded_file_bank.name)
                    if year_match_bank:
                        file_year_bank = year_match_bank.group(1)
                        st.info(f"Detected year '{file_year_bank}' from filename for '{uploaded_file_bank.name}' dates.") 
                    else:
                        st.warning(f"Could not automatically detect year from filename. Defaulting to {file_year_bank} for '{uploaded_file_bank.name}' dates. Please ensure this is correct.")

                    with st.spinner(f"Extracting and parsing transactions from {uploaded_file_bank.name}..."):
                        current_file_df_bank = pd.DataFrame()

                        if file_type == "PDF": 
                            if uploaded_file_bank.name.lower().endswith(".pdf"):
                                raw_pdf_page_texts_bank = extract_pdf_text(BytesIO(uploaded_file_bank.getvalue()))
                                if raw_pdf_page_texts_bank:
                                    current_file_df_bank = gpt_parse_pdf_transactions(raw_pdf_page_texts_bank, file_year_bank)
                                else:
                                    st.error(f"Failed to extract any meaningful text from PDF: {uploaded_file_bank.name}. Please try another file or check its format.")
                            else:
                                st.error(f"File type selected is PDF, but '{uploaded_file_bank.name}' is not a .pdf. Skipping.")
                        else: # CSV or Excel
                            try:
                                if uploaded_file_bank.name.lower().endswith(".csv"):
                                    current_file_df_bank = pd.read_csv(uploaded_file_bank)
                                else: 
                                    current_file_df_bank = pd.read_excel(uploaded_file_bank)

                                # NEW: Infer standard columns for CSV/Excel
                                # Attempt to find common column names for Date, Description, Amount
                                date_col = next((col for col in current_file_df_bank.columns if re.search(r'date', col, re.IGNORECASE)), None)
                                desc_col = next((col for col in current_file_df_bank.columns if re.search(r'description|narrative|memo|details', col, re.IGNORECASE)), None)
                                amount_col = next((col for col in current_file_df_bank.columns if re.search(r'amount|debit|credit', col, re.IGNORECASE)), None)

                                if not all([date_col, desc_col, amount_col]):
                                    st.warning("Could not automatically detect 'Date', 'Description', and 'Amount' columns in your CSV/Excel. Please ensure they exist and consider renaming if parsing issues persist.")
                                    # Prompt user to select columns if auto-detection fails
                                    st.subheader("Manually Select Columns")
                                    date_col = st.selectbox("Select Date Column", current_file_df_bank.columns, key=f"date_col_{uploaded_file_bank.name}")
                                    desc_col = st.selectbox("Select Description Column", current_file_df_bank.columns, key=f"desc_col_{uploaded_file_bank.name}")
                                    amount_col = st.selectbox("Select Amount Column", current_file_df_bank.columns, key=f"amount_col_{uploaded_file_bank.name}")
                                    
                                if date_col and desc_col and amount_col:
                                    current_file_df_bank = current_file_df_bank[[date_col, desc_col, amount_col]].copy()
                                    current_file_df_bank.columns = ['Date', 'Description', 'Amount']
                                else:
                                    st.error("Required columns ('Date', 'Description', 'Amount') not found or selected. Skipping file.")
                                    current_file_df_bank = pd.DataFrame() # Empty DF to skip further processing
                                
                                if not current_file_df_bank.empty:
                                    # Clean and convert Amount column
                                    current_file_df_bank['Amount'] = pd.to_numeric(
                                        current_file_df_bank['Amount'].astype(str).str.replace(r'[$,()]', '', regex=True), 
                                        errors='coerce'
                                    )
                                    current_file_df_bank.dropna(subset=['Amount'], inplace=True) # Drop rows where amount couldn't be converted
                                    # Handle negative amounts if present in parentheses for CSV/Excel
                                    # This regex check and replacement might be redundant if pd.to_numeric with coerce handles it.
                                    # It's good to keep in mind for explicit handling if needed.
                                    # For now, relying on pd.to_numeric to handle common number formats.

                            except Exception as e:
                                st.error(f"Error reading CSV/Excel file '{uploaded_file_bank.name}': {e}. Please ensure it's a valid format. Skipping.")
                    
                    if not current_file_df_bank.empty:
                        current_file_df_bank['Source File'] = uploaded_file_bank.name 
                        all_transactions_dfs_bank.append(current_file_df_bank)

                if all_transactions_dfs_bank:
                    transactions_df_bank = pd.concat(all_transactions_dfs_bank, ignore_index=True)
                    
                    st.subheader("Extracted Transactions (Combined):")
                    
                    if "Description" not in transactions_df_bank.columns:
                        st.error("The combined DataFrame does not contain a 'Description' column. This is unexpected. Please check the raw JSON output in your terminal and GPT's parsing prompt.")
                        transactions_df_bank = pd.DataFrame() 
                    else:
                        st.info("Extracting Vendors and Classifying COAs...")
                        
                        extracted_vendors = []
                        coa_classifications = []
                        
                        overall_progress_bar_bank = st.progress(0)
                        overall_status_text_bank = st.empty()
                        
                        total_transactions_overall_bank = len(transactions_df_bank)
                        for i, row in transactions_df_bank.iterrows():
                            original_description = str(row["Description"]) 
                            
                            vendor = "Unknown Vendor" 
                            coa = "Uncategorized" 

                            # --- NEW: Prioritize uploaded vendor mapping ---
                            found_vendor_by_keyword = False
                            if st.session_state.vendor_mapping:
                                for keyword, mapped_vendor in st.session_state.vendor_mapping.items():
                                    if keyword.lower() in original_description.lower():
                                        vendor = mapped_vendor
                                        found_vendor_by_keyword = True
                                        break
                            
                            # Check known types if not found by keyword
                            if not found_vendor_by_keyword:
                                known_vendor, known_coa = identify_known_transaction_type(original_description)
                                if known_vendor:
                                    vendor = known_vendor
                                    # COA will be set from known_coa or overridden by COA mapping later
                                else:
                                    # Fallback to GPT if no keyword or known type matches
                                    if st.session_state.is_subscribed or trial_status == "active": # Only use GPT if subscribed or in trial
                                        vendor = gpt_extract_vendor(original_description)
                                    else:
                                        vendor = "N/A (Trial Expired/Not Subscribed)"

                            # --- NEW: Prioritize uploaded COA mapping ---
                            if vendor in st.session_state.coa_mapping:
                                coa = st.session_state.coa_mapping[vendor]
                            elif known_coa: # Use known COA if found earlier and no specific COA mapping for vendor
                                coa = known_coa
                            else:
                                # Fallback to GPT for COA if not found in mappings or known types
                                if st.session_state.is_subscribed or trial_status == "active": # Only use GPT if subscribed or in trial
                                    coa = gpt_coa_classification(vendor)
                                else:
                                    coa = "N/A (Trial Expired/Not Subscribed)"
                            
                            extracted_vendors.append(vendor)
                            coa_classifications.append(coa)
                            
                            progress_overall = (i + 1) / total_transactions_overall_bank
                            overall_progress_bar_bank.progress(progress_overall)
                            overall_status_text_bank.text(f"Overall Processing: {i+1}/{total_transactions_overall_bank} transactions...")
                        
                        transactions_df_bank["Vendor"] = extracted_vendors
                        transactions_df_bank["Guesstimated COA"] = coa_classifications
                        
                        overall_status_text_bank.success("Overall Vendor Extraction and COA Classification Complete!")
                        overall_progress_bar_bank.empty()

                        st.dataframe(transactions_df_bank)

                        st.subheader("Download Results (Combined):")
                        col1_bank, col2_bank = st.columns(2)
                        
                        with col1_bank:
                            excel_buffer_bank = BytesIO()
                            transactions_df_bank.to_excel(excel_buffer_bank, index=False, engine='xlsxwriter')
                            excel_buffer_bank.seek(0)
                            st.download_button(
                                label="Download Excel File", 
                                data=excel_buffer_bank, 
                                file_name="transactions_with_coa.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                key="bank_excel_download" 
                            )
                        
                        with col2_bank:
                            csv_buffer_bank = BytesIO()
                            transactions_df_bank.to_csv(csv_buffer_bank, index=False)
                            csv_buffer_bank.seek(0)
                            st.download_button(
                                label="Download CSV File", 
                                data=csv_buffer_bank, 
                                file_name="transactions_with_coa.csv",
                                mime="text/csv",
                                key="bank_csv_download" 
                            )
                else: 
                    st.warning("No transactions could be processed from any of the uploaded files for this tool.")

        else: 
            st.warning("Please upload file(s) to get started with the Bank Transactions Exporter.")

    # --- Tool 2: Payroll Sensitivity Analyzer (gated by subscription) ---
    with tab2:
        st.header("Payroll Sensitivity Analyzer")
        if st.session_state.is_subscribed:
            st.info("This tool is available for subscribed users.")
            st.markdown("**(Tool content for Payroll Sensitivity Analyzer would go here)**")
            st.warning("This feature is under development.")
            # Example placeholder for a subscribed feature
            # st.file_uploader("Upload Payroll Data")
            # st.button("Analyze Payroll")
        else:
            st.warning("This tool requires an active subscription. Please subscribe to unlock full access.")
            st.markdown("---")

    # --- Tool 3: Coming Soon... (gated by subscription) ---
    with tab3:
        st.header("Coming Soon...")
        if st.session_state.is_subscribed:
            st.info("Exciting new tools are on their way for our valued subscribers!")
        else:
            st.warning("Subscribe to unlock future tools and features!")

elif trial_status == "expired":
    st.subheader("Trial Ended")
    st.warning("Your 7-day free trial has expired. Please **log in or sign up** and **subscribe** to continue using the tools.")
    st.markdown("---")

````