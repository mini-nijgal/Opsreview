import streamlit as st
import pandas as pd
import os
import io
import requests
from datetime import datetime

# Google Sheets Configuration
GOOGLE_SHEET_ID = "1Nxvj1LRWYIw3cQcX2Qz9RJmvv17JlCe-V8G2tmvqHfE"
BASE_GOOGLE_SHEETS_URL = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/export?format=csv"

DATA_SOURCES = {
    "ops_review": {
        "url": f"{BASE_GOOGLE_SHEETS_URL}&sheet=Master",
        "sheet": "Master"
    },
    "finance": {
        "url": f"{BASE_GOOGLE_SHEETS_URL}&sheet=Finance", 
        "sheet": "Finance"
    },
    "revenue": {
        "url": f"{BASE_GOOGLE_SHEETS_URL}&sheet=Revenue",
        "sheet": "Revenue"
    },
    "tickets": {
        "url": f"{BASE_GOOGLE_SHEETS_URL}&sheet=Tickets",
        "sheet": "Tickets"
    },
    "may_revenue_excel": {
        "file": "May'25 Revenue.xlsx",
        "sheets": ["Summary", "Details", "Projections"]
    },
    "weekly_status_pdf": {
        "url": "https://github.com/mini-nijgal/Opsreview/raw/main/Weekly%20Project%20Status%207.05.2025.pdf"
    }
}

def read_data_from_url(url):
    """Read CSV data from URL with encoding fallback"""
    try:
        try:
            df = pd.read_csv(url)
        except UnicodeDecodeError:
            df = pd.read_csv(url, encoding='latin1')
        
        # Convert date columns if they exist
        for date_col in ["Contract Start Date", "Contract End Date", "Project Start Date"]:
            if date_col in df.columns:
                df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
        
        return df
    except Exception as e:
        st.error(f"Error reading data from URL: {e}")
        return None

def load_may_revenue_excel():
    """Load May 2025 Excel file"""
    try:
        excel_file_path = os.path.join(os.path.dirname(__file__), "..", "May'25 Revenue.xlsx")
        if os.path.exists(excel_file_path):
            excel_data = {}
            with pd.ExcelFile(excel_file_path) as xls:
                for sheet_name in xls.sheet_names:
                    excel_data[sheet_name] = pd.read_excel(excel_file_path, sheet_name=sheet_name)
            return excel_data
        else:
            st.warning(f"Excel file 'May'25 Revenue.xlsx' not found")
            return None
    except Exception as e:
        st.error(f"Error loading May 2025 Excel file: {e}")
        return None

def fetch_hubspot_tickets(api_key):
    """Fetch tickets from HubSpot API"""
    try:
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        url = "https://api.hubapi.com/crm/v3/objects/tickets"
        params = {
            'properties': [
                'subject', 'content', 'hs_ticket_priority', 'hs_pipeline_stage',
                'hs_ticket_category', 'source_type', 'createdate', 'hs_lastmodifieddate',
                'hubspot_owner_id', 'hs_resolution'
            ],
            'limit': 100
        }
        
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            tickets = []
            
            for ticket in data.get('results', []):
                properties = ticket.get('properties', {})
                tickets.append({
                    'Ticket ID': ticket.get('id'),
                    'Subject': properties.get('subject', ''),
                    'Content': properties.get('content', ''),
                    'Priority': properties.get('hs_ticket_priority', ''),
                    'Status': properties.get('hs_pipeline_stage', ''),
                    'Category': properties.get('hs_ticket_category', ''),
                    'Source': properties.get('source_type', ''),
                    'Created Date': properties.get('createdate', ''),
                    'Last Modified': properties.get('hs_lastmodifieddate', ''),
                    'Owner ID': properties.get('hubspot_owner_id', ''),
                    'Resolution': properties.get('hs_resolution', '')
                })
            
            df = pd.DataFrame(tickets)
            
            # Convert date columns
            for date_col in ['Created Date', 'Last Modified']:
                if date_col in df.columns:
                    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
            
            return df
        else:
            st.error(f"Failed to fetch HubSpot data: {response.status_code}")
            return pd.DataFrame()
            
    except Exception as e:
        st.error(f"Error fetching HubSpot tickets: {str(e)}")
        return pd.DataFrame()

def load_data_by_page(page):
    """Load data based on selected page"""
    df = pd.DataFrame()
    
    data_source = st.radio("Choose data source:", ("Use Google Sheets Data", "Upload File", "Enter URL", "Use Default File"))
    
    with st.container():
        if data_source == "Use Google Sheets Data":
            df = load_from_google_sheets(page)
        elif data_source == "Upload File":
            df = load_from_upload()
        elif data_source == "Enter URL":
            df = load_from_url()
        elif data_source == "Use Default File":
            df = load_from_default_file(page)
    
    return df

