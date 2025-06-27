import streamlit as st
from asc_606_tool import run as run_asc_606
from asc_842_tool import run as run_asc_842
from payroll_tool import run as run_payroll
from bank_pdf_exporter import run as run_bank_pdf
from recon_tool import run as run_recon
from prepaid_tool import run as run_prepaid

st.set_page_config(page_title="CIFRA Platform", layout="wide")

st.sidebar.title("CIFRA Tools")
tool = st.sidebar.radio("Choose a tool:", [
    "Payroll Sensibility Analyzer",
    "ASC 606 Revenue Recognition",
    "ASC 842 Lease Accounting",
    "Prepaid Expense Tool",
    "Bank PDF Exporter",
    "Bank Reconciliation Tool"
])

st.title("CIFRA Smart Finance Platform")

if tool == "Payroll Sensibility Analyzer":
    run_payroll()
elif tool == "ASC 606 Revenue Recognition":
    run_asc_606()
elif tool == "ASC 842 Lease Accounting":
    run_asc_842()
elif tool == "Prepaid Expense Tool":
    run_prepaid()
elif tool == "Bank PDF Exporter":
    run_bank_pdf()
elif tool == "Bank Reconciliation Tool":
    run_recon()
else:
    st.error("Tool not found.")
