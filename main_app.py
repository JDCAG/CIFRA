import streamlit as st
from bank_pdf_exporter import run as run_bank_exporter
from payroll_tool import run as run_payroll
from recon_tool import run as run_recon
from asc_606_tool import run as run_606
from asc_842_tool import run as run_842
from prepaid_tool import run as run_prepaid

st.set_page_config(page_title="CIFRA", layout="centered")

st.title("CIFRA")

st.markdown("### Choose a tool to launch:")

tool_options = {
    "🏦 Bank PDF Exporter": {"func": run_bank_exporter, "tag": "Free trial"},
    "📈 Payroll Sensibility Analyzer": {"func": run_payroll, "tag": "Pro only"},
    "📊 Bank Reconciliation Tool": {"func": run_recon, "tag": "Pro only"},
    "🧾 ASC 606 Tool": {"func": run_606, "tag": "Pro only"},
    "📘 ASC 842 Tool": {"func": run_842, "tag": "Pro only"},
    "📙 Prepaid Expense Tool": {"func": run_prepaid, "tag": "Pro only"}
}

selected_tool = st.selectbox("Select a tool", list(tool_options.keys()))

tag = tool_options[selected_tool]["tag"]
if tag == "Pro only":
    st.warning(f"{selected_tool} is a Pro-only feature.")
elif tag == "Free trial":
    st.success(f"{selected_tool} is available with a 7-day free trial.")

if st.button("Launch"):
    tool_options[selected_tool]["func"]()