def load_from_google_sheets(page):
    """Load data from Google Sheets based on page"""
    if page == "Projects & Customer Health":
        return load_ops_review_data()
    elif page == "Support Tickets":
        return load_tickets_data()
    elif page == "Revenue":
        return load_revenue_data()
    else:
        return load_ops_review_data()  # Default

def load_ops_review_data():
    """Load Projects & Customer Health data"""
    with st.spinner("Loading Projects & Customer Health data from Google Sheets..."):
        ops_url = DATA_SOURCES["ops_review"]["url"]
        try:
            df_loaded = read_data_from_url(ops_url)
            if df_loaded is not None and not df_loaded.empty:
                required_ops_columns = ["Exective", "Project Status (R/G/Y)"]
                has_ops_columns = all(col in df_loaded.columns for col in required_ops_columns)
                
                if has_ops_columns:
                    st.success("✅ Projects & Customer Health data loaded successfully!")
                    st.info("🔗 Data source: [Master Tab - Google Sheets](https://docs.google.com/spreadsheets/d/1Nxvj1LRWYIw3cQcX2Qz9RJmvv17JlCe-V8G2tmvqHfE/edit#gid=0)")
                    return df_loaded
                else:
                    st.warning("⚠️ Google Sheets Master tab doesn't have expected structure. Loading local Data1.csv instead...")
                    return load_local_fallback("Data1.csv")
            else:
                st.error("Empty data returned from Google Sheets.")
                return pd.DataFrame()
        except Exception as e:
            st.error(f"Error loading data from Google Sheets: {e}")
            return pd.DataFrame()

def load_tickets_data():
    """Load Support Tickets data"""
    # Try HubSpot first
    if 'hubspot_api_key' in st.session_state and st.session_state.hubspot_api_key:
        with st.spinner("Loading Support Tickets data from HubSpot..."):
            try:
                df_loaded = fetch_hubspot_tickets(st.session_state.hubspot_api_key)
                if not df_loaded.empty:
                    st.success(f"✅ {len(df_loaded)} support tickets loaded from HubSpot!")
                    return df_loaded
                else:
                    st.warning("No tickets found in HubSpot. Falling back to Google Sheets...")
            except Exception as e:
                st.error(f"Error loading from HubSpot: {e}")
    
    # Fallback to Google Sheets
    with st.spinner("Loading Support Tickets data from Google Sheets..."):
        tickets_url = DATA_SOURCES["tickets"]["url"]
        try:
            df_loaded = read_data_from_url(tickets_url)
            if df_loaded is not None and not df_loaded.empty:
                st.success("✅ Tickets data loaded from Google Sheets!")
                return df_loaded
            else:
                st.error("Empty data returned from Google Sheets Tickets tab.")
                return pd.DataFrame()
        except Exception as e:
            st.error(f"Error loading tickets data: {e}")
            return pd.DataFrame()

def load_revenue_data():
    """Load Revenue data from Google Sheets Revenue tab"""
    with st.spinner("Loading Revenue data from Google Sheets..."):
        revenue_url = DATA_SOURCES["revenue"]["url"]  # Using revenue source which points to Revenue tab
        try:
            df_loaded = read_data_from_url(revenue_url)
            if df_loaded is not None and not df_loaded.empty:
                # Check if it has revenue-like columns
                revenue_columns = ["Current ARR", "Contracted ARR", "Recognized ARR", "Services Revenue", "Customer Name"]
                has_revenue_columns = any(col in df_loaded.columns for col in revenue_columns)
                
                if has_revenue_columns:
                    st.success("✅ Revenue data loaded from Google Sheets Revenue tab!")
                    st.info("🔗 Data source: [Revenue Tab - Google Sheets](https://docs.google.com/spreadsheets/d/1Nxvj1LRWYIw3cQcX2Qz9RJmvv17JlCe-V8G2tmvqHfE/edit#gid=2)")
                    return df_loaded
                else:
                    st.warning("⚠️ Google Sheets Revenue tab doesn't have expected revenue structure. Loading local Revenue.csv instead...")
                    return load_local_revenue_fallback()
            else:
                st.error("Empty data returned from Google Sheets Revenue tab.")
                return load_local_revenue_fallback()
        except Exception as e:
            st.error(f"Error loading revenue data from Google Sheets: {e}")
            return load_local_revenue_fallback()

def load_local_revenue_fallback():
    """Load local Revenue.csv as fallback"""
    data_file_path = os.path.join(os.path.dirname(__file__), "..", "Revenue.csv")
    if os.path.exists(data_file_path):
        df = pd.read_csv(data_file_path)
        st.success("✅ Revenue.csv loaded successfully!")
        return df
    else:
        st.error("❌ File 'Revenue.csv' not found.")
        return pd.DataFrame()

