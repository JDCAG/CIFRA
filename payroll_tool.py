import streamlit as st
import pandas as pd

st.set_page_config(page_title="Payroll Sensibility Analyzer", layout="centered")

st.title("📊 Payroll Sensibility Analyzer")

uploaded_file = st.file_uploader("Upload a payroll CSV file", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    st.subheader("Raw Payroll Data")
    st.dataframe(df)

    # Select columns
    st.subheader("Configuration")
    col_name = st.selectbox("Select employee name column", df.columns)
    col_title = st.selectbox("Select title/position column", df.columns)
    col_salary = st.selectbox("Select salary/compensation column", df.columns)

    if st.button("Analyze"):
        # Placeholder logic for percentile evaluation
        def categorize(row):
            if row[col_salary] >= 150000:
                return "Overpaid"
            elif row[col_salary] <= 70000:
                return "Underpaid"
            else:
                return "Fairly Paid"

        df_result = df.copy()
        df_result["Classification"] = df_result.apply(categorize, axis=1)

        st.subheader("Payroll Analysis Result")
        st.dataframe(df_result[[col_name, col_title, col_salary, "Classification"]])

        csv = df_result.to_csv(index=False).encode("utf-8")
        st.download_button("Download Result CSV", csv, "payroll_analysis.csv", "text/csv")

else:
    st.info("Please upload a CSV file to begin.")
