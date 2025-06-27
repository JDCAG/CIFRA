import streamlit as st
import pandas as pd
import numpy as np
import datetime as dt

st.set_page_config(page_title="ASC 842 Lease Accounting", layout="centered")

st.title("🏢 ASC 842 Lease Accounting Tool")

uploaded_file = st.file_uploader("Upload a lease schedule CSV file", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    st.subheader("Uploaded Lease Schedule")
    st.dataframe(df)

    st.subheader("Configuration")
    col_lease = st.selectbox("Select Lease Name column", df.columns)
    col_start = st.selectbox("Select Lease Start Date column", df.columns)
    col_end = st.selectbox("Select Lease End Date column", df.columns)
    col_payment = st.selectbox("Select Monthly Payment column", df.columns)
    col_rate = st.selectbox("Select Discount Rate column", df.columns)

    df[col_start] = pd.to_datetime(df[col_start], errors='coerce')
    df[col_end] = pd.to_datetime(df[col_end], errors='coerce')

    if st.button("Generate Amortization Schedule"):
        amort_schedules = []

        for _, row in df.iterrows():
            lease = row[col_lease]
            start = row[col_start]
            end = row[col_end]
            pmt = row[col_payment]
            rate = row[col_rate] / 100 / 12  # Monthly rate

            if pd.isnull(start) or pd.isnull(end) or pd.isnull(pmt) or pd.isnull(rate):
                continue

            periods = pd.date_range(start, end, freq='MS')
            n = len(periods)
            pv = pmt * (1 - (1 + rate) ** -n) / rate if rate > 0 else pmt * n
            remaining_liability = pv

            for m in periods:
                interest = remaining_liability * rate
                principal = pmt - interest
                remaining_liability -= principal

                amort_schedules.append({
                    "Lease": lease,
                    "Month": m.strftime('%Y-%m'),
                    "Payment": round(pmt, 2),
                    "Interest": round(interest, 2),
                    "Principal": round(principal, 2),
                    "Liability Balance": round(max(remaining_liability, 0), 2)
                })

        df_amort = pd.DataFrame(amort_schedules)
        st.subheader("Generated Amortization Schedule")
        st.dataframe(df_amort)

        csv = df_amort.to_csv(index=False).encode("utf-8")
        st.download_button("Download Amortization Schedule CSV", csv, "lease_amortization_schedule.csv", "text/csv")

else:
    st.info("Please upload a CSV file to begin.")
