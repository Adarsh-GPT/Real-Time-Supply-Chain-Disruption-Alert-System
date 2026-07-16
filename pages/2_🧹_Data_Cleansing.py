"""pages/2_🧹_Data_Cleansing.py — Data Cleansing showcase."""
import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Data Cleansing • SupplyRadar", page_icon="🧹", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif;}
.header-box { background: var(--secondary-background-color); padding: 1.5rem; border-radius: 10px; border: 1px solid var(--border-color); margin-bottom: 1.5rem; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="header-box">
    <h2>🧹 Data Cleansing & ETL Pipeline</h2>
    <p style="color:#8899aa;">Demonstrating automated data cleaning, standardization, and quality improvement using Python and Pandas (Extract, Transform, Load).</p>
</div>
""", unsafe_allow_html=True)

@st.cache_data
def generate_messy_data():
    """Generates mock 'dirty' procurement data mimicking real-world ERP exports."""
    np.random.seed(42)
    data = {
        'Supplier_ID': ['SUP-001', 'sup-002', ' SUP-003 ', None, 'SUP-005', 'SUP-001', 'SUP-007'],
        'Company': ['marriott', ' SYSCO ', 'ecolab', 'US Foods', 'hilton', 'marriott', 'Marriott Int.'],
        'Category': ['Linens', 'F&B', 'Cleaning', 'F&B', 'Furniture', 'Linens', 'F&B'],
        'Order_Date': ['12/31/2023', '2023-12-30', '12-29-23', 'invalid_date', '2023/12/27', '12/31/2023', '12/25/2023'],
        'Amount_USD': ['$5000', '1200.50', '€3000', '450.0', None, '$5000', '-200'],
        'Risk_Score': [85, 90, 110, 45, 60, 85, 30] # 110 is invalid (max 100)
    }
    return pd.DataFrame(data)

df_messy = generate_messy_data()

st.markdown("### 1. Raw Data Ingestion (Dirty Data)")
st.write("Data extracted from legacy supplier systems often contains inconsistencies, nulls, and format errors.")
st.dataframe(df_messy, use_container_width=True)

st.markdown("### 2. Automated Cleaning Pipeline")
st.write("We apply a standard Pandas pipeline to sanitize and normalize the dataset.")

code = '''def clean_procurement_data(df):
    # 1. Drop complete duplicates
    df = df.drop_duplicates()
    
    # 2. Standardize text strings (strip whitespace, title case)
    df['Company'] = df['Company'].str.strip().str.title()
    df['Supplier_ID'] = df['Supplier_ID'].str.strip().str.upper()
    df['Company'] = df['Company'].replace('Marriott Int.', 'Marriott')
    
    # 3. Handle missing values
    df = df.dropna(subset=['Supplier_ID', 'Amount_USD'])
    
    # 4. Clean and convert currency strings to float
    df['Amount_USD'] = df['Amount_USD'].replace({'\\$': '', '€': '', ',': ''}, regex=True).astype(float)
    df = df[df['Amount_USD'] > 0] # Remove negative anomalies
    
    # 5. Standardize dates
    df['Order_Date'] = pd.to_datetime(df['Order_Date'], errors='coerce')
    df = df.dropna(subset=['Order_Date']) # Drop rows where date parsing failed
    
    # 6. Cap Risk Score to valid range [0-100]
    df['Risk_Score'] = df['Risk_Score'].clip(0, 100)
    
    return df.reset_index(drop=True)'''

st.code(code, language='python')

def clean_procurement_data(df):
    df = df.copy()
    df = df.drop_duplicates()
    df['Company'] = df['Company'].str.strip().str.title()
    df['Supplier_ID'] = df['Supplier_ID'].str.strip().str.upper()
    df['Company'] = df['Company'].replace('Marriott Int.', 'Marriott')
    df = df.dropna(subset=['Supplier_ID', 'Amount_USD'])
    df['Amount_USD'] = df['Amount_USD'].replace({'\\$': '', '€': '', ',': ''}, regex=True).astype(float)
    df = df[df['Amount_USD'] > 0]
    df['Order_Date'] = pd.to_datetime(df['Order_Date'], errors='coerce')
    df = df.dropna(subset=['Order_Date'])
    df['Risk_Score'] = df['Risk_Score'].clip(0, 100)
    return df.reset_index(drop=True)

df_clean = clean_procurement_data(df_messy)

st.markdown("### 3. Final Standardized Data (Ready for Analysis)")
st.dataframe(df_clean, use_container_width=True)

col1, col2, col3 = st.columns(3)
col1.metric("Original Rows", len(df_messy))
col2.metric("Cleaned Rows", len(df_clean))
col3.metric("Data Quality Score", "100%", delta="25%", delta_color="normal")
