import streamlit as st

# Import each tool's `run()` function
from asc_606_tool import run as run_606
from asc_842_tool import run as run_842
from payroll_tool import run as run_payroll
from bank_pdf_exporter import run as run_pdf
from recon_tool import run as run_recon
from prepaid_tool import run as run_prepaid

# Streamlit app config
st.set_page_config(page_title="CIFRA Platform", layout="wide")

# Sidebar layout
st.sidebar.image("https://avatars.githubusercontent.com/u/16881247?s=200", width=80)
st.sidebar.title("📊 CIFRA Tools")
tool = st.sidebar.radio("Select a tool:", [
    "Payroll Sensitivity",
    "ASC 606 (Rev Rec)",
    "ASC 842 (Lease Accounting)",
    "Prepaid Expense Tool",
    "Bank PDF Exporter",
    "Reconciliation Tool"
])

# Main content router
st.title("🧠 CIFRA: Smart Accounting Tools")

if tool == "Payroll Sensitivity":
    run_payroll()
elif tool == "ASC 606 (Rev Rec)":
    run_606()
elif tool == "ASC 842 (Lease Accounting)":
    run_842()
elif tool == "Prepaid Expense Tool":
    run_prepaid()
elif tool == "Bank PDF Exporter":
    run_pdf()
elif tool == "Reconciliation Tool":
    run_recon()
else:
    st.warning("Please select a tool from the sidebar.")
