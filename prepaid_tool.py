import streamlit as st
import pandas as pd
import datetime as dt

st.set_page_config(page_title="Prepaid Expense Tool", layout="centered")

st.title("💳 Prepaid Expense Amortization Tool")

uploaded_file = st.file_uploader("Upload a CSV with prepaid expense details", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    st.subheader("Uploaded Prepaid Expense Data")
    st.dataframe(df)

    col_name = st.selectbox("Select Expense Name column", df.columns)
    col_start = st.selectbox("Select Start Date column", df.columns)
    col_end = st.selectbox("Select End Date column", df.columns)
    col_amount = st.selectbox("Select Total Amount column", df.columns)

    df[col_start] = pd.to_datetime(df[col_start], errors='coerce')
    df[col_end] = pd.to_datetime(df[col_end], errors='coerce')

    if st.button("Generate Amortization Schedule"):
        amortized = []

        for _, row in df.iterrows():
            name = row[col_name]
            start = row[col_start]
            end = row[col_end]
            amount = row[col_amount]

            if pd.isnull(start) or pd.isnull(end) or pd.isnull(amount):
                continue

            periods = pd.date_range(start, end, freq='MS')
            monthly_amt = amount / len(periods)

            for date in periods:
                amortized.append({
                    "Expense Name": name,
                    "Month": date.strftime('%Y-%m'),
                    "Amortized Amount": round(monthly_amt, 2)
                })

        df_result = pd.DataFrame(amortized)
        st.subheader("Generated Amortization Schedule")
        st.dataframe(df_result)

        csv = df_result.to_csv(index=False).encode("utf-8")
        st.download_button("Download Schedule as CSV", csv, "prepaid_expense_amortization.csv", "text/csv")
else:
    st.info("Please upload a CSV file to get started.")
