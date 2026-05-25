import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.title("Inventory Optimization Dashboard")

uploaded_file = st.file_uploader(
    "Upload Inventory Optimization Template",
    type=['xlsx']
)

if uploaded_file:

    inventory_df = pd.read_excel(
        uploaded_file,
        sheet_name='Inventory_Data'
    )

    price_df = pd.read_excel(
        uploaded_file,
        sheet_name='Price_Data'
    )

    st.success("File uploaded successfully")

#Show Uploaded Data Preview
    st.subheader("Inventory Data Preview")

    st.dataframe(
        inventory_df.head()
    )

# Merge Pricing

    inventory_df['Last_Material'] = (
        inventory_df['Last_Material']
        .astype(str)
    )

    price_df['Last_Material'] = (
        price_df['Last_Material']
        .astype(str)
    )

    df = inventory_df.merge(
        price_df,
        on='Last_Material',
        how='left'
    )

# Create Monthly Columns List
    monthly_cols = [
        "Mar'24","Apr'24","May'24",
        "Jun'24","Jul'24","Aug'24",
        "Sep'24","Oct'24","Nov'24",
        "Dec'24","Jan'25","Feb'25",
        "Mar'25","Apr'25","May'25",
        "Jun'25","Jul'25","Aug'25",
        "Sep'25","Oct'25","Nov'25",
        "Dec'25","Jan'26","Feb'26",
        "Mar'26","Apr'26","May'26"
    ]

# Run Optimization Engine

    # Demand Statistics
    df['Avg_Monthly_Demand'] = (
        df[monthly_cols].mean(axis=1)
    )

    df['Demand_StdDev'] = (
        df[monthly_cols].std(axis=1)
    )

    # Annual Demand
    df['Annual_Demand'] = (
        df[monthly_cols].sum(axis=1)
    )

    # Lead Time
    df['Effective_LT_Days'] = np.where(
        df['New_Buy_LT'].notnull(),
        df['New_Buy_LT'],
        df['Repair_LT']
    )

    df['LT_Months'] = (
        df['Effective_LT_Days'] / 30
    )

    # Lead Time Demand
    df['Lead_Time_Demand'] = (
        df['Avg_Monthly_Demand'] *
        df['LT_Months']
    )

    # Safety Stock
    z_score = 1.65

    df['Safety_Stock'] = (
        z_score *
        df['Demand_StdDev'] *
        np.sqrt(df['LT_Months'])
    )

    # ROP
    df['ROP'] = (
        df['Lead_Time_Demand'] +
        df['Safety_Stock']
    )

    # Inventory Risk
    def inventory_risk(row):

        if row['Net_Inventory'] <= 0:
            return 'Severe Risk'

        elif row['Net_Inventory'] < row['Safety_Stock']:
            return 'High Risk'

        elif row['Net_Inventory'] < row['ROP']:
            return 'Medium Risk'

        else:
            return 'Low Risk'

    df['Inventory_Risk'] = df.apply(
        inventory_risk,
        axis=1
    )
# Financial Metrics

    # Inventory Value
    df['Inventory_Value'] = (
        df['Net_Inventory'] *
        df['Net_Price']
    )

    # Excess Qty
    df['Excess_Qty'] = (
        df['Net_Inventory'] -
        df['ROP']
    )

    # Excess Value
    df['Excess_Value'] = np.where(
        df['Excess_Qty'] > 0,
        df['Excess_Qty'] * df['Net_Price'],
        0
    )

# KPI Dashboard
    st.header("Executive KPI Dashboard")

    total_inventory = (
        df['Inventory_Value'].sum()
    )

    total_excess = (
        df['Excess_Value'].sum()
    )

    excess_pct = (
        total_excess / total_inventory
    ) * 100


    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Inventory Value",
        f"{total_inventory:,.0f}"
    )

    col2.metric(
        "Excess Value",
        f"{total_excess:,.0f}"
    )

    col3.metric(
        "Excess %",
        f"{excess_pct:.2f}%"
    )

# Risk Chart
    st.subheader(
        "Inventory Risk Distribution"
    )

    risk_counts = df[
        'Inventory_Risk'
    ].value_counts()

    fig, ax = plt.subplots()

    risk_counts.plot(
        kind='bar',
        ax=ax
    )

    st.pyplot(fig)

# Top Excess Inventory

    st.subheader(
        "Top Excess Inventory"
    )

    top_excess = df.sort_values(
        by='Excess_Value',
        ascending=False
    ).head(10)

    st.dataframe(top_excess[[
        'Last_Material',
        'Description',
        'Excess_Value'
    ]])

# Download Optimized Report
    output = df.to_csv(index=False)

    st.download_button(
        label="Download Optimized Report",
        data=output,
        file_name='optimized_inventory_report.csv',
        mime='text/csv'
    )