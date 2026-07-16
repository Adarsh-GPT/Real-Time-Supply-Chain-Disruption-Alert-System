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
uploaded_file = st.file_uploader("Upload your own messy CSV (or use our default ERP extract)", type=["csv"])

if uploaded_file is not None:
    try:
        df_messy = pd.read_csv(uploaded_file)
        st.success("Custom CSV loaded successfully!")
    except Exception as e:
        st.error(f"Error reading CSV: {e}")
        df_messy = generate_messy_data()
else:
    df_messy = generate_messy_data()
    st.info("Using default legacy ERP extract. Upload a CSV above to test your own data.")

st.dataframe(df_messy, use_container_width=True)

st.markdown("### 2. Interactive Python Pipeline Editor")
st.write("Write your custom Pandas code below. The function **must** be named `clean_data` and accept/return a DataFrame `df`.")

default_code = '''def clean_data(df):
    df = df.copy()
    
    # 1. Drop duplicates
    df = df.drop_duplicates()
    
    # 2. Clean 'Company' names if column exists
    if 'Company' in df.columns:
        df['Company'] = df['Company'].astype(str).str.strip().str.title()
        df['Company'] = df['Company'].replace('Marriott Int.', 'Marriott')
        
    # 3. Clean Currency if 'Amount_USD' exists
    if 'Amount_USD' in df.columns:
        df['Amount_USD'] = df['Amount_USD'].astype(str).replace({'\\$': '', '€': '', ',': ''}, regex=True).astype(float)
        
    # 4. Standardize dates
    if 'Order_Date' in df.columns:
        df['Order_Date'] = pd.to_datetime(df['Order_Date'], errors='coerce')
        
    return df.reset_index(drop=True)
'''

user_code = st.text_area("Python Editor", value=default_code, height=300, key="code_editor")

st.markdown("### 3. Pipeline Execution Results")
if st.button("🚀 Run Pipeline", type="primary"):
    with st.spinner("Executing custom python script..."):
        try:
            # Create a safe dictionary for execution
            local_env = {"pd": pd, "np": np}
            
            # Execute the user's code definition
            exec(user_code, local_env)
            
            # Get the defined function
            if "clean_data" not in local_env:
                st.error("Error: Your code must define a function named `clean_data`.")
            else:
                clean_func = local_env["clean_data"]
                df_clean = clean_func(df_messy)
                
                st.success("Pipeline executed successfully!")
                st.dataframe(df_clean, use_container_width=True)
                
                # Show metrics
                col1, col2, col3 = st.columns(3)
                col1.metric("Original Rows", len(df_messy))
                col2.metric("Cleaned Rows", len(df_clean))
                col3.metric("Fields Transformed", sum(df_messy.dtypes != df_clean.dtypes) if len(df_messy.columns) == len(df_clean.columns) else "N/A", delta="Optimized")
                
                # Download button
                csv = df_clean.to_csv(index=False).encode('utf-8')
                st.download_button("⬇️ Download Cleaned Data", data=csv, file_name="cleaned_data.csv", mime="text/csv")
                
        except Exception as e:
            st.error(f"❌ Execution Error:\n{str(e)}")
