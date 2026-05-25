```python
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO
from datetime import datetime, timedelta

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------
st.set_page_config(
    page_title="Inventory Optimization Dashboard",
    layout="wide"
)

st.title("Inventory Optimization Dashboard")
st.markdown(
    "Medical Equipment Spare Parts Optimization & PO Trigger Engine"
)

# --------------------------------------------------
# FILE UPLOAD
# --------------------------------------------------
uploaded_file = st.file_uploader(
    "Upload Inventory Optimization Template",
    type=['xlsx']
)

# --------------------------------------------------
# EXCEL DOWNLOAD FUNCTION
# --------------------------------------------------
def convert_df_to_excel(dataframe, sheet_name="Optimized_Report"):

    output = BytesIO()

    with pd.ExcelWriter(output, engine='openpyxl') as writer:

        dataframe.to_excel(
            writer,
            index=False,
            sheet_name=sheet_name
        )

    processed_data = output.getvalue()

    return processed_data

# --------------------------------------------------
# MAIN APPLICATION
# --------------------------------------------------
if uploaded_file:

    try:

        # --------------------------------------------------
        # READ EXCEL SHEETS
        # --------------------------------------------------
        inventory_df = pd.read_excel(
            uploaded_file,
            sheet_name='Inventory_Data'
        )

        price_df = pd.read_excel(
            uploaded_file,
            sheet_name='Price_Data'
        )

        st.success("File uploaded successfully")

        # --------------------------------------------------
        # DATA PREVIEW
        # --------------------------------------------------
        st.subheader("Inventory Data Preview")
        st.dataframe(inventory_df.head())

        # --------------------------------------------------
        # STANDARDIZE MATERIAL KEYS
        # --------------------------------------------------
        inventory_df['Last_Material'] = (
            inventory_df['Last_Material']
            .astype(str)
        )

        price_df['Last_Material'] = (
            price_df['Last_Material']
            .astype(str)
        )

        # --------------------------------------------------
        # MERGE PRICE DATA
        # --------------------------------------------------
        df = inventory_df.merge(
            price_df,
            on='Last_Material',
            how='left'
        )

        # --------------------------------------------------
        # AUTO DETECT MONTHLY COLUMNS
        # --------------------------------------------------
        monthly_cols = [
            col for col in df.columns
            if "'" in str(col)
        ]

        # --------------------------------------------------
        # DEMAND ANALYTICS
        # --------------------------------------------------
        df['Avg_Monthly_Demand'] = (
            df[monthly_cols].mean(axis=1)
        )

        df['Demand_StdDev'] = (
            df[monthly_cols].std(axis=1)
        )

        df['Annual_Demand'] = (
            df[monthly_cols].sum(axis=1)
        )

        # --------------------------------------------------
        # LEAD TIME CALCULATIONS
        # --------------------------------------------------
        df['Effective_LT_Days'] = np.where(
            df['New_Buy_LT'].notnull(),
            df['New_Buy_LT'],
            df['Repair_LT']
        )

        df['LT_Months'] = (
            df['Effective_LT_Days'] / 30
        )

        # --------------------------------------------------
        # LEAD TIME DEMAND
        # --------------------------------------------------
        df['Lead_Time_Demand'] = (
            df['Avg_Monthly_Demand'] *
            df['LT_Months']
        )

        # --------------------------------------------------
        # SAFETY STOCK
        # --------------------------------------------------
        z_score = 1.65

        df['Safety_Stock'] = (
            z_score *
            df['Demand_StdDev'] *
            np.sqrt(df['LT_Months'])
        )

        # --------------------------------------------------
        # REORDER POINT
        # --------------------------------------------------
        df['ROP'] = (
            df['Lead_Time_Demand'] +
            df['Safety_Stock']
        )

        # --------------------------------------------------
        # INVENTORY RISK ENGINE
        # --------------------------------------------------
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

        # --------------------------------------------------
        # FINANCIAL METRICS
        # --------------------------------------------------
        df['Inventory_Value'] = (
            df['Net_Inventory'] *
            df['Net_Price']
        )

        df['Excess_Qty'] = (
            df['Net_Inventory'] -
            df['ROP']
        )

        df['Excess_Value'] = np.where(
            df['Excess_Qty'] > 0,
            df['Excess_Qty'] * df['Net_Price'],
            0
        )

        # --------------------------------------------------
        # DAILY DEMAND
        # --------------------------------------------------
        df['Avg_Daily_Demand'] = (
            df['Avg_Monthly_Demand'] / 30
        )

        # --------------------------------------------------
        # DAYS TO STOCKOUT
        # --------------------------------------------------
        df['Days_To_Stockout'] = np.where(

            df['Avg_Daily_Demand'] > 0,

            df['Net_Inventory'] /
            df['Avg_Daily_Demand'],

            np.nan
        )

        # --------------------------------------------------
        # PO TRIGGER ENGINE
        # --------------------------------------------------
        def po_trigger(row):

            if pd.isnull(row['Days_To_Stockout']):
                return 'NO DEMAND'

            elif row['Days_To_Stockout'] <= row['Effective_LT_Days']:
                return 'TRIGGER PO'

            elif row['Days_To_Stockout'] <= (
                row['Effective_LT_Days'] + 15
            ):
                return 'EXPEDITE'

            else:
                return 'MONITOR'

        df['PO_Action'] = df.apply(
            po_trigger,
            axis=1
        )

        # --------------------------------------------------
        # RECOMMENDED PO QUANTITY
        # --------------------------------------------------
        df['Recommended_PO_Qty'] = np.where(

            df['ROP'] > df['Net_Inventory'],

            np.ceil(
                df['ROP'] -
                df['Net_Inventory']
            ),

            0
        )

        # --------------------------------------------------
        # PO ALERT
        # --------------------------------------------------
        def po_alert(row):

            if row['PO_Action'] == 'TRIGGER PO':
                return 'URGENT BUY'

            elif row['PO_Action'] == 'EXPEDITE':
                return 'EXPEDITE SHIPMENT'

            else:
                return 'NORMAL'

        df['PO_Alert'] = df.apply(
            po_alert,
            axis=1
        )

        # --------------------------------------------------
        # PO TRIGGER DATE
        # --------------------------------------------------
        today = datetime.today()

        def calculate_trigger_date(days):

            if pd.isnull(days):
                return None

            days = min(days, 3650)

            trigger_days = max(days - 30, 0)

            return (
                today + timedelta(days=trigger_days)
            ).date()

        df['PO_Trigger_Date'] = df[
            'Days_To_Stockout'
        ].apply(calculate_trigger_date)

        # --------------------------------------------------
        # TOTAL OPEN PO
        # --------------------------------------------------
        df['Total_Open_PO'] = (
            df['Open_Po_Qty_Nb'] +
            df['Open_Po_Qty_Rp']
        )

        # --------------------------------------------------
        # TOTAL FUTURE SUPPLY
        # --------------------------------------------------
        df['Total_Future_Supply'] = (
            df['Net_Inventory'] +
            df['Total_Open_PO']
        )

        # --------------------------------------------------
        # PO COVERAGE GAP
        # --------------------------------------------------
        df['PO_Coverage_Gap'] = (
            df['Total_Future_Supply'] -
            df['ROP']
        )

        # --------------------------------------------------
        # PO SUFFICIENCY ENGINE
        # --------------------------------------------------
        def po_sufficiency(row):

            if row['PO_Coverage_Gap'] < 0:
                return 'INSUFFICIENT PO'

            elif row['PO_Coverage_Gap'] <= (
                row['Safety_Stock']
            ):
                return 'LOW PO COVERAGE'

            else:
                return 'SUFFICIENT PO'

        df['PO_Sufficiency_Status'] = (
            df.apply(
                po_sufficiency,
                axis=1
            )
        )

        # --------------------------------------------------
        # ADDITIONAL PO REQUIRED
        # --------------------------------------------------
        df['Additional_PO_Required'] = np.where(

            df['PO_Coverage_Gap'] < 0,

            np.ceil(
                abs(df['PO_Coverage_Gap'])
            ),

            0
        )

        # --------------------------------------------------
        # EXECUTIVE KPI DASHBOARD
        # --------------------------------------------------
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

        # --------------------------------------------------
        # INVENTORY RISK CHART
        # --------------------------------------------------
        st.subheader("Inventory Risk Distribution")

        risk_counts = df[
            'Inventory_Risk'
        ].value_counts()

        fig, ax = plt.subplots()

        risk_counts.plot(
            kind='bar',
            ax=ax
        )

        st.pyplot(fig)

        # --------------------------------------------------
        # TOP EXCESS INVENTORY
        # --------------------------------------------------
        st.subheader("Top Excess Inventory")

        top_excess = df.sort_values(
            by='Excess_Value',
            ascending=False
        ).head(10)

        st.dataframe(top_excess[[
            'Last_Material',
            'Description',
            'Excess_Value'
        ]])

        # --------------------------------------------------
        # PO TRIGGER DASHBOARD
        # --------------------------------------------------
        st.subheader("PO Trigger Engine")

        po_df = df[
            df['PO_Action'] != 'MONITOR'
        ]

        st.dataframe(po_df[[
            'Last_Material',
            'Description',
            'Net_Inventory',
            'Days_To_Stockout',
            'Effective_LT_Days',
            'Recommended_PO_Qty',
            'PO_Action',
            'PO_Alert',
            'PO_Trigger_Date'
        ]])

        # --------------------------------------------------
        # PO SUFFICIENCY ANALYSIS
        # --------------------------------------------------
        st.subheader("PO Sufficiency Analysis")

        po_gap_df = df[
            df['PO_Sufficiency_Status'] != 'SUFFICIENT PO'
        ]

        st.dataframe(po_gap_df[[
            'Last_Material',
            'Description',
            'Net_Inventory',
            'Total_Open_PO',
            'ROP',
            'PO_Coverage_Gap',
            'Additional_PO_Required',
            'PO_Sufficiency_Status',
            'PO_Action',
            'PO_Alert'
        ]])

        # --------------------------------------------------
        # DOWNLOAD OPTIMIZED REPORT
        # --------------------------------------------------
        excel_data = convert_df_to_excel(df)

        st.download_button(
            label="Download Optimized Excel Report",
            data=excel_data,
            file_name='optimized_inventory_report.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

        # --------------------------------------------------
        # DOWNLOAD PO TRIGGER REPORT
        # --------------------------------------------------
        po_excel = convert_df_to_excel(
            po_df,
            sheet_name='PO_Trigger_Report'
        )

        st.download_button(
            label="Download PO Trigger Excel Report",
            data=po_excel,
            file_name='po_trigger_report.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

        # --------------------------------------------------
        # DOWNLOAD PO GAP REPORT
        # --------------------------------------------------
        po_gap_excel = convert_df_to_excel(
            po_gap_df,
            sheet_name='PO_Gap_Report'
        )

        st.download_button(
            label='Download PO Gap Report',
            data=po_gap_excel,
            file_name='po_gap_report.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    except Exception as e:

        st.error(f"Error processing file: {e}")

else:

    st.info("Please upload Inventory Optimization Template to continue")