def load_from_upload():
    """Load data from file upload"""
    uploaded_file = st.file_uploader("Choose a CSV or Excel file", type=["csv", "xlsx"])
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                try:
                    df = pd.read_csv(uploaded_file)
                except UnicodeDecodeError:
                    df = pd.read_csv(uploaded_file, encoding='latin1')
            else:
                df = pd.read_excel(uploaded_file)
            
            # Convert date columns
            for date_col in ["Contract Start Date", "Contract End Date", "Project Start Date"]:
                if date_col in df.columns:
                    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
            
            st.success("File uploaded successfully!")
            return df
        except Exception as e:
            st.error(f"Error: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

def load_from_url():
    """Load data from URL"""
    data_url = st.text_input("Enter URL for CSV or Excel data:")
    if st.button("Load Data"):
        if data_url:
            with st.spinner("Loading data from URL..."):
                df_loaded = read_data_from_url(data_url)
                if df_loaded is not None and not df_loaded.empty:
                    st.success("Data loaded successfully!")
                    return df_loaded
                else:
                    st.error("Empty data returned from URL.")
                    return pd.DataFrame()
        else:
            st.warning("Please enter a valid URL.")
    return pd.DataFrame()

def load_from_default_file(page):
    """Load data from default local files"""
    with st.spinner("Loading default sample data..."):
        try:
            if page == "Projects & Customer Health":
                return load_local_fallback("Data1.csv")
            elif page == "Support Tickets":
                return load_local_fallback("Tickets.csv", fallback="Data1.csv")
            elif page == "Revenue":
                return load_local_fallback("Revenue.csv")
            else:
                return load_local_fallback("Data1.csv")
        except Exception as e:
            st.error(f"❌ Error loading CSV file: {e}")
            return pd.DataFrame()

def load_local_fallback(filename, fallback=None):
    """Load local CSV file with optional fallback"""
    file_path = os.path.join(os.path.dirname(__file__), "..", filename)
    if os.path.exists(file_path):
        df = pd.read_csv(file_path)
        # Convert date columns
        for date_col in ["Contract Start Date", "Contract End Date", "Project Start Date"]:
            if date_col in df.columns:
                df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
        st.success(f"✅ {filename} loaded successfully!")
        return df
    elif fallback:
        st.info(f"📋 {filename} not found, loading {fallback} instead.")
        return load_local_fallback(fallback)
    else:
        st.error(f"❌ File '{filename}' not found.")
        return pd.DataFrame()

def apply_filters(df):
    """Apply sidebar filters to dataframe"""
    if df.empty:
        return df
    
    df_filtered = df.copy()
    
    # Clean column names
    df_filtered.columns = df_filtered.columns.str.strip().str.replace('ï»¿', '', regex=False)
    
    # Convert date columns
    for col in ["Contract Start Date", "Contract End Date", "Project Start Date"]:
        if col in df_filtered.columns:
            df_filtered[col] = pd.to_datetime(df_filtered[col], errors='coerce')
    
    # Ensure string columns for filters
    for col in ["Exective", "Owner", "Project Status (R/G/Y)", "Status (R/G/Y)", "Churn", "Customer Name", "Geography", "Application", "Customer Health"]:
        if col in df_filtered.columns:
            df_filtered[col] = df_filtered[col].astype(str).str.strip().fillna("Unknown")
    
    # Ensure numeric columns
    for col in ["Revenue", "NRR", "GRR", "Total Usecases/Module", "Services Revenue"]:
        if col in df_filtered.columns:
            df_filtered[col] = pd.to_numeric(df_filtered[col], errors='coerce').fillna(0)
    
    st.sidebar.subheader("Filter Data")
    
    # Customer filter
    if "Customer Name" in df_filtered.columns:
        customers = sorted(df_filtered["Customer Name"].unique())
        cust_filter = st.sidebar.multiselect("Filter by Customer Name", options=customers, default=[])
        if cust_filter:
            df_filtered = df_filtered[df_filtered["Customer Name"].isin(cust_filter)]
    
    # Executive/Owner filter
    exec_col = "Exective" if "Exective" in df_filtered.columns else "Owner" if "Owner" in df_filtered.columns else None
    if exec_col:
        executives = sorted(df_filtered[exec_col].unique())
        exec_filter = st.sidebar.multiselect(f"Filter by {exec_col}", options=executives, default=[])
        if exec_filter:
            df_filtered = df_filtered[df_filtered[exec_col].isin(exec_filter)]
    
    # Status filter
    status_col = "Project Status (R/G/Y)" if "Project Status (R/G/Y)" in df_filtered.columns else "Status (R/G/Y)" if "Status (R/G/Y)" in df_filtered.columns else None
    if status_col:
        status_unique = sorted(df_filtered[status_col].unique())
        status_filter = st.sidebar.multiselect("Filter by Status", options=status_unique, default=[])
        if status_filter:
            df_filtered = df_filtered[df_filtered[status_col].isin(status_filter)]
    
    # Customer Health filter
    health_filter_col = None
    for col in df_filtered.columns:
        if "customer health" in col.lower():
            health_filter_col = col
            break
    
    if health_filter_col:
        health_options = ["Green", "Yellow", "Red"]
        available_health = [h for h in health_options if h in df_filtered[health_filter_col].unique()]
        if available_health:
            health_filter = st.sidebar.multiselect("Filter by Customer Health", options=available_health, default=[])
            if health_filter:
                df_filtered = df_filtered[df_filtered[health_filter_col].isin(health_filter)]
    
    # Date filters
    if "Project Start Date" in df_filtered.columns and not df_filtered["Project Start Date"].isnull().all():
        proj_min_date = df_filtered["Project Start Date"].min()
        proj_max_date = df_filtered["Project Start Date"].max()
        st.sidebar.subheader("📅 Filter by Project Start Date")
        if not (pd.isna(proj_min_date) or pd.isna(proj_max_date)):
            proj_start_date = st.sidebar.date_input("Project Start From", proj_min_date, min_value=proj_min_date, max_value=proj_max_date)
            proj_end_date = st.sidebar.date_input("Project Start To", proj_max_date, min_value=proj_min_date, max_value=proj_max_date)
            if proj_start_date <= proj_end_date:
                df_filtered = df_filtered[(df_filtered["Project Start Date"] >= pd.to_datetime(proj_start_date)) & 
                                        (df_filtered["Project Start Date"] <= pd.to_datetime(proj_end_date))].copy()
    
    if "Contract End Date" in df_filtered.columns and not df_filtered["Contract End Date"].isnull().all():
        min_date_val = df_filtered["Contract End Date"].min()
        max_date_val = df_filtered["Contract End Date"].max()
        st.sidebar.subheader("📌 Filter by Contract End Date")
        if not (pd.isna(min_date_val) or pd.isna(max_date_val)):
            start_date = st.sidebar.date_input("End Date From", min_date_val, min_value=min_date_val, max_value=max_date_val)
            end_date = st.sidebar.date_input("End Date To", max_date_val, min_value=min_date_val, max_value=max_date_val)
            if start_date <= end_date:
                df_filtered = df_filtered[(df_filtered["Contract End Date"] >= pd.to_datetime(start_date)) & 
                                          (df_filtered["Contract End Date"] <= pd.to_datetime(end_date))].copy()
    
    return df_filtered

def load_data(data_source, page):
    """Load data based on source and page selection"""
    df = pd.DataFrame()
    
    with st.container():
        if data_source == "Use Google Sheets Data":
            df = load_from_google_sheets(page)
        elif data_source == "Upload File":
            df = load_from_upload()
        elif data_source == "Enter URL":
            df = load_from_url()
        elif data_source == "Use Default File":
            df = load_from_default_file(page)
    
    # Create filtered copy
    df_filtered = df.copy()
    
    # Handle special case for Projects & Customer Health page
    if page == "Projects & Customer Health" and not df_filtered.empty:
        df_filtered = ensure_ops_review_structure(df_filtered)
    
    return df, df_filtered

def ensure_ops_review_structure(df):
    """Ensure the dataframe has the expected Ops Review structure"""
    required_ops_columns = ["Exective", "Project Status (R/G/Y)"]
    has_ops_columns = all(col in df.columns for col in required_ops_columns)
    
    if not has_ops_columns:
        st.warning("⚠️ Current data doesn't have Ops Review structure. Loading Data1.csv specifically...")
        try:
            fallback_df = load_local_fallback("Data1.csv")
            if not fallback_df.empty:
                st.success("✅ Data1.csv loaded specifically for Projects & Customer Health!")
                return fallback_df
            else:
                st.error("❌ Could not find Data1.csv file.")
        except Exception as e:
            st.error(f"❌ Error loading Data1.csv: {e}")
    
    return df

def load_and_filter_data(page):
    """Main function to load and filter data (legacy function for compatibility)"""
    df = load_data_by_page(page)
    
    # Special handling for Ops Review page
    if page == "Projects & Customer Health" and not df.empty:
        df = ensure_ops_review_structure(df)
    
    df_filtered = apply_filters(df)
    
    return df, df_filtered 