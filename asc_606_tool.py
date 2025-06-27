import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="ASC 606 Revenue Recognition", layout="centered")

st.title("📑 ASC 606 Revenue Recognition Tool")

uploaded_file = st.file_uploader("Upload a revenue schedule CSV file", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    st.subheader("Uploaded Revenue Schedule")
    st.dataframe(df)

    st.subheader("Configuration")
    col_name = st.selectbox("Select Contract/Item column", df.columns)
    col_start = st.selectbox("Select Revenue Start Date column", df.columns)
    col_end = st.selectbox("Select Revenue End Date column", df.columns)
    col_amount = st.selectbox("Select Total Revenue Amount column", df.columns)

    df[col_start] = pd.to_datetime(df[col_start], errors='coerce')
    df[col_end] = pd.to_datetime(df[col_end], errors='coerce')

    if st.button("Generate Revenue Schedule"):
        schedules = []

        for _, row in df.iterrows():
            name = row[col_name]
            start = row[col_start]
            end = row[col_end]
            amount = row[col_amount]

            if pd.isnull(start) or pd.isnull(end):
                continue

            months = pd.date_range(start, end, freq='MS')
            monthly_amount = amount / len(months) if len(months) > 0 else 0

            for m in months:
                schedules.append({
                    "Contract/Item": name,
                    "Month": m.strftime('%Y-%m'),
                    "Monthly Revenue": round(monthly_amount, 2)
                })

        df_sched = pd.DataFrame(schedules)
        st.subheader("Generated Revenue Recognition Schedule")
        st.dataframe(df_sched)

        csv = df_sched.to_csv(index=False).encode("utf-8")
        st.download_button("Download Revenue Schedule CSV", csv, "revenue_schedule.csv", "text/csv")

else:
    st.info("Please upload a CSV file to begin.")
