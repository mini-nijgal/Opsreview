import streamlit as st
import plotly.express as px
import pandas as pd
import warnings
import base64
import os
import streamlit.components.v1 as components
import re # For simple Q&A parsing
import random
import string
import requests
import io
from datetime import datetime
from office365.runtime.auth.authentication_context import AuthenticationContext
from office365.sharepoint.client_context import ClientContext
from office365.sharepoint.files.file import File
import PyPDF2
import tempfile

warnings.filterwarnings('ignore')

# ------------------ CONFIG ------------------
st.set_page_config(page_title="Avathon Analytics Dashboard", page_icon="📊", layout="wide")

# --- SharePoint Authentication ---
def get_sharepoint_file(url, username=None, password=None):
    """Get file content from SharePoint URL"""
    if username is None and password is None:
        if 'sharepoint_username' in st.session_state and 'sharepoint_password' in st.session_state:
            username = st.session_state.sharepoint_username
            password = st.session_state.sharepoint_password
        else:
            return None
    repos = ""
    try:
        # Extract the SharePoint site and document info
        # Parse the URL to get site URL and relative path
        url_parts = url.split('/')
        
        # Get the site URL (includes domain and site name)
        site_url = f"{url_parts[0]}//{url_parts[2]}"
        
        # Check if it's a sites URL
        if '/sites/' in url:
            site_name = url.split('/sites/')[1].split('/')[0]
            site_url = f"{site_url}/sites/{site_name}"
            
            # Get the relative path (everything after the site name)
            relative_url_parts = url.split(f"/sites/{site_name}/")[1]
            relative_path = f"/sites/{site_name}/{relative_url_parts}"
        else:
            st.error(f"URL format not recognized: {url}")
            st.info("URL should be in format: https://domain.sharepoint.com/sites/sitename/path/to/document")
            return None
            
        # Create authentication context
        auth_context = AuthenticationContext(site_url)
        auth_context.acquire_token_for_user(username, password)
        ctx = ClientContext(site_url, auth_context)
        
        # For debugging
        st.info(f"Connecting to SharePoint site: {site_url}")
        st.info(f"Accessing relative path: {relative_path}")
        
        # Try to access the file
        response = File.open_binary(ctx, relative_path)
        repos = response.content
        st.info(f"Response: {response.content}")
        return response.content
            
    except Exception as e:
        st.error(f"Error accessing SharePoint file: {str(e)}")
        # Add extra debugging info
        if "Cannot get binary security token" in str(e):
            st.warning("Authentication error. This may be due to incorrect credentials or modern authentication requirements.")
            st.info("Try using an app password if your account uses multi-factor authentication.")
            st.info(f"Response: {repos}")
        return None

# Function to read Excel file from SharePoint with sheet specification
def read_excel_from_sharepoint(url, sheet_name=None):
    # Get file content from SharePoint
    file_content = get_sharepoint_file(url)
    
    if file_content is None:
        # If authentication hasn't happened yet, return empty DataFrame
        return pd.DataFrame()
    
    # Read Excel file
    try:
        if sheet_name:
            return pd.read_excel(io.BytesIO(file_content), sheet_name=sheet_name)
        else:
            return pd.read_excel(io.BytesIO(file_content))
    except Exception as e:
        st.error(f"Error reading Excel file: {str(e)}")
        return pd.DataFrame()

# Function to get PDF from SharePoint
def get_pdf_from_sharepoint(url):
    file_content = get_sharepoint_file(url)
    
    if file_content is None:
        return None
    
    return file_content

# --- App Navigation ---
st.sidebar.title("Navigation")
page = st.sidebar.selectbox(
    "Go to",
    ("Ops Review", "Tickets", "Finance", "Chat Analytics")
)

# --- Initialize session state for chat ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- Authentication UI ---
# Keep the authentication section in case SharePoint is needed, but make it optional
with st.sidebar.expander("SharePoint Authentication (Optional)", expanded=False):
    st.write("Only needed if using SharePoint data sources")
    username = st.text_input("Username (email)", 
                             value=st.session_state.get('sharepoint_username', ''),
                             key="username_input")
    password = st.text_input("Password", 
                             value=st.session_state.get('sharepoint_password', ''),
                             type="password",
                             key="password_input")
    
    if st.button("Authenticate"):
        # Store credentials in session state
        st.session_state.sharepoint_username = username
        st.session_state.sharepoint_password = password
        st.success("Credentials saved for this session")
    
    # Help section for SharePoint URLs
    st.markdown("### About Data Sources")
    st.markdown("""
    The dashboard now primarily uses Google Sheets for data.
    SharePoint authentication is only needed if you switch back to SharePoint data sources.
    """)


# ------------------ DATA SELECTION ------------------
def read_data_from_url(url):
    try:
        # Try different encodings
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

# Define the data sources for different views
DATA_SOURCES = {
    "ops_review": {
        "url": "https://raw.githubusercontent.com/sparkcognition/sample-data/main/ops_review_data.csv",
        "sheet": "Data1"
    },
    "finance": {
        "url": "https://raw.githubusercontent.com/sparkcognition/sample-data/main/finance_data.csv", 
        "sheet": "Revenue"
    },
    "tickets": {
        "url": "https://raw.githubusercontent.com/sparkcognition/sample-data/main/tickets_data.csv",
        "sheet": "Tickets"
    },
    "weekly_status_pdf": {
        "url": "https://github.com/sparkcognition/sample-data/raw/main/weekly_status.pdf"
    }
}

data_source = st.radio("Choose data source:", ("Use Google Sheets Data", "Upload File", "Enter URL", "Use Default File"))
# Initialize df as None or an empty DataFrame
df = pd.DataFrame() # Initialize as empty DataFrame

with st.container():
    if data_source == "Use Google Sheets Data":
        # Load data based on the selected page
        if page == "Ops Review":
            with st.spinner("Loading Ops Review data from Google Sheets..."):
                ops_url = DATA_SOURCES["ops_review"]["url"]
                try:
                    # Try different encodings
                    try:
                        df_loaded = pd.read_csv(ops_url)
                    except UnicodeDecodeError:
                        df_loaded = pd.read_csv(ops_url, encoding='latin1')
                    
                    if not df_loaded.empty:
                        # Verify this data has Ops Review structure
                        required_ops_columns = ["Exective", "Project Status (R/G/Y)"]
                        has_ops_columns = all(col in df_loaded.columns for col in required_ops_columns)
                        
                        if has_ops_columns:
                            df = df_loaded
                            # Convert date columns if they exist
                            for date_col in ["Contract Start Date", "Contract End Date", "Project Start Date"]:
                                if date_col in df.columns:
                                    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
                            st.success(f"✅ Ops Review data loaded successfully from Google Sheets!")
                        else:
                            st.warning("⚠️ Google Sheets data doesn't have Ops Review structure. Loading local Data1.csv instead...")
                            # Fallback to local Data1.csv
                            try:
                                data_file_path = os.path.join(os.path.dirname(__file__), "Data1.csv")
                                if os.path.exists(data_file_path):
                                    df = pd.read_csv(data_file_path)
                                    for date_col in ["Contract Start Date", "Contract End Date", "Project Start Date"]:
                                        if date_col in df.columns:
                                            df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
                                    st.info("✅ Loaded Data1.csv as fallback for Ops Review.")
                                else:
                                    df = df_loaded  # Use whatever we got from Google Sheets
                                    st.warning("Could not find local Data1.csv, using Google Sheets data anyway.")
                            except Exception as fallback_error:
                                st.error(f"Fallback failed: {fallback_error}")
                                df = df_loaded
                    else:
                        st.error("Empty data returned from Google Sheets.")
                except Exception as e:
                    st.error(f"Error loading data from Google Sheets: {e}")
                    st.info("Try using the 'Use Default File' option if external data sources are not available.")
        elif page == "Finance":
            with st.spinner("Loading Finance data from Google Sheets..."):
                finance_url = DATA_SOURCES["finance"]["url"]
                try:
                    # Try different encodings
                    try:
                        df_loaded = pd.read_csv(finance_url)
                    except UnicodeDecodeError:
                        df_loaded = pd.read_csv(finance_url, encoding='latin1')
                    
                    if not df_loaded.empty:
                        df = df_loaded
                        # Convert date columns if they exist
                        for date_col in ["Contract Start Date", "Contract End Date", "Project Start Date"]:
                            if date_col in df.columns:
                                df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
                        st.success(f"Data loaded successfully for {page}!")
                    else:
                        st.error("Empty data returned from Google Sheets.")
                except Exception as e:
                    st.error(f"Error loading data from Google Sheets: {e}")
                    st.info("Try using the 'Use Default File' option if external data sources are not available.")
        elif page == "Tickets":
            with st.spinner("Loading Tickets data from Google Sheets..."):
                tickets_url = DATA_SOURCES["tickets"]["url"]
                try:
                    # Try different encodings
                    try:
                        df_loaded = pd.read_csv(tickets_url)
                    except UnicodeDecodeError:
                        df_loaded = pd.read_csv(tickets_url, encoding='latin1')
                    
                    if not df_loaded.empty:
                        df = df_loaded
                        # Convert date columns if they exist
                        for date_col in ["Contract Start Date", "Contract End Date", "Project Start Date"]:
                            if date_col in df.columns:
                                df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
                        st.success(f"Data loaded successfully for {page}!")
                    else:
                        st.error("Empty data returned from Google Sheets.")
                except Exception as e:
                    st.error(f"Error loading data from Google Sheets: {e}")
                    st.info("Try using the 'Use Default File' option if external data sources are not available.")
        else:
            # Default to Ops Review data for Chat Analytics
            with st.spinner("Loading data from Google Sheets..."):
                ops_url = DATA_SOURCES["ops_review"]["url"]
                try:
                    # Try different encodings
                    try:
                        df_loaded = pd.read_csv(ops_url)
                    except UnicodeDecodeError:
                        df_loaded = pd.read_csv(ops_url, encoding='latin1')
                    
                    if not df_loaded.empty:
                        df = df_loaded
                        # Convert date columns if they exist
                        for date_col in ["Contract Start Date", "Contract End Date", "Project Start Date"]:
                            if date_col in df.columns:
                                df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
                        st.success("Data loaded successfully!")
                    else:
                        st.error("Empty data returned from Google Sheets.")
                except Exception as e:
                    st.error(f"Error loading data from Google Sheets: {e}")
                    st.info("Try using the 'Use Default File' option if external data sources are not available.")
    elif data_source == "Upload File":
        uploaded_file = st.file_uploader("Choose a CSV or Excel file", type=["csv", "xlsx"])
        if uploaded_file is not None:
            try:
                if uploaded_file.name.endswith('.csv'):
                    # Try different encodings
                    try:
                        df = pd.read_csv(uploaded_file)
                    except UnicodeDecodeError:
                        # If UTF-8 fails, try other encodings
                        df = pd.read_csv(uploaded_file, encoding='latin1')
                else:
                    df = pd.read_excel(uploaded_file)
                
                # Convert date columns if they exist
                for date_col in ["Contract Start Date", "Contract End Date", "Project Start Date"]:
                    if date_col in df.columns:
                        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
                
                st.success("File uploaded successfully!")
            except Exception as e:
                st.error(f"Error: {e}")
                st.info("If you're seeing encoding errors, try saving your CSV file with UTF-8 encoding.")
    elif data_source == "Enter URL":
        data_url = st.text_input("Enter URL for CSV or Excel data:")
        if st.button("Load Data"):
            if data_url:
                with st.spinner("Loading data from URL..."):
                    try:
                        df_loaded = read_data_from_url(data_url)
                        if df_loaded is not None and not df_loaded.empty:
                            df = df_loaded
                            st.success("Data loaded successfully!")
                        else:
                            st.error("Empty data returned from URL.")
                    except Exception as e:
                        st.error(f"Error loading data from URL: {e}")
                        st.info("If you're seeing encoding errors, try a different URL or use the Upload File option.")
            else:
                st.warning("Please enter a valid URL.")
    elif data_source == "Use Default File":
        # Load default sample data from specific CSV files
        with st.spinner("Loading default sample data..."):
            try:
                if page == "Ops Review":
                    data_file_path = os.path.join(os.path.dirname(__file__), "Data1.csv")
                    if os.path.exists(data_file_path):
                        df = pd.read_csv(data_file_path)
                        st.success("✅ Data1.csv loaded successfully for Ops Review!")
                    else:
                        st.error(f"❌ File 'Data1.csv' not found in {os.path.dirname(__file__)}.")
                        st.info("Please ensure Data1.csv is in the same directory as the dashboard.py file.")
                elif page == "Finance":
                    data_file_path = os.path.join(os.path.dirname(__file__), "Revenue.csv")
                    if os.path.exists(data_file_path):
                        df = pd.read_csv(data_file_path)
                        st.success("✅ Revenue.csv loaded successfully for Finance!")
                    else:
                        st.error(f"❌ File 'Revenue.csv' not found in {os.path.dirname(__file__)}.")
                        st.info("Please ensure Revenue.csv is in the same directory as the dashboard.py file.")
                elif page == "Tickets":
                    # Look for Tickets.csv, fallback to Data1.csv
                    tickets_file_path = os.path.join(os.path.dirname(__file__), "Tickets.csv")
                    if os.path.exists(tickets_file_path):
                        df = pd.read_csv(tickets_file_path)
                        st.success("✅ Tickets.csv loaded successfully!")
                    else:
                        # Fallback to Data1.csv for tickets
                        data_file_path = os.path.join(os.path.dirname(__file__), "Data1.csv")
                        if os.path.exists(data_file_path):
                            df = pd.read_csv(data_file_path)
                            st.info("📋 Data1.csv loaded for Tickets page (Tickets.csv not found).")
                        else:
                            st.error(f"❌ Neither 'Tickets.csv' nor 'Data1.csv' found in {os.path.dirname(__file__)}.")
                else:
                    # Default to Data1.csv for Chat Analytics and other pages
                    data_file_path = os.path.join(os.path.dirname(__file__), "Data1.csv")
                    if os.path.exists(data_file_path):
                        df = pd.read_csv(data_file_path)
                        st.success("✅ Data1.csv loaded successfully!")
                    else:
                        st.error(f"❌ File 'Data1.csv' not found in {os.path.dirname(__file__)}.")
                        st.info("Please ensure Data1.csv is in the same directory as the dashboard.py file.")
                
                # Convert date columns if they exist (only if df was successfully loaded)
                if not df.empty:
                    for date_col in ["Contract Start Date", "Contract End Date", "Project Start Date"]:
                        if date_col in df.columns:
                            df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
                            
            except Exception as e:
                st.error(f"❌ Error loading CSV file: {e}")
    # We don't need the elif statement here as the Chat Analytics page uses the data loaded by other options

# Create a copy for filtering, so the original df remains for the chat
df_filtered = df.copy()

# Special handling for Ops Review page - ensure we're using Data1 tab structure
if page == "Ops Review" and not df_filtered.empty:
    # Check if we have the expected Ops Review columns (Data1 tab structure)
    required_ops_columns = ["Exective", "Project Status (R/G/Y)"]
    has_ops_columns = all(col in df_filtered.columns for col in required_ops_columns)
    
    if not has_ops_columns:
        st.warning("⚠️ Current data doesn't have Ops Review structure. Loading Data1.csv specifically...")
        try:
            data_file_path = os.path.join(os.path.dirname(__file__), "Data1.csv")
            if os.path.exists(data_file_path):
                df_ops = pd.read_csv(data_file_path)
                # Convert date columns if they exist
                for date_col in ["Contract Start Date", "Contract End Date", "Project Start Date"]:
                    if date_col in df_ops.columns:
                        df_ops[date_col] = pd.to_datetime(df_ops[date_col], errors='coerce')
                
                df = df_ops.copy()
                df_filtered = df_ops.copy()
                st.success("✅ Data1.csv loaded specifically for Ops Review!")
            else:
                st.error("❌ Could not find Data1.csv file.")
        except Exception as e:
            st.error(f"❌ Error loading Data1.csv: {e}")

# ------------------ FILTERS ------------------
if not df_filtered.empty:
    df_filtered.columns = df_filtered.columns.str.strip().str.replace('ï»¿', '', regex=False)

    for col in ["Contract Start Date", "Contract End Date", "Project Start Date"]:
        if col in df_filtered.columns:
            df_filtered[col] = pd.to_datetime(df_filtered[col], errors='coerce')
    # Ensure string columns for filters - handle both Data1 and Revenue tab column names
    for col in ["Exective", "Owner", "Project Status (R/G/Y)", "Status (R/G/Y)", "Churn", "Customer Name", "Geography", "Application", "Customer Health"]:
        if col in df_filtered.columns:
            df_filtered[col] = df_filtered[col].astype(str).str.strip().fillna("Unknown") # Fill NaN with 'Unknown' for str cols
    # Ensure numeric columns for calculations
    for col in ["Revenue", "NRR", "GRR", "Total Usecases/Module", "Services Revenue"]:
        if col in df_filtered.columns:
            df_filtered[col] = pd.to_numeric(df_filtered[col], errors='coerce').fillna(0)

    st.sidebar.subheader("Filter Data")
    if "Customer Name" in df_filtered.columns:
        customers = sorted(df_filtered["Customer Name"].unique())
        cust_filter = st.sidebar.multiselect("Filter by Customer Name", options=customers, default=[])
        if cust_filter:
            df_filtered = df_filtered[df_filtered["Customer Name"].isin(cust_filter)]

    # Executive/Owner filter - handle both column names
    exec_col = None
    if "Exective" in df_filtered.columns:
        exec_col = "Exective"
    elif "Owner" in df_filtered.columns:
        exec_col = "Owner"
        
    if exec_col:
        executives = sorted(df_filtered[exec_col].unique())
        exec_filter = st.sidebar.multiselect(f"Filter by {exec_col}", options=executives, default=[])
        if exec_filter:
            df_filtered = df_filtered[df_filtered[exec_col].isin(exec_filter)]
    
    # Status filter - handle both column names
    status_col = None
    if "Project Status (R/G/Y)" in df_filtered.columns:
        status_col = "Project Status (R/G/Y)"
    elif "Status (R/G/Y)" in df_filtered.columns:
        status_col = "Status (R/G/Y)"
        
    if status_col:
        status_unique = sorted(df_filtered[status_col].unique())
        status_filter = st.sidebar.multiselect("Filter by Status", options=status_unique, default=[])
        if status_filter:
            df_filtered = df_filtered[df_filtered[status_col].isin(status_filter)]

    # New Customer Health filter - handle different column name variations
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
    
    # Add Project Start Date filter
    if "Project Start Date" in df_filtered.columns and not df_filtered["Project Start Date"].isnull().all():
        proj_min_date = df_filtered["Project Start Date"].min()
        proj_max_date = df_filtered["Project Start Date"].max()
        st.sidebar.subheader("📅 Filter by Project Start Date")
        if pd.isna(proj_min_date) or pd.isna(proj_max_date):
            st.sidebar.warning("Not enough valid project start date data for range filter.")
        else:
            proj_start_date = st.sidebar.date_input("Project Start From", proj_min_date, min_value=proj_min_date, max_value=proj_max_date)
            proj_end_date = st.sidebar.date_input("Project Start To", proj_max_date, min_value=proj_min_date, max_value=proj_max_date)
            if proj_start_date <= proj_end_date:
                df_filtered = df_filtered[(df_filtered["Project Start Date"] >= pd.to_datetime(proj_start_date)) & 
                                        (df_filtered["Project Start Date"] <= pd.to_datetime(proj_end_date))].copy()
            else:
                st.sidebar.error("End date must be on or after start date.")

    # Contract date filter - Updated to use Contract End Date instead of Start Date
    if "Contract End Date" in df_filtered.columns and not df_filtered["Contract End Date"].isnull().all():
        min_date_val = df_filtered["Contract End Date"].min()
        max_date_val = df_filtered["Contract End Date"].max()
        st.sidebar.subheader("📌 Filter by Contract End Date")
        if pd.isna(min_date_val) or pd.isna(max_date_val):
            st.sidebar.warning("Not enough valid contract end date data for range filter.")
        else:
            start_date = st.sidebar.date_input("End Date From", min_date_val, min_value=min_date_val, max_value=max_date_val)
            end_date = st.sidebar.date_input("End Date To", max_date_val, min_value=min_date_val, max_value=max_date_val)
            if start_date <= end_date:
                df_filtered = df_filtered[(df_filtered["Contract End Date"] >= pd.to_datetime(start_date)) & 
                                          (df_filtered["Contract End Date"] <= pd.to_datetime(end_date))].copy()
            else:
                st.sidebar.error("End date must be on or after start date.")


# ------------------ CHAT PAGE HELPER FUNCTIONS ------------------
def display_faq(current_data):
    faq_items = {}
    if not current_data.empty:
        faq_items = {
            "What is the total revenue?": f"The total revenue in the current filtered data is ${current_data['Revenue'].sum():,.0f}." if 'Revenue' in current_data else "Revenue data not available.",
            "How many projects are there in total?": f"There are {current_data.shape[0]} projects in the current filtered data.",
            "Which executive has the most projects?": (f"The executive with the most projects is {current_data['Exective'].mode()[0]} with {current_data['Exective'].value_counts().max()} projects." if 'Exective' in current_data and not current_data['Exective'].dropna().empty else "Executive data not available or insufficient."),
            "What are the different project statuses?": (f"The project statuses are: {', '.join(current_data['Project Status (R/G/Y)'].unique())}." if 'Project Status (R/G/Y)' in current_data else "Project status data not available.")
        }
    else:
        faq_items["No data loaded"] = "Please load data to see relevant FAQs."

    st.subheader("Frequently Asked Questions")
    if not faq_items:
        st.write("Load data to see FAQs.")
        return
        
    for question, answer in faq_items.items():
        with st.expander(question):
            st.write(answer)

def analyze_data_for_chat(question, data):
    """
    Advanced data analysis function for chat responses.
    Handles various types of analytical questions about the data.
    """
    question_lower = question.lower().strip()
    
    # Generate a random unique ID for charts to prevent duplicates
    def generate_chart_id():
        return ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    
    try:
        # Initialize response components
        text_response = ""
        fig = None
        
        # Handle empty or invalid data
        if data.empty:
            return "I need data to answer questions. Please load or adjust filters on other pages.", None
            
        # Get available columns and their data types for dynamic analysis
        available_columns = list(data.columns)
        numeric_columns = data.select_dtypes(include=['int64', 'float64']).columns.tolist()
        categorical_columns = data.select_dtypes(include=['object', 'category']).columns.tolist()
        date_columns = data.select_dtypes(include=['datetime64']).columns.tolist()
        
        # Direct customer query handler - for queries like "Give summary statistics for Customer Name called Aramco"
        customer_query_match = re.search(r"(?:for|about|of)\s+(?:customer|client)(?:\s+name)?\s+(?:called|named)\s+([a-zA-Z0-9\s\-\.']+)", question_lower)
        
        if customer_query_match and "summary" in question_lower:
            customer_name = customer_query_match.group(1).strip()
            
            # Find customer column
            customer_cols = [col for col in categorical_columns if "customer" in col.lower()]
            if not customer_cols:
                return "No customer column found in the data.", None
                
            customer_col = customer_cols[0]
            
            # Find matching customer with partial matching
            matching_customer = None
            for val in data[customer_col].dropna().unique():
                if customer_name.lower() in str(val).lower():
                    matching_customer = val
                    break
            
            if matching_customer:
                # Filter data for this customer
                customer_data = data[data[customer_col] == matching_customer]
                
                if customer_data.empty:
                    return f"No data found for customer '{matching_customer}'.", None
                
                # Display basic stats
                chart_id = generate_chart_id()
                
                # Project count
                project_count = len(customer_data)
                
                # Important stats
                stats_text = f"**Customer: {matching_customer}**\n\nTotal projects: {project_count}\n\n"
                
                # Get status breakdown if available
                status_cols = [col for col in categorical_columns if "status" in col.lower()]
                if status_cols:
                    status_col = status_cols[0]
                    status_counts = customer_data[status_col].value_counts()
                    if not status_counts.empty:
                        status_text = "\n".join([f"- {status}: {count}" for status, count in status_counts.items()])
                        stats_text += f"**Status breakdown:**\n{status_text}\n\n"
                
                # Get revenue stats if available
                revenue_cols = [col for col in numeric_columns if "revenue" in col.lower()]
                if revenue_cols:
                    revenue_col = revenue_cols[0]
                    total_revenue = customer_data[revenue_col].sum()
                    stats_text += f"**Total revenue:** ${total_revenue:,.2f}\n\n"
                
                # Create a table of all projects
                important_cols = []
                for term in ["status", "revenue", "date", "executive", "exective"]:
                    matched_cols = [col for col in available_columns if term.lower() in col.lower()]
                    important_cols.extend(matched_cols)
                
                if important_cols:
                    stats_text += f"**Project details:**\n```\n{customer_data[important_cols].to_string(index=False)}\n```"
                
                # Create a visualization
                fig = None
                if status_cols:
                    status_col = status_cols[0]
                    status_counts = customer_data[status_col].value_counts()
                    
                    if not status_counts.empty:
                        # Create a pie chart with status colors
                        status_color_map = {
                            "Red": "#d62728", "R": "#d62728", "Amber": "#ff7f0e", 
                            "Yellow": "#ffdd57", "Y": "#ff7f0e", "Green": "#2ca02c", 
                            "G": "#2ca02c", "Blank": "#cccccc", "<NA>": "#cccccc", "Unknown": "#cccccc"
                        }
                        
                        fig = px.pie(
                            values=status_counts.values, 
                            names=status_counts.index, 
                            title=f"Project Status for {matching_customer}",
                            color=status_counts.index,
                            color_discrete_map=status_color_map
                        )
                        # Add a unique ID to prevent duplicate charts
                        fig.update_layout(uirevision=chart_id)
                
                return stats_text, fig
            else:
                similar_customers = []
                for val in data[customer_col].dropna().unique():
                    if any(word in str(val).lower() for word in customer_name.lower().split()):
                        similar_customers.append(val)
                
                if similar_customers:
                    suggestions = "\n- ".join(similar_customers[:5])
                    return f"I couldn't find a customer named '{customer_name}'. Did you mean one of these?\n\n- {suggestions}", None
                else:
                    return f"I couldn't find a customer named '{customer_name}' in the data.", None
        
        # DIRECT STATUS COUNT - highest priority handler for counting by status
        # This will handle the specific "how many projects have project status as X" type questions with direct count
        if re.search(r"how many projects (?:have|are)(?: project)? status(?: as| is| =)? (red|green|yellow|amber|r\b|g\b|y\b|a\b)", question_lower) or \
           re.search(r"(count|number of) projects (?:with|having)(?: project)? status(?: as| is| =)? (red|green|yellow|amber|r\b|g\b|y\b|a\b)", question_lower):
            
            # Extract the exact color from the query to ensure we use the right one
            color_match = re.search(r"status(?:.*?)(red|green|yellow|amber|r\b|g\b|y\b|a\b)", question_lower)
            if not color_match:
                color_match = re.search(r"(red|green|yellow|amber|r\b|g\b|y\b|a\b)", question_lower)
            
            if color_match:
                status_color = color_match.group(1).lower().strip()
                
                # Find the status column
                status_cols = [col for col in categorical_columns if "status" in col.lower()]
                if not status_cols:
                    return "No status column found in the data.", None
                
                status_col = status_cols[0]
                
                # Map colors to possible values - using clear mapping
                if status_color in ["red", "r"]:
                    possible_values = ["Red", "R"]
                    display_color = "Red"
                elif status_color in ["green", "g"]:
                    possible_values = ["Green", "G"]
                    display_color = "Green"
                elif status_color in ["yellow", "y", "amber", "a"]:
                    possible_values = ["Yellow", "Y", "Amber", "A"]
                    display_color = "Yellow/Amber"
                else:
                    # If somehow we get here with an invalid color
                    return f"I'm not sure about status '{status_color}'. Please ask about Red, Green, or Yellow status.", None
                
                # Just count exact matches
                count = 0
                matched_values = []
                for val in possible_values:
                    val_count = data[data[status_col] == val].shape[0]
                    if val_count > 0:
                        count += val_count
                        matched_values.append(f"{val}: {val_count}")
                
                # Output the exact color that was asked about, not a hardcoded value
                response = f"**There are {count} projects with {display_color} status.**"
                
                # Add a debug section if needed (can be removed in final version)
                if len(matched_values) > 0:
                    response += f"\n\nBreakdown: {', '.join(matched_values)}"
                
                # Return a simple text answer with no chart
                return response, None
        
        # PROJECT LIST BY STATUS - list projects with a specific status
        project_status_patterns = [
            r"(?:which|what|list|show|display)(?:.+?)(?:projects|assignments|entries)(?:.+?)(?:have|has|with)(?:.+?)(?:status|state)(?:.+?)(?:as|is|=|:)(?:.+?)(red|green|yellow|amber|r\b|g\b|y\b|a\b)",
            r"(?:projects|assignments|entries)(?:.+?)(?:status|state)(?:.+?)(?:as|is|=|:)(?:.+?)(red|green|yellow|amber|r\b|g\b|y\b|a\b)"
        ]
        
        for pattern in project_status_patterns:
            match = re.search(pattern, question_lower)
        if match:
                status_color = match.group(1).lower().strip()
                
                # Find the status column
                status_cols = [col for col in categorical_columns if "status" in col.lower()]
                if not status_cols:
                    return "No status column found in the data.", None
                
                status_col = status_cols[0]
                
                # Map colors to possible values
                if status_color in ["red", "r"]:
                    possible_values = ["Red", "R"]
                    display_color = "Red"
                elif status_color in ["green", "g"]:
                    possible_values = ["Green", "G"]
                    display_color = "Green"
                elif status_color in ["yellow", "y", "amber", "a"]:
                    possible_values = ["Yellow", "Y", "Amber", "A"]
                    display_color = "Yellow/Amber"
                
                # Find projects with these status values
                filtered_data = pd.DataFrame()
                for val in possible_values:
                    # Try exact match first
                    temp_data = data[data[status_col] == val]
                    if not temp_data.empty:
                        filtered_data = pd.concat([filtered_data, temp_data])
                
                # Check if we found any projects
                if filtered_data.empty:
                    return f"No projects found with {display_color} status.", None
                
                # Select important columns to display
                important_cols = []
                for term in ["customer", "name", "project", "revenue", "date", "executive", "exective"]:
                    matched_cols = [col for col in available_columns if term.lower() in col.lower()]
                    important_cols.extend(matched_cols)
                    if len(important_cols) >= 5:  # Limit to most important 5 columns
                        break
                
                # Always include the status column if not already present
                if status_col not in important_cols:
                    important_cols.append(status_col)
                
                # Limit the number of rows to display
                display_limit = 15
                has_more = len(filtered_data) > display_limit
                limited_data = filtered_data.head(display_limit)
                
                # Create result table
                if important_cols:
                    result_table = limited_data[important_cols].to_string(index=False)
                else:
                    # If no columns were identified, use the first 5 columns
                    result_table = limited_data.iloc[:, :5].to_string(index=False)
                
                # Format the response message
                result_msg = f"**Found {len(filtered_data)} projects with {display_color} status.**"
                if has_more:
                    result_msg += f"\n\nShowing first {display_limit} projects:"
                else:
                    result_msg += "\n\nHere are all the projects:"
                
                result_msg += f"\n\n```\n{result_table}\n```"
                
                # Create visualization - bar chart of top customers with this status
                fig = None
                customer_cols = [col for col in categorical_columns if "customer" in col.lower()]
                
                if customer_cols and not filtered_data.empty:
                    customer_col = customer_cols[0]
                    customer_counts = filtered_data[customer_col].value_counts().head(10)
                    
                    if not customer_counts.empty:
                        if status_color in ["red", "r"]:
                            bar_color = "#d62728"
                        elif status_color in ["green", "g"]:
                            bar_color = "#2ca02c"
                        else:  # yellow/amber
                            bar_color = "#ff7f0e"
                            
                        fig = px.bar(
                            x=customer_counts.index,
                            y=customer_counts.values,
                            title=f"Customers with {display_color} Status Projects",
                            labels={"x": customer_col, "y": "Number of Projects"}
                        )
                        fig.update_traces(marker_color=bar_color)
                
                return result_msg, fig
        
        # ADVANCED ENTITY QUERY - handle questions about specific people, locations, and filters
        # This can handle queries like "projects assigned to Bhavana by location" or "project status of Bhavana"
        entity_patterns = [
            # Person's projects by location/grouping
            r"(?:what|tell|show|list|find)(?:.+?)(?:projects|assignments)(?:.+?)(assigned to|for|by|of)(?:.+?)([a-zA-Z\s]+?)(?:.*?)(by|grouped by|per|across)(?:.+?)([a-zA-Z\s]+)",
            # Person's project status
            r"(?:what|tell|show|list)(?:.+?)(project status|status|health|state)(?:.+?)(of|for|by)(?:.+?)([a-zA-Z\s]+)",
            # General query about a person
            r"(?:what|tell|show|list|find)(?:.+?)([a-zA-Z\s]+?)(?:'s|\s+has|\s+have)(?:.+?)(projects|assignments|status|revenue)"
        ]
        
        for pattern in entity_patterns:
            match = re.search(pattern, question_lower)
        if match:
                # Extract the person's name and other elements based on the pattern matches
                groups = match.groups()
                
                # Find the person's name (could be in different positions based on pattern)
                person_name = None
                for group in groups:
                    # Skip common words and short phrases that aren't likely to be names
                    if group and len(group.strip()) > 2 and group.strip() not in [
                        "assigned to", "for", "by", "of", "project status", "status", 
                        "health", "state", "projects", "assignments", "revenue",
                        "grouped by", "per", "across", "location", "geography"
                    ]:
                        person_name = group.strip()
                        break
                
                if not person_name:
                    return "I couldn't identify a person's name in your question. Please specify whose projects you're asking about.", None
                
                # Determine what attribute we're looking for
                looking_for_status = any(term in question_lower for term in ["status", "health", "state"])
                looking_for_location = any(term in question_lower for term in ["location", "geography", "region", "by location"])
                
                # Find relevant columns
                person_cols = []
                for col_type in ["executive", "exective", "person", "owner", "manager", "lead"]:
                    temp_cols = [col for col in categorical_columns if col_type in col.lower()]
                    person_cols.extend(temp_cols)
                
                if not person_cols:
                    return f"I couldn't find any columns in the data that might contain person names like '{person_name}'.", None
                
                # Find the person in the data
                person_data = None
                person_col_used = None
                
                for col in person_cols:
                    # Try to find the person with partial matching
                    for val in data[col].dropna().unique():
                        if person_name.lower() in str(val).lower() or str(val).lower() in person_name.lower():
                            person_data = data[data[col] == val].copy()
                            person_col_used = col
                            person_name = val  # Use the actual value from the data
                            break
                    if person_data is not None:
                        break
                
                if person_data is None or person_data.empty:
                    return f"I couldn't find anyone matching '{person_name}' in the data.", None
                
                # Process the query based on what the user is looking for
                if looking_for_status:
                    # Find status column
                    status_cols = [col for col in categorical_columns if "status" in col.lower()]
                    if not status_cols:
                        return f"I found {len(person_data)} projects for {person_name}, but there's no status information in the data.", None
                    
                    status_col = status_cols[0]
                    status_counts = person_data[status_col].value_counts()
                    
                    if status_counts.empty:
                        return f"I found {len(person_data)} projects for {person_name}, but they don't have any status values.", None
                    
                    # Create visualization
                    status_color_map = {
                        "Red": "#d62728", "R": "#d62728", "Amber": "#ff7f0e", 
                        "Yellow": "#ffdd57", "Y": "#ff7f0e", "Green": "#2ca02c", 
                        "G": "#2ca02c", "Blank": "#cccccc", "<NA>": "#cccccc", "Unknown": "#cccccc"
                    }
                    
                    fig = px.pie(
                        values=status_counts.values, 
                        names=status_counts.index, 
                        title=f"Project Status Distribution for {person_name}",
                        color=status_counts.index,
                        color_discrete_map=status_color_map
                    )
                    fig.update_traces(textinfo="percent+label")
                    
                    # Format response text
                    status_text = "\n".join([f"- {status}: {count}" for status, count in status_counts.items()])
                    response = f"**Project Status for {person_name}:**\n\nTotal projects: {len(person_data)}\n\n{status_text}"
                    
                    return response, fig
                
                elif looking_for_location:
                    # Find location/geography column
                    location_cols = [col for col in categorical_columns if any(term in col.lower() for term in ["location", "geography", "region", "geo"])]
                    
                    if not location_cols:
                        return f"I found {len(person_data)} projects for {person_name}, but there's no location/geography information in the data.", None
                    
                    location_col = location_cols[0]
                    location_counts = person_data[location_col].value_counts()
                    
                    if location_counts.empty:
                        return f"I found {len(person_data)} projects for {person_name}, but they don't have any location values.", None
                    
                    # Create a bar chart for locations
                    fig = px.bar(
                        x=location_counts.index,
                        y=location_counts.values,
                        title=f"Projects for {person_name} by {location_col}",
                        labels={"x": location_col, "y": "Number of Projects"}
                    )
                    
                    # Format response text
                    location_text = "\n".join([f"- {location}: {count}" for location, count in location_counts.items()])
                    response = f"**Projects for {person_name} by {location_col}:**\n\nTotal projects: {len(person_data)}\n\n{location_text}"
                    
                    return response, fig
                
                else:
                    # General information about the person's projects
                    important_cols = []
                    for term in ["customer", "name", "status", "revenue", "date", "location", "geography"]:
                        matched_cols = [col for col in available_columns if term.lower() in col.lower()]
                        important_cols.extend(matched_cols)
                    
                    # Limit columns to show
                    if len(important_cols) > 5:
                        important_cols = important_cols[:5]
                    
                    # Add the person column if not already included
                    if person_col_used not in important_cols:
                        important_cols.append(person_col_used)
                    
                    # Create a text summary
                    display_limit = 10
                    has_more = len(person_data) > display_limit
                    
                    # Get a summary of key columns
                    summary_parts = []
                    
                    # Customer distribution if available
                    customer_cols = [col for col in categorical_columns if "customer" in col.lower()]
                    if customer_cols:
                        customer_col = customer_cols[0]
                        customer_counts = person_data[customer_col].value_counts().head(5)
                        if not customer_counts.empty:
                            customer_text = ", ".join([f"{customer} ({count})" for customer, count in customer_counts.items()])
                            summary_parts.append(f"Top customers: {customer_text}")
                    
                    # Status distribution if available
                    status_cols = [col for col in categorical_columns if "status" in col.lower()]
                    if status_cols:
                        status_col = status_cols[0]
                        status_counts = person_data[status_col].value_counts()
                        if not status_counts.empty:
                            status_text = ", ".join([f"{status} ({count})" for status, count in status_counts.items()])
                            summary_parts.append(f"Status distribution: {status_text}")
                    
                    # Revenue summary if available
                    revenue_cols = [col for col in numeric_columns if "revenue" in col.lower()]
                    if revenue_cols:
                        revenue_col = revenue_cols[0]
                        total_revenue = person_data[revenue_col].sum()
                        avg_revenue = person_data[revenue_col].mean()
                        summary_parts.append(f"Total revenue: ${total_revenue:,.2f}, Average: ${avg_revenue:,.2f}")
                    
                    summary_text = "\n".join(summary_parts)
                    
                    # Prepare main response
                    response = f"**Information for {person_name}:**\n\nTotal projects: {len(person_data)}"
                    if summary_text:
                        response += f"\n\n{summary_text}"
                    
                    if has_more:
                        response += f"\n\nShowing first {display_limit} of {len(person_data)} projects:"
                    else:
                        response += f"\n\nAll {len(person_data)} projects:"
                    
                    # Add the data table
                    limited_data = person_data[important_cols].head(display_limit)
                    result_table = limited_data.to_string(index=False)
                    response += f"\n\n```\n{result_table}\n```"
                    
                    # Create visualization - bar chart of projects by status if status exists
                    fig = None
                    if status_cols:
                        status_col = status_cols[0]
                        status_counts = person_data[status_col].value_counts()
                        
                        if not status_counts.empty:
                            fig = px.bar(
                                x=status_counts.index,
                                y=status_counts.values,
                                title=f"Projects for {person_name} by Status",
                                labels={"x": "Status", "y": "Number of Projects"}
                            )
                    
                    return response, fig
        
        # Handle basic greetings and help
        if any(greeting in question_lower for greeting in ["hello", "hi", "hey", "help", "what can you do"]):
            column_info = f"Your data has {len(available_columns)} columns including: {', '.join(available_columns[:5])}"
            if len(available_columns) > 5:
                column_info += f" and {len(available_columns) - 5} more."
            
            suggestions = "Try asking about:\n"
            if "revenue" in numeric_columns or any("revenue" in col.lower() for col in numeric_columns):
                suggestions += "- Revenue analysis\n"
            if "customer" in categorical_columns or any("customer" in col.lower() for col in categorical_columns):
                suggestions += "- Customer information\n"
            if "project" in categorical_columns or any("project" in col.lower() for col in categorical_columns):
                suggestions += "- Project statistics\n"
            if "status" in categorical_columns or any("status" in col.lower() for col in categorical_columns):
                suggestions += "- Status distributions\n"
            if date_columns:
                suggestions += "- Time-based trends\n"
            suggestions += "- Summary statistics for any column\n"
            suggestions += "- 'What columns are available?'"
            
            return f"Hello! I can analyze your data based on the columns available.\n\n{column_info}\n\n{suggestions}", None
            
        # Handle column discovery requests
        if any(phrase in question_lower for phrase in ["what columns", "available columns", "what data", "show columns", "list columns"]):
            col_types = {
                "Numeric": numeric_columns,
                "Categorical": categorical_columns,
                "Date": date_columns
            }
            
            response = "**Available columns in your data:**\n\n"
            for type_name, cols in col_types.items():
                if cols:
                    response += f"*{type_name} columns:*\n- " + "\n- ".join(cols) + "\n\n"
            
            return response, None
        
        # Handle summary statistics request with filtering capability
        if "summary" in question_lower or "statistics" in question_lower or "describe" in question_lower:
            # Check for filtering conditions
            filter_match = re.search(r"(?:for|of)\s+([a-zA-Z\s]+)(?:.+?)(?:where|with|having|for|when)(?:.+?)([a-zA-Z\s]+?)(?:\s+is\s+|\s+=\s+|\s+equals\s+)([a-zA-Z0-9\s]+)", question_lower)
            
            # Initialize filtered_data as a copy of the original data
            filtered_data = data.copy()
            filter_desc = ""
            
            # Apply filtering if specified
            if filter_match:
                target_col_hint, filter_col_hint, filter_value_hint = filter_match.groups()
                
                # Find the filter column
                filter_col = None
                for col in available_columns:
                    normalized_col = col.lower().replace("(", "").replace(")", "").replace("/", "").replace("-", "")
                    if filter_col_hint.lower() in normalized_col or normalized_col in filter_col_hint.lower():
                        filter_col = col
                        break
                
                if filter_col:
                    # Find matching filter values using partial matching
                    matching_values = []
                    for val in filtered_data[filter_col].dropna().unique():
                        if filter_value_hint.lower() in str(val).lower() or str(val).lower() in filter_value_hint.lower():
                            matching_values.append(val)
                    
                    if matching_values:
                        # Apply the filter
                        filtered_data = filtered_data[filtered_data[filter_col].isin(matching_values)]
                        filter_desc = f" (filtered by {filter_col} = {matching_values[0]})"
                        
                        if filtered_data.empty:
                            return f"No data found where {filter_col} matches '{filter_value_hint}'.", None
                    else:
                        return f"Couldn't find any matching values for '{filter_value_hint}' in column '{filter_col}'.", None
                else:
                    return f"Couldn't find a column matching '{filter_col_hint}' to filter by.", None
            
            # Clean the question to handle special characters in column names
            cleaned_question = question_lower.replace("(", "").replace(")", "").replace("/", "").replace("-", "")
            
            # First try to find an exact column match
            col_match = None
            
            # If filtering was applied, use the target column hint
            if filter_match:
                target_col_hint = filter_match.group(1).strip()
                for col in available_columns:
                    normalized_col = col.lower().replace("(", "").replace(")", "").replace("/", "").replace("-", "")
                    if target_col_hint.lower() in normalized_col or normalized_col in target_col_hint.lower():
                        col_match = col
                        break
            else:
                # Regular column matching if no filter specified
                for col in available_columns:
                    normalized_col = col.lower().replace("(", "").replace(")", "").replace("/", "").replace("-", "")
                    if normalized_col in cleaned_question:
                        col_match = col
                        break
            
            # If no exact match, try partial matching
            if col_match is None:
                for col in available_columns:
                    normalized_col = col.lower().replace("(", "").replace(")", "").replace("/", "").replace("-", "")
                    parts = normalized_col.split()
                    if all(part in cleaned_question for part in parts if len(part) > 2):
                        col_match = col
                        break
            
            if col_match:
                if col_match in numeric_columns:
                    # Handle numeric column
                    stats = filtered_data[col_match].describe().to_dict()
                    fig = px.box(filtered_data, y=col_match, title=f"Distribution of {col_match}{filter_desc}")
                    return f"**Summary statistics for {col_match}{filter_desc}:**\n" + \
                           f"Count: {stats['count']:.0f}\n" + \
                           f"Mean: {stats['mean']:.2f}\n" + \
                           f"Std Dev: {stats['std']:.2f}\n" + \
                           f"Min: {stats['min']:.2f}\n" + \
                           f"25%: {stats['25%']:.2f}\n" + \
                           f"Median: {stats['50%']:.2f}\n" + \
                           f"75%: {stats['75%']:.2f}\n" + \
                           f"Max: {stats['max']:.2f}", fig
                elif col_match in categorical_columns:
                    # Enhanced categorical column analysis
                    if filtered_data[col_match].isna().all():
                        return f"**The column '{col_match}' contains only missing values{filter_desc}.**", None
                    
                    # Get value counts with proper handling of missing values
                    value_counts = filtered_data[col_match].value_counts(dropna=False).head(15)
                    total_count = len(filtered_data)
                    
                    # Calculate percentages
                    percentages = [(count, count/total_count*100) for val, count in value_counts.items()]
                    
                    # Prepare formatted output
                    value_summary = "\n".join([f"- {val}: {count} ({pct:.1f}%)" for (val, count), pct in zip(value_counts.items(), [p[1] for p in percentages])])
                    
                    # Create visualization - handle special case for Project Status colors
                    if "status" in col_match.lower() and any(x in str(list(value_counts.index)) for x in ["R", "G", "Y", "Red", "Green", "Yellow"]):
                        # Define color map for status values
                        status_color_map = {
                            "Red": "#d62728", "R": "#d62728", "Amber": "#ff7f0e", 
                            "Yellow": "#ffdd57", "Y": "#ff7f0e", "Green": "#2ca02c", 
                            "G": "#2ca02c", "Blank": "#cccccc", "<NA>": "#cccccc", "Unknown": "#cccccc"
                        }
                        
                        fig = px.pie(
                            values=value_counts.values, 
                            names=value_counts.index, 
                            title=f"Distribution of {col_match}{filter_desc}",
                            color=value_counts.index,
                            color_discrete_map=status_color_map
                        )
                    else:
                        fig = px.pie(
                            values=value_counts.values, 
                            names=value_counts.index, 
                            title=f"Distribution of {col_match}{filter_desc}"
                        )
                    
                    # Make the chart more readable
                    fig.update_traces(textinfo="percent+label")
                    
                    return f"**Value counts for {col_match}{filter_desc}:**\n\nTotal entries: {total_count}\n\n{value_summary}", fig
                elif col_match in date_columns:
                    # Handle date column
                    earliest = filtered_data[col_match].min()
                    latest = filtered_data[col_match].max()
                    return f"**Date range for {col_match}{filter_desc}:**\nEarliest: {earliest}\nLatest: {latest}\nSpan: {(latest - earliest).days} days", None
            else:
                # Check specifically for "status" in the question to handle Project Status (R/G/Y)
                if "status" in cleaned_question or "rgy" in cleaned_question:
                    status_cols = [col for col in categorical_columns if "status" in col.lower()]
                    if status_cols:
                        col_match = status_cols[0]
                        # Get value counts with proper handling of missing values
                        value_counts = filtered_data[col_match].value_counts(dropna=False)
                        total_count = len(filtered_data)
                        
                        # Calculate percentages
                        percentages = [(count, count/total_count*100) for val, count in value_counts.items()]
                        
                        # Prepare formatted output
                        value_summary = "\n".join([f"- {val}: {count} ({pct:.1f}%)" for (val, count), pct in zip(value_counts.items(), [p[1] for p in percentages])])
                        
                        # Create visualization with proper status colors
                        status_color_map = {
                            "Red": "#d62728", "R": "#d62728", "Amber": "#ff7f0e", 
                            "Yellow": "#ffdd57", "Y": "#ff7f0e", "Green": "#2ca02c", 
                            "G": "#2ca02c", "Blank": "#cccccc", "<NA>": "#cccccc", "Unknown": "#cccccc"
                        }
                        
                        fig = px.pie(
                            values=value_counts.values, 
                            names=value_counts.index, 
                            title=f"Distribution of {col_match}{filter_desc}",
                            color=value_counts.index,
                            color_discrete_map=status_color_map
                        )
                        fig.update_traces(textinfo="percent+label")
                        
                        return f"**Value counts for {col_match}{filter_desc}:**\n\nTotal entries: {total_count}\n\n{value_summary}", fig
                
                # General summary if no specific column mentioned
                numeric_summary = filtered_data[numeric_columns].describe().transpose()
                top_rows = min(10, len(numeric_summary))
                truncated_summary = numeric_summary.head(top_rows)
                
                filter_info = f" {filter_desc}" if filter_desc else ""
                
                return "**Dataset Summary" + filter_info + ":**\n" + \
                       f"Total rows: {len(filtered_data)}\n" + \
                       f"Total columns: {len(available_columns)}\n\n" + \
                       f"Numeric column summary (showing {top_rows} of {len(numeric_summary)} columns):\n{truncated_summary.to_string()}", fig
        
        # Revenue Analysis - adapt to actual column names
        revenue_cols = [col for col in numeric_columns if "revenue" in col.lower()]
        if revenue_cols and any(term in question_lower for term in ["revenue", "earnings", "income"]):
            revenue_col = revenue_cols[0]  # Use first revenue column found
            
            customer_cols = [col for col in categorical_columns if "customer" in col.lower() or "client" in col.lower()]
            if customer_cols and ("customer" in question_lower or "client" in question_lower):
                customer_col = customer_cols[0]
                match = re.search(r"(?:revenue|earnings|income).*?(?:for|of)\s*(.+?)(?:\?|$)", question_lower)
                if match:
                    customer_name_query = match.group(1).strip()
                    # Look for partial matches in customer names
                    customer_data = data[data[customer_col].str.lower().str.contains(customer_name_query, na=False)]
                    if not customer_data.empty:
                        revenue = customer_data[revenue_col].sum()
                        # Create visualization if date column exists
                        if date_columns and len(customer_data) > 1:
                            date_col = date_columns[0]
                            trend_data = customer_data.sort_values(date_col)
                            fig = px.line(trend_data, x=date_col, y=revenue_col,
                                        title=f"Revenue Trend for {customer_data[customer_col].iloc[0]}")
                        return f"Total {revenue_col} for {customer_data[customer_col].iloc[0]} is ${revenue:,.2f}", fig
                    return f"No data found for customer matching '{customer_name_query}'.", None
            else:
                total_revenue = data[revenue_col].sum()
                avg_revenue = data[revenue_col].mean()
                fig = px.box(data, y=revenue_col, title=f"{revenue_col} Distribution")
                return f"Total {revenue_col}: ${total_revenue:,.2f}\nAverage {revenue_col} per entry: ${avg_revenue:,.2f}", fig
        
        # Project Status Analysis - adapt to actual column names
        status_cols = [col for col in categorical_columns if "status" in col.lower()]
        if status_cols and "status" in question_lower:
            status_col = status_cols[0]
            
            customer_cols = [col for col in categorical_columns if "customer" in col.lower() or "client" in col.lower()]
            if customer_cols and ("customer" in question_lower or "client" in question_lower):
                customer_col = customer_cols[0]
                match = re.search(r"status.*?(?:for|of)\s*(.+?)(?:\?|$)", question_lower)
                if match:
                    customer_name_query = match.group(1).strip()
                    # Look for partial matches in customer names
                    customer_data = data[data[customer_col].str.lower().str.contains(customer_name_query, na=False)]
                    if not customer_data.empty:
                        status_counts = customer_data[status_col].value_counts()
                        fig = px.pie(values=status_counts.values, names=status_counts.index,
                                   title=f"{status_col} Distribution for {customer_data[customer_col].iloc[0]}")
                        status_text = "\n".join([f"{status}: {count}" for status, count in status_counts.items()])
                        return f"{status_col} breakdown for {customer_data[customer_col].iloc[0]}:\n{status_text}", fig
                    return f"No data found for customer matching '{customer_name_query}'.", None
            else:
                status_counts = data[status_col].value_counts()
                fig = px.pie(values=status_counts.values, names=status_counts.index,
                           title=f"Overall {status_col} Distribution")
                status_text = "\n".join([f"{status}: {count}" for status, count in status_counts.items()])
                return f"Overall {status_col} breakdown:\n{status_text}", fig
        
        # Executive or personnel analysis - adapt to actual column names
        exec_cols = [col for col in categorical_columns if any(term in col.lower() for term in ["exec", "manager", "director", "person", "staff"])]
        if exec_cols and any(term in question_lower for term in ["executive", "exec", "manager", "director", "person", "staff"]):
            exec_col = exec_cols[0]
            
            if "performance" in question_lower or "projects" in question_lower or "analysis" in question_lower:
                # Find revenue column and project/status columns if they exist
                if revenue_cols:
                    revenue_col = revenue_cols[0]
                    agg_dict = {revenue_col: 'sum'}
                    
                    # Find count column
                    if customer_cols:
                        agg_dict[customer_cols[0]] = 'count'
                    
                    # Find status column for success rate
                    if status_cols:
                        status_col = status_cols[0]
                        # This is a placeholder - would need to know what values indicate "success"
                        agg_dict[status_col] = lambda x: x.value_counts().to_dict()
                    
                    exec_analysis = data.groupby(exec_col).agg(agg_dict)
                    
                    # Prepare visualization
                    if revenue_cols:
                        fig = px.bar(exec_analysis.reset_index(), x=exec_col, y=revenue_col,
                                    title=f"{revenue_col} by {exec_col}")
                    
                    return f"**Analysis by {exec_col}:**\n{exec_analysis.to_string()}", fig
        
        # Top performers - adapt to actual column names
        if "top" in question_lower and revenue_cols:
            revenue_col = revenue_cols[0]
            
            customer_cols = [col for col in categorical_columns if "customer" in col.lower() or "client" in col.lower()]
            if customer_cols and ("customer" in question_lower or "client" in question_lower):
                customer_col = customer_cols[0]
                # Extract number if specified (default to 5)
                number_match = re.search(r"top\s+(\d+)", question_lower)
                top_n = int(number_match.group(1)) if number_match else 5
                
                top_items = data.groupby(customer_col)[revenue_col].sum().nlargest(top_n)
                fig = px.bar(top_items.reset_index(), x=customer_col, y=revenue_col,
                           title=f"Top {top_n} {customer_col}s by {revenue_col}")
                return f"**Top {top_n} {customer_col}s by {revenue_col}:**\n{top_items.to_string()}", fig
            
            # Handle other possible "top" requests for different columns
            for col in categorical_columns:
                if col.lower() in question_lower and revenue_cols:
                    top_n = 5
                    top_items = data.groupby(col)[revenue_col].sum().nlargest(top_n)
                    fig = px.bar(top_items.reset_index(), x=col, y=revenue_col,
                               title=f"Top {top_n} {col}s by {revenue_col}")
                    return f"**Top {top_n} {col}s by {revenue_col}:**\n{top_items.to_string()}", fig
        
        # Time trends analysis if date columns exist
        if date_columns and any(term in question_lower for term in ["trend", "over time", "time series", "historical"]):
            date_col = date_columns[0]
            
            # Look for columns to analyze
            analyze_col = None
            for col in numeric_columns:
                if col.lower() in question_lower:
                    analyze_col = col
                    break
            
            # If no specific column mentioned but revenue columns exist
            if analyze_col is None and revenue_cols:
                analyze_col = revenue_cols[0]
            
            if analyze_col:
                # Group by month or appropriate time period
                try:
                    trend_data = data.groupby(data[date_col].dt.to_period("M")).agg({analyze_col: 'sum'})
                    trend_data = trend_data.reset_index()
                    trend_data[date_col] = trend_data[date_col].dt.to_timestamp()
                    
                    fig = px.line(trend_data, x=date_col, y=analyze_col, 
                                title=f"{analyze_col} Trend Over Time", markers=True)
                    
                    return f"**{analyze_col} trend over time:**\nShowing monthly aggregated values.", fig
                except Exception as e:
                    return f"Could not create time trend analysis: {str(e)}", None
        
        # Direct counter for projects by status
        count_patterns = [
            r"(?:count|number|how many)(?:.+?)(?:projects|rows|records)(?:.+?)(?:status|state)(?:.+?)(?:as|is|=|:)(?:.+?)(red|green|yellow|amber|r\b|g\b|y\b|a\b)",
            r"(?:projects|rows|records)(?:.+?)(?:status|state)(?:.+?)(?:as|is|=|:)(?:.+?)(red|green|yellow|amber|r\b|g\b|y\b|a\b)(?:.+?)(?:count|number|how many)",
            r"(?:count|number|how many)(?:.+?)(red|green|yellow|amber|r\b|g\b|y\b|a\b)(?:.+?)(?:status|state|projects|rows)",
        ]
        
        for pattern in count_patterns:
            match = re.search(pattern, question_lower)
            if match:
                status_query = match.group(1).strip().lower()
                
                # Find all status-related columns
                status_cols = [col for col in categorical_columns if "status" in col.lower()]
                if not status_cols:
                    return "I couldn't find any status columns in your data.", None
                
                status_col = status_cols[0]  # Use the first status column found
                
                # Map the query to possible status values
                if status_query in ["red", "r"]:
                    possible_values = ["Red", "R"]
                elif status_query in ["green", "g"]:
                    possible_values = ["Green", "G"] 
                elif status_query in ["yellow", "y", "amber", "a"]:
                    possible_values = ["Yellow", "Y", "Amber", "A"]
                
                # Count matches
                total_matches = 0
                counts_by_value = {}
                
                # Print debugging info
                all_unique_values = data[status_col].dropna().unique()
                unique_values_str = ", ".join([f"'{str(val)}'" for val in all_unique_values])
                
                for val in possible_values:
                    # Exact match
                    matches = data[data[status_col] == val]
                    count = len(matches)
                    if count > 0:
                        counts_by_value[val] = count
                        total_matches += count
                
                    # Case insensitive contains match (for partial text values)
                    if data[status_col].dtype == object:  # Only for string columns
                        for unique_val in all_unique_values:
                            if val.lower() in str(unique_val).lower() and unique_val not in counts_by_value:
                                partial_matches = data[data[status_col] == unique_val]
                                partial_count = len(partial_matches)
                                counts_by_value[unique_val] = partial_count
                                total_matches += partial_count
                
                # Create a helpful response
                if total_matches > 0:
                    # Create detailed breakdown
                    breakdown = "\n".join([f"- {val}: {count}" for val, count in counts_by_value.items()])
                    
                    # Create visualization
                    if counts_by_value:
                        fig = px.bar(
                            x=list(counts_by_value.keys()),
                            y=list(counts_by_value.values()),
                            title=f"Projects with {status_query.title()} Status",
                            labels={"x": "Status Value", "y": "Count"}
                        )
                        # Color the bars appropriately
                        if status_query in ["red", "r"]:
                            fig.update_traces(marker_color="#d62728")
                        elif status_query in ["green", "g"]:
                            fig.update_traces(marker_color="#2ca02c")
                        elif status_query in ["yellow", "y", "amber", "a"]:
                            fig.update_traces(marker_color="#ff7f0e")
                    else:
                        fig = None
                    
                    return f"**Found {total_matches} projects with {status_query.title()} status**\n\nBreakdown by exact value:\n{breakdown}\n\nStatus column used: '{status_col}'\nAll possible values in this column: {unique_values_str}", fig
                else:
                    return f"I found 0 projects with {status_query.title()} status.\n\nStatus column used: '{status_col}'\nAll status values in this column: {unique_values_str}", None
        
        # Additional pattern for simple "list all X" queries
        list_match = re.search(r"(?:show|list|tell|get|find)(?:.+?)(all|the)\s+([a-zA-Z\s]+)", question_lower)
        if list_match:
            try:
                item_type = list_match.group(2).strip()
                
                # Check if we're asking for all values of a particular column
                matching_column = None
                for col in available_columns:
                    if item_type.lower() in col.lower() or col.lower() in item_type.lower():
                        matching_column = col
                        break
                
                if matching_column:
                    unique_values = data[matching_column].dropna().unique()
                    
                    if len(unique_values) > 30:  # If too many values, show a summary
                        value_counts = data[matching_column].value_counts().head(15)
                        fig = px.pie(values=value_counts.values, names=value_counts.index, 
                                  title=f"Top values in {matching_column} (showing top 15 of {len(unique_values)} unique values)")
                        value_list = "\n- ".join([f"{k}: {v}" for k, v in value_counts.items()])
                        return f"There are {len(unique_values)} unique values in '{matching_column}'. Here are the most common:\n\n- {value_list}", fig
                    else:
                        unique_list = "\n- ".join([str(val) for val in unique_values])
                        return f"All values in '{matching_column}':\n\n- {unique_list}", None
            except Exception as e:
                return f"Error processing list request: {str(e)}", None
        
        # If we've reached this point, we don't have a good match for the question
        # Let's provide a helpful response based on available columns
        column_suggestions = ""
        if numeric_columns:
            column_suggestions += f"\n- Numeric data: {', '.join(numeric_columns[:3])}"
            if len(numeric_columns) > 3:
                column_suggestions += f" and {len(numeric_columns)-3} more"
        if categorical_columns:
            column_suggestions += f"\n- Categories: {', '.join(categorical_columns[:3])}"
            if len(categorical_columns) > 3:
                column_suggestions += f" and {len(categorical_columns)-3} more"
        if date_columns:
            column_suggestions += f"\n- Time data: {', '.join(date_columns)}"
        
        return "I'm not sure how to answer that specific question. Try asking about:" + \
               "\n- 'What columns are available?'" + \
               "\n- Summary statistics for a specific column" + \
               "\n- Distribution of categorical data" + \
               "\n- Trends over time (if date data available)" + \
               f"\n\nYour data includes:{column_suggestions}", None

    except Exception as e:
        return f"I encountered an error analyzing the data: {str(e)}\n\nTry asking a different question or check if the columns you're asking about exist in the data.", None


# ------------------ PAGE DISPLAY LOGIC ------------------
# Use df_filtered for visualizations and df (original) for chat if needed, or pass df_filtered to chat
current_display_df = df_filtered # Use filtered data for display pages

if not current_display_df.empty:
    if page == "Ops Review":
        st.title("📊 Customer Health and Revenue Analysis Dashboard")
        
        # Show data source indicator
        if "Exective" in current_display_df.columns and "Project Status (R/G/Y)" in current_display_df.columns:
            st.success("✅ Using Data1.csv structure (Ops Review data)")
        else:
            st.warning("⚠️ Not using standard Ops Review data structure")
            
        status_color_map = {
            "Red": "#d62728", "R": "#d62728", "Amber": "#ff7f0e", 
            "Yellow": "#ffdd57", "Y": "#ff7f0e", "Green": "#2ca02c", 
            "G": "#2ca02c", "Blank": "#cccccc", "<NA>": "#cccccc", "Unknown": "#cccccc"
        }

        st.markdown("## 📝 Data Overview & Key Insights")
        
        # Calculate summary statistics (excluding revenue as it's from different file)
        total_projects_sum = current_display_df.shape[0]
        total_churned_sum = int(pd.to_numeric(current_display_df['Churn'], errors='coerce').fillna(0).sum()) if "Churn" in current_display_df.columns else 0
        churn_rate = (total_churned_sum / total_projects_sum) * 100 if total_projects_sum > 0 else 0
        unique_customers = current_display_df["Customer Name"].nunique() if "Customer Name" in current_display_df.columns else 0
        
        # Calculate total use cases if available
        total_usecases = current_display_df["Total Usecases/Module"].sum() if "Total Usecases/Module" in current_display_df.columns else 0
        
        # Handle both Executive column names
        exec_col = None
        if "Exective" in current_display_df.columns:
            exec_col = "Exective"
        elif "Owner" in current_display_df.columns:
            exec_col = "Owner"
            
        top_exec_name = None
        top_exec_count_val = 0
        if exec_col and not current_display_df[exec_col].dropna().empty:
            top_exec_series = current_display_df[exec_col].value_counts()
            if not top_exec_series.empty:
                top_exec_name = top_exec_series.idxmax()
                top_exec_count_val = top_exec_series.max()
        
        # Handle both Status column names
        status_col = None
        if "Project Status (R/G/Y)" in current_display_df.columns:
            status_col = "Project Status (R/G/Y)"
        elif "Status (R/G/Y)" in current_display_df.columns:
            status_col = "Status (R/G/Y)"
        
        # Create metric cards in columns
        metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
        
        with metric_col1:
            st.metric(
                label="📊 Total Projects",
                value=f"{total_projects_sum:,}",
                help="Total number of projects in current filtered data"
            )
        
        with metric_col2:
            st.metric(
                label="🏢 Unique Customers",
                value=f"{unique_customers:,}",
                help="Number of distinct customers"
            )
        
        with metric_col3:
            if total_usecases > 0:
                st.metric(
                    label="🔧 Total Use Cases",
                    value=f"{total_usecases:,}",
                    help="Total use cases/modules across all projects"
                )
            else:
                avg_projects_per_customer = total_projects_sum / unique_customers if unique_customers > 0 else 0
                st.metric(
                    label="📈 Projects per Customer",
                    value=f"{avg_projects_per_customer:.1f}",
                    help="Average number of projects per customer"
                )
        
        with metric_col4:
            if total_churned_sum > 0:
                st.metric(
                    label="⚠️ Churn Rate",
                    value=f"{churn_rate:.1f}%",
                    delta=f"{total_churned_sum} churned",
                    delta_color="inverse",
                    help="Percentage of projects that have churned"
                )
            else:
                st.metric(
                    label="✅ Active Projects",
                    value=f"{total_projects_sum:,}",
                    help="All projects are active (no churn data)"
                )
        
        st.markdown("---")
        
        # Create status distribution section
        status_col1, status_col2 = st.columns(2)
        
        with status_col1:
            st.markdown("### 📈 Status Distribution")
            
            if status_col and not current_display_df[status_col].empty:
                status_counts = current_display_df[status_col].value_counts()
                
                # Create a clean status summary with color coding
                for status, count in status_counts.items():
                    percentage = (count / total_projects_sum) * 100
                    
                    # Add color indicators based on status
                    if status in ["Green", "G"]:
                        emoji = "🟢"
                    elif status in ["Yellow", "Y", "Amber", "A"]:
                        emoji = "🟡"
                    elif status in ["Red", "R"]:
                        emoji = "🔴"
                    else:
                        emoji = "⚪"
                    
                    st.markdown(f"""
                    {emoji} **{status}:** {count} projects ({percentage:.1f}%)
                    """)
            else:
                st.markdown("*No status information available*")
        
        with status_col2:
            # Placeholder for future content
            st.write("")

        # Add Client Details section after status distribution
        st.markdown("---")
        st.markdown("### 👥 Client Details by Executive")
        
        # Check for both column name variations
        exec_col = None
        status_col = None
        
        if "Exective" in current_display_df.columns:
            exec_col = "Exective"
        elif "Owner" in current_display_df.columns:
            exec_col = "Owner"
            
        if "Project Status (R/G/Y)" in current_display_df.columns:
            status_col = "Project Status (R/G/Y)"
        elif "Status (R/G/Y)" in current_display_df.columns:
            status_col = "Status (R/G/Y)"
        
        if exec_col and status_col and "Customer Name" in current_display_df.columns:
            # Create columns for better layout
            client_col1, client_col2 = st.columns(2)
            executives = sorted(current_display_df[exec_col].unique())
            
            for i, exec_name in enumerate(executives):
                if pd.notna(exec_name):
                    exec_data = current_display_df[current_display_df[exec_col] == exec_name]
                    
                    # Alternate between columns
                    with client_col1 if i % 2 == 0 else client_col2:
                        st.markdown(f"**👤 {exec_name}**")
                        
                        for status in sorted(exec_data[status_col].unique()):
                            if pd.notna(status):
                                status_data = exec_data[exec_data[status_col] == status]
                                if not status_data.empty:
                                    client_list = status_data["Customer Name"].value_counts()
                                    
                                    # Status emoji
                                    if status in ["Green", "G"]:
                                        status_emoji = "🟢"
                                    elif status in ["Yellow", "Y", "Amber", "A"]:
                                        status_emoji = "🟡"
                                    elif status in ["Red", "R"]:
                                        status_emoji = "🔴"
                                    else:
                                        status_emoji = "⚪"
                                    
                                    st.markdown(f"&nbsp;&nbsp;{status_emoji} **{status}:** {', '.join(client_list.index)}")
                        
                        st.markdown("")  # Add spacing between executives
        else:
            st.info("Client details require Executive and Status columns to be available.")

        st.markdown("---")
        st.markdown("## 📈 Visualizations")
        
        if "Geography" in current_display_df.columns:
            # Get geography data for world map
            geo_counts = current_display_df["Geography"].value_counts().reset_index()
            geo_counts.columns = ["Geography", "Project_Count"]
            
            if not geo_counts.empty:
                # Create a mapping for common geography names to country codes
                country_mapping = {
                    "USA": "United States",
                    "US": "United States", 
                    "United States": "United States",
                    "UK": "United Kingdom",
                    "United Kingdom": "United Kingdom",
                    "Canada": "Canada",
                    "Germany": "Germany",
                    "France": "France",
                    "Italy": "Italy",
                    "Spain": "Spain",
                    "Japan": "Japan",
                    "China": "China",
                    "India": "India",
                    "Australia": "Australia",
                    "Brazil": "Brazil",
                    "Mexico": "Mexico",
                    "Netherlands": "Netherlands",
                    "Sweden": "Sweden",
                    "Norway": "Norway",
                    "South Korea": "South Korea",
                    "Singapore": "Singapore"
                }
                
                # Map geography names to standardized country names
                geo_counts["Country"] = geo_counts["Geography"].map(country_mapping).fillna(geo_counts["Geography"])
                
                # Create world map
                fig_world_map = px.choropleth(
                    geo_counts,
                    locations="Country",
                    color="Project_Count",
                    hover_name="Geography",
                    hover_data={"Project_Count": True},
                    locationmode="country names",
                    color_continuous_scale="Viridis",
                    title="Project Count by Geography - World Map"
                )
                
                fig_world_map.update_layout(
                    height=600,
                    geo=dict(
                        showframe=False,
                        showcoastlines=True,
                        projection_type='equirectangular'
                    )
                )
                
                st.plotly_chart(fig_world_map, use_container_width=True)
            else: 
                st.write("Not enough data for 'Project Count by Geography' world map.")
        else: 
            st.write("Required column 'Geography' not found for world map.")

        # Customer Health Chart - handle different column name variations
        health_col = None
        for col in current_display_df.columns:
            if "customer health" in col.lower():
                health_col = col
                break
        
        if health_col and not current_display_df[health_col].empty:
            st.subheader("Customer Health Distribution")
            health_counts = current_display_df[health_col].value_counts().reset_index()
            health_counts.columns = ["Health", "Count"]
            
            if not health_counts.empty:
                # Add client and executive information for hover
                health_details = []
                for health_status in health_counts["Health"]:
                    health_data = current_display_df[current_display_df[health_col] == health_status]
                    
                    # Get client names
                    if "Customer Name" in current_display_df.columns:
                        client_list = health_data["Customer Name"].value_counts()
                        clients_text = ", ".join(client_list.index)  # Show all clients
                    else:
                        clients_text = "No client data"
                    
                    # Get executive names
                    exec_col = None
                    if "Exective" in current_display_df.columns:
                        exec_col = "Exective"
                    elif "Owner" in current_display_df.columns:
                        exec_col = "Owner"
                    
                    if exec_col:
                        exec_list = health_data[exec_col].value_counts()
                        executives_text = ", ".join(exec_list.index)  # Show all executives
                    else:
                        executives_text = "No executive data"
                    
                    health_details.append({
                        "clients": clients_text,
                        "executives": executives_text
                    })
                
                health_counts["Clients"] = [detail["clients"] for detail in health_details]
                health_counts["Executives"] = [detail["executives"] for detail in health_details]
                
                # Create color mapping for health status
                health_color_map = {
                    "Green": "#2ca02c",
                    "Yellow": "#ffdd57", 
                    "Amber": "#ff7f0e",
                    "Red": "#d62728",
                    "Good": "#2ca02c",
                    "Fair": "#ff7f0e", 
                    "Poor": "#d62728"
                }
                
                fig_health_donut = px.pie(
                    health_counts,
                    values="Count",
                    names="Health",
                    title="Customer Health Distribution",
                    hole=0.4,
                    color="Health",
                    color_discrete_map=health_color_map,
                    hover_data=["Clients", "Executives"]
                )
                
                fig_health_donut.update_traces(
                    textinfo="percent+label+value",
                    textposition="auto",
                    hovertemplate="<b>%{label}</b><br>" +
                                  "Count: %{value}<br>" +
                                  "Percentage: %{percent}<br>" +
                                  "Clients: %{customdata[0]}<br>" +
                                  "Executives: %{customdata[1]}<br>" +
                                  "<extra></extra>"
                )
                
                fig_health_donut.update_layout(
                    height=500,
                    showlegend=True,
                    legend=dict(
                        orientation="v",
                        yanchor="middle",
                        y=0.5,
                        xanchor="left",
                        x=1.05
                    )
                )
                
                st.plotly_chart(fig_health_donut, use_container_width=True)
            else:
                st.write("Not enough data for Customer Health chart.")

        viz_row2_col1, viz_row2_col2 = st.columns(2)
        with viz_row2_col1:
            # Check for both "Exective" (Data1 tab) and "Owner" (Revenue tab)
            exec_col = None
            if "Exective" in current_display_df.columns:
                exec_col = "Exective"
            elif "Owner" in current_display_df.columns:
                exec_col = "Owner"
                
            if exec_col:
                exec_counts = current_display_df[exec_col].value_counts().reset_index()
                exec_counts.columns = [exec_col, "Count"]
                if not exec_counts.empty:
                    # Add client information for hover
                    exec_clients = []
                    for exec_name in exec_counts[exec_col]:
                        exec_data = current_display_df[current_display_df[exec_col] == exec_name]
                        if "Customer Name" in current_display_df.columns:
                            client_list = exec_data["Customer Name"].value_counts()
                            all_clients = ", ".join(client_list.index)  # Show all clients
                            exec_clients.append(all_clients)
                        else:
                            exec_clients.append("No client data")
                    
                    exec_counts["Clients"] = exec_clients
                    
                    fig_exec_donut = px.pie(
                        exec_counts, values="Count", names=exec_col,
                        title=f"Project Count by {exec_col}", hole=0.4,
                        hover_data=["Clients"]
                    )
                    fig_exec_donut.update_traces(
                        textinfo="percent+label",
                        hovertemplate="<b>%{label}</b><br>" +
                                      "Projects: %{value}<br>" +
                                      "Clients: %{customdata[0]}<br>" +
                                      "<extra></extra>"
                    )
                    fig_exec_donut.update_layout(height=400)
                    st.plotly_chart(fig_exec_donut, use_container_width=True)
                else: st.write(f"Not enough data for 'Project Count by {exec_col}' donut chart.")
            else: st.write("Column 'Exective' or 'Owner' not found for donut chart.")

        with viz_row2_col2:
            # Check for both column name variations
            exec_col = None
            status_col = None
            
            if "Exective" in current_display_df.columns:
                exec_col = "Exective"
            elif "Owner" in current_display_df.columns:
                exec_col = "Owner"
                
            if "Project Status (R/G/Y)" in current_display_df.columns:
                status_col = "Project Status (R/G/Y)"
            elif "Status (R/G/Y)" in current_display_df.columns:
                status_col = "Status (R/G/Y)"
                
            if exec_col and status_col:
                exec_status_counts = current_display_df.groupby([exec_col, status_col], observed=True).size().reset_index(name="Count")
                if not exec_status_counts.empty:
                    # Add client information for hover
                    exec_status_clients = []
                    for _, row in exec_status_counts.iterrows():
                        exec_name = row[exec_col]
                        status = row[status_col]
                        filtered_data = current_display_df[
                            (current_display_df[exec_col] == exec_name) & 
                            (current_display_df[status_col] == status)
                        ]
                        if "Customer Name" in current_display_df.columns and not filtered_data.empty:
                            client_list = filtered_data["Customer Name"].value_counts()
                            all_clients = ", ".join(client_list.index)  # Show all clients
                            exec_status_clients.append(all_clients)
                        else:
                            exec_status_clients.append("No client data")
                    
                    exec_status_counts["Clients"] = exec_status_clients
                    
                    fig_exec_status_bar = px.bar(
                        exec_status_counts, x=exec_col, y="Count", color=status_col,
                        title=f"Project Status by {exec_col}", barmode="group", 
                        color_discrete_map=status_color_map,
                        hover_data=["Clients"]
                    )
                    fig_exec_status_bar.update_traces(
                        hovertemplate="<b>%{x}</b><br>" +
                                      "Status: %{fullData.name}<br>" +
                                      "Count: %{y}<br>" +
                                      "Clients: %{customdata[0]}<br>" +
                                      "<extra></extra>"
                    )
                    fig_exec_status_bar.update_layout(height=400)
                    st.plotly_chart(fig_exec_status_bar, use_container_width=True)
                else: st.write(f"Not enough data for 'Project Status by {exec_col}' bar chart.")
            else: st.write("Required columns for 'Project Status by Executive' not found.")

        viz_row3_col1, viz_row3_col2 = st.columns(2)
        with viz_row3_col1:
            # Check for both status column variations
            status_col = None
            if "Project Status (R/G/Y)" in current_display_df.columns:
                status_col = "Project Status (R/G/Y)"
            elif "Status (R/G/Y)" in current_display_df.columns:
                status_col = "Status (R/G/Y)"
                
            if status_col and not current_display_df[status_col].empty:
                # Get total counts by status for a cleaner pie chart
                status_counts_df = current_display_df[status_col].value_counts().reset_index()
                status_counts_df.columns = ['Status', 'Count']
                
                # Create a clean pie chart
                fig_status_pie = px.pie(
                    status_counts_df, 
                    values="Count", 
                    names="Status", 
                    title="Project Status Distribution",
                    color="Status", 
                    color_discrete_map=status_color_map
                )
                
                # Update layout for better appearance
                fig_status_pie.update_traces(
                    textinfo="percent+label+value",
                    textposition="auto",
                    hovertemplate="<b>%{label}</b><br>" +
                                  "Projects: %{value}<br>" +
                                  "Percentage: %{percent}<br>" +
                                  "<extra></extra>"
                )
                
                fig_status_pie.update_layout(
                    height=400,
                    showlegend=True,
                    legend=dict(
                        orientation="v",
                        yanchor="middle",
                        y=0.5,
                        xanchor="left",
                        x=1.05
                    )
                )
                
                st.plotly_chart(fig_status_pie, use_container_width=True)
                
                # Add a simple status breakdown table below
                st.subheader("Status Breakdown")
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Project Counts by Status:**")
                    for idx, row in status_counts_df.iterrows():
                        percentage = (row['Count'] / status_counts_df['Count'].sum()) * 100
                        st.markdown(f"• **{row['Status']}**: {row['Count']} projects ({percentage:.1f}%)")
                
                with col2:
                    # Show top customers for each status
                    st.markdown("**Top Customer by Status:**")
                    for status in status_counts_df['Status']:
                        customers_for_status = current_display_df[current_display_df[status_col] == status]
                        if not customers_for_status.empty:
                            top_customer = customers_for_status["Customer Name"].value_counts().head(1)
                            if not top_customer.empty:
                                customer_name = top_customer.index[0]
                                customer_count = top_customer.iloc[0]
                                st.markdown(f"• **{status}**: {customer_name} ({customer_count} projects)")
                            else:
                                st.markdown(f"• **{status}**: No customer data")
            else: st.write("Not enough data for 'Project Status Distribution' chart.")
        
        with viz_row3_col2:
            if "Contract End Date" in current_display_df.columns and not current_display_df["Contract End Date"].isnull().all():
                # Create a DataFrame with contract end dates and customer names
                contract_customer_data = current_display_df[["Contract End Date", "Customer Name"]].dropna()
                
                if not contract_customer_data.empty:
                    # Group by year and customer
                    contract_customer_data["End_Year"] = contract_customer_data["Contract End Date"].dt.year
                    contract_trend_year = contract_customer_data.groupby(["End_Year", "Customer Name"]).size().reset_index(name="Contract_Count")
                    
                    # Create scatter plot with client names visible
                    fig_contracts_scatter = px.scatter(
                        contract_trend_year,
                        x="End_Year",
                        y="Contract_Count", 
                        color="Customer Name",
                        text="Customer Name",  # Show client names as text
                        title="Contracts Ending by Year - Scatter Plot",
                        hover_data=["Contract_Count"],
                        size_max=60
                    )
                    
                    # Update text positioning and styling
                    fig_contracts_scatter.update_traces(
                        textposition="middle center",
                        textfont=dict(size=10, color="black"),
                        marker=dict(size=12, line=dict(width=2, color="white")),
                        hovertemplate="<b>%{customdata[1]}</b><br>" +
                                      "Year: %{x}<br>" +
                                      "Contracts: %{y}<br>" +
                                      "<extra></extra>"
                    )
                    
                    # Improve layout for better readability
                    fig_contracts_scatter.update_layout(
                        height=500,
                        xaxis_title="Contract End Year",
                        yaxis_title="Number of Contracts",
                        showlegend=True,
                        legend=dict(
                            orientation="v",
                            yanchor="top",
                            y=1,
                            xanchor="left",
                            x=1.02
                        ),
                        # Add some padding to prevent text overlap
                        margin=dict(l=50, r=150, t=50, b=50)
                    )
                    
                    # Adjust x-axis to show all years clearly
                    if len(contract_trend_year["End_Year"].unique()) > 1:
                        year_range = contract_trend_year["End_Year"].max() - contract_trend_year["End_Year"].min()
                        fig_contracts_scatter.update_xaxes(
                            tickmode="linear",
                            dtick=1 if year_range <= 10 else 2
                        )
                    
                    st.plotly_chart(fig_contracts_scatter, use_container_width=True)
                else:
                    st.write("Not enough data for 'Contracts Ending by Year' chart.")
            else: st.write("Column 'Contract End Date' not found or empty for 'Contracts Ending by Year' chart.")
        


        st.markdown("---"); st.markdown("## 📄 Embedded Documents")
        # st.markdown("### SharePoint Presentation")
        # components.iframe(src="https://sparkc.sharepoint.com/:p:/s/ProfessionalServicesGroup/EV7F-1-nHr5BkrR6-MbTuPYBSISt1dQ9BdkuX3MUYm94NA?e=JOkhCh", height=450, width=1000, scrolling=True)
        
        st.markdown("### Weekly Project Status PDF")
        
        # Get PDF from Google Sheets
        def show_google_sheets_pdf(url):
            with st.spinner("Loading PDF from Google Sheets..."):
                try:
                    import requests
                    response = requests.get(url)
                    if response.status_code == 200:
                        # Create a temp file to hold the PDF
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                            tmp_file.write(response.content)
                            tmp_path = tmp_file.name
                        
                        # Read and display the PDF
                        try:
                            with open(tmp_path, "rb") as f:
                                base64_pdf = base64.b64encode(f.read()).decode('utf-8')
                            st.markdown(f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="650" type="application/pdf" style="border: 1px solid #ddd;"></iframe>', unsafe_allow_html=True)
                            
                            # Display basic PDF info
                            with st.expander("PDF Information"):
                                st.write("PDF successfully loaded from Google Sheets")
                            
                            # Clean up the temp file
                            os.unlink(tmp_path)
                        except Exception as e:
                            st.error(f"Error displaying PDF: {str(e)}")
                            if os.path.exists(tmp_path):
                                os.unlink(tmp_path)
                    else:
                        st.error(f"Failed to retrieve PDF from Google Sheets. Status code: {response.status_code}")
                except Exception as e:
                    st.error(f"Error accessing Google Sheets PDF: {str(e)}")
        
        # Use the function to display Google Sheets PDF
        show_google_sheets_pdf(DATA_SOURCES["weekly_status_pdf"]["url"])
        
        # Legacy code for local PDF (as fallback)
        with st.expander("Try Local PDF (Fallback Option)"):
            st.info("If Google Sheets PDF export doesn't work, you can try loading from a local file.")
            
            # Original local PDF display function
            def show_local_pdf(pdf_file_path):
                script_dir = os.path.dirname(__file__)
                abs_pdf_file_path = os.path.join(script_dir, pdf_file_path)
                if not os.path.exists(abs_pdf_file_path): abs_pdf_file_path = os.path.abspath(pdf_file_path)
                if os.path.exists(abs_pdf_file_path):
                    with open(abs_pdf_file_path, "rb") as f: base64_pdf = base64.b64encode(f.read()).decode('utf-8')
                    st.markdown(f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="650" type="application/pdf" style="border: 1px solid #ddd;"></iframe>', unsafe_allow_html=True)
                else: st.error(f"PDF file '{pdf_file_path}' not found. Looked for: '{abs_pdf_file_path}'")
            
            pdf_file_path = st.text_input("Local PDF file path (relative to script directory):", "Weekly Project Status 4June2025.pdf")
            if st.button("Load Local PDF"):
                show_local_pdf(pdf_file_path)

    elif page == "Tickets":
        st.title("🎫 Tickets Dashboard")
        st.markdown("Insights into support tickets and resolutions.")
        
        # Add Hubspot and Jira links in a prominent section
        st.markdown("## 🔗 Ticket Integration Links")
        tickets_col1, tickets_col2 = st.columns(2)
        
        with tickets_col1:
            st.markdown("""
            ### Hubspot Tickets
            [Access Hubspot Tickets](https://app.hubspot.com/contacts/20074161/objects/0-5/views/all/list)
            """)
            st.components.v1.html(
                """
                <a href="https://app.hubspot.com/contacts/20074161/objects/0-5/views/all/list" 
                   target="_blank" 
                   style="display: inline-block; padding: 10px 20px; background-color: #ff7a59; color: white; 
                   text-decoration: none; border-radius: 5px; font-weight: bold; margin-top: 10px;">
                   Open Hubspot Tickets
                </a>
                """, 
                height=60
            )
        
        with tickets_col2:
            st.markdown("""
            ### Jira Tickets
            [Access Jira Board](https://sparkcognition.atlassian.net/jira/software/projects/ASUP/boards/1116)
            """)
            st.components.v1.html(
                """
                <a href="https://sparkcognition.atlassian.net/jira/software/projects/ASUP/boards/1116" 
                   target="_blank" 
                   style="display: inline-block; padding: 10px 20px; background-color: #0052cc; color: white; 
                   text-decoration: none; border-radius: 5px; font-weight: bold; margin-top: 10px;">
                   Open Jira Board
                </a>
                """, 
                height=60
            )
        
        st.markdown("---")
        
        if not current_display_df.empty:
            # Key metrics - Remove Revenue information
            st.markdown("### 📊 Ticket Metrics")
            ticket_kpi_row = st.columns(3)
            
            # Count of tickets if status column exists
            total_tickets = current_display_df.shape[0]
            ticket_kpi_row[0].metric("Total Tickets", f"{total_tickets:,}")
            
            # Count by status if available
            if "Ticket Status" in current_display_df.columns:
                open_tickets = current_display_df[current_display_df["Ticket Status"].str.lower() == "open"].shape[0]
                closed_tickets = current_display_df[current_display_df["Ticket Status"].str.lower() == "closed"].shape[0]
                ticket_kpi_row[1].metric("Open Tickets", f"{open_tickets:,}")
                ticket_kpi_row[2].metric("Closed Tickets", f"{closed_tickets:,}")
            else:
                # If no status column exists, show other non-revenue metrics
                customers_with_tickets = current_display_df["Customer Name"].nunique() if "Customer Name" in current_display_df else 0
                ticket_kpi_row[1].metric("Customers with Tickets", f"{customers_with_tickets:,}")
                
                # Metric related to ticket count instead of revenue
                if "Ticket Priority" in current_display_df.columns:
                    high_priority = current_display_df[current_display_df["Ticket Priority"].str.lower() == "high"].shape[0] if "Ticket Priority" in current_display_df else 0
                    ticket_kpi_row[2].metric("High Priority Tickets", f"{high_priority:,}")
                else:
                    # Default to showing a generic ticket-related metric
                    ticket_kpi_row[2].metric("Avg. Tickets per Customer", f"{total_tickets/max(1, customers_with_tickets):.1f}")
            
            st.markdown("---")
            
            # Tickets per Customer visualization
            if "Customer Name" in current_display_df.columns:
                st.subheader("Tickets per Customer")
                
                # Check if Ticket Status column exists
                if "Ticket Status" in current_display_df.columns:
                    # Create a pivot table of tickets by customer and status
                    ticket_pivot = pd.pivot_table(
                        current_display_df,
                        index="Customer Name",
                        columns="Ticket Status",
                        aggfunc="size",
                        fill_value=0
                    ).reset_index()
                    
                    # Get top 10 customers by total tickets
                    ticket_counts = current_display_df["Customer Name"].value_counts().reset_index()
                    ticket_counts.columns = ["Customer Name", "Total Tickets"]
                    top_customers = ticket_counts.sort_values("Total Tickets", ascending=False).head(10)["Customer Name"].tolist()
                    
                    # Filter pivot table to top customers
                    filtered_pivot = ticket_pivot[ticket_pivot["Customer Name"].isin(top_customers)]
                    
                    # Melt the pivot table for plotting
                    plot_data = pd.melt(
                        filtered_pivot,
                        id_vars=["Customer Name"],
                        var_name="Ticket Status",
                        value_name="Count"
                    )
                    
                    # Create a grouped bar chart
                    fig_tickets_by_customer = px.bar(
                        plot_data,
                        x="Customer Name",
                        y="Count",
                        color="Ticket Status",
                        title="Tickets by Customer and Status (Top 10)",
                        barmode="group"
                    )
                    fig_tickets_by_customer.update_layout(height=500)
                    st.plotly_chart(fig_tickets_by_customer, use_container_width=True)
                    
                    # Heat map of tickets by status
                    st.subheader("Ticket Status Heat Map")
                    # Create a correlation matrix-like display
                    heat_data = filtered_pivot.set_index("Customer Name")
                    
                    fig_heatmap = px.imshow(
                        heat_data,
                        labels=dict(x="Ticket Status", y="Customer", color="Count"),
                        title="Ticket Status Heat Map by Customer",
                        color_continuous_scale="YlOrRd"
                    )
                    fig_heatmap.update_layout(height=500)
                    st.plotly_chart(fig_heatmap, use_container_width=True)
                else:
                    # Simple count visualization if no status column
                    ticket_counts = current_display_df["Customer Name"].value_counts().reset_index()
                    ticket_counts.columns = ["Customer Name", "Count"]
                    ticket_counts = ticket_counts.sort_values("Count", ascending=False).head(10)
                    
                    fig_tickets_by_customer = px.bar(
                        ticket_counts,
                        x="Customer Name",
                        y="Count",
                        title="Tickets by Customer (Top 10)",
                        color="Count",
                        color_continuous_scale="Viridis"
                    )
                    fig_tickets_by_customer.update_layout(height=500)
                    st.plotly_chart(fig_tickets_by_customer, use_container_width=True)
            
            # Example: Tickets by Application if the column exists
            if "Application" in current_display_df.columns and not current_display_df["Application"].empty:
                st.subheader("Tickets by Application")
                app_counts = current_display_df["Application"].value_counts().reset_index()
                app_counts.columns = ['Application', 'Count']
                fig_tickets_app = px.bar(
                    app_counts, 
                    x="Application", 
                    y="Count", 
                    title="Tickets by Application",
                    color="Count",
                    color_continuous_scale="Blues"
                )
                st.plotly_chart(fig_tickets_app, use_container_width=True)
            
            # Ticket Response Time analysis if dates available
            date_columns = [col for col in current_display_df.columns if 'date' in col.lower()]
            if len(date_columns) >= 2:  # Need at least 2 date columns for response time
                st.subheader("Ticket Response Time Analysis")
                st.info("This is a placeholder for response time analysis. With actual ticket data containing created and resolved dates, you can calculate average response times.")
                
                # Placeholder graph
                st.write("Response Time Chart Placeholder")
                
            else:
                st.warning("No data loaded/matches filters to display ticket information.")


    elif page == "Finance":
        st.title("💰 Finance Dashboard")
        st.markdown("Financial performance and revenue analysis.")
        
        # Show data source indicator for Finance
        if "Status (R/G/Y)" in current_display_df.columns or "Contracted ARR" in current_display_df.columns:
            st.success("✅ Using Revenue.csv structure (Finance data)")
        else:
            st.warning("⚠️ Not using standard Finance data structure")
        
        if not current_display_df.empty:
            # Clean numeric columns by removing currency symbols and converting to numeric
            numeric_columns_to_clean = ["Contracted ARR", "Recognized ARR", "Services Revenue"]
            for col in numeric_columns_to_clean:
                if col in current_display_df.columns:
                    current_display_df[col] = pd.to_numeric(
                        current_display_df[col].astype(str).str.replace(r'[\$,]', '', regex=True), 
                        errors='coerce'
                    ).fillna(0)
            
            # Add metric cards showing key KPIs
            st.markdown("### 📊 Key Financial KPIs")
            fin_kpi_row1 = st.columns(4)
            
            # Contracted ARR
            total_contracted_arr = current_display_df["Contracted ARR"].sum() if "Contracted ARR" in current_display_df.columns else 0
            fin_kpi_row1[0].metric(
                "Total Contracted ARR", 
                f"${total_contracted_arr:,.0f}"
            )
            
            # Recognized ARR
            total_recognized_arr = current_display_df["Recognized ARR"].sum() if "Recognized ARR" in current_display_df.columns else 0
            fin_kpi_row1[1].metric(
                "Total Recognized ARR", 
                f"${total_recognized_arr:,.0f}"
            )
            
            # Services Revenue
            total_services_revenue = current_display_df["Services Revenue"].sum() if "Services Revenue" in current_display_df.columns else 0
            fin_kpi_row1[2].metric(
                "Total Services Revenue", 
                f"${total_services_revenue:,.0f}"
            )
            
            # Active Contracts
            active_contracts = 0
            if "Status (R/G/Y)" in current_display_df.columns:
                active_contracts = current_display_df[current_display_df["Status (R/G/Y)"].astype(str).str.title().isin(["Green", "Amber", "G", "Y", "Yellow"])].shape[0]
            else: 
                active_contracts = current_display_df.shape[0] 
            
            fin_kpi_row1[3].metric("Active Contracts", f"{active_contracts:,}")
            
            # Additional KPIs
            fin_kpi_row2 = st.columns(3)
            
            # Total Customers
            total_customers = current_display_df["Customer Name"].nunique() if "Customer Name" in current_display_df.columns else 0
            fin_kpi_row2[0].metric("Total Customers", f"{total_customers:,}")
            
            # ARR Recognition Rate
            arr_recognition_rate = (total_recognized_arr / total_contracted_arr * 100) if total_contracted_arr > 0 else 0
            fin_kpi_row2[1].metric("ARR Recognition Rate", f"{arr_recognition_rate:.1f}%")
            
            # Average Contract Value
            avg_contract_value = total_contracted_arr / total_customers if total_customers > 0 else 0
            fin_kpi_row2[2].metric("Avg Contract Value", f"${avg_contract_value:,.0f}")
            
            st.markdown("---")
            st.markdown("### 📈 Revenue Analysis")
            
            # Revenue by Geography
            if "Geography" in current_display_df.columns and "Contracted ARR" in current_display_df.columns:
                st.subheader("Contracted ARR by Geography")
                geo_revenue = current_display_df.groupby("Geography", observed=True)["Contracted ARR"].sum().reset_index()
                geo_revenue = geo_revenue.sort_values("Contracted ARR", ascending=False)
                
                if not geo_revenue.empty:
                    fig_geo_revenue = px.bar(
                        geo_revenue, 
                        x="Geography", 
                        y="Contracted ARR",
                        title="Contracted ARR by Geography",
                        color="Contracted ARR",
                        color_continuous_scale="Viridis"
                    )
                    fig_geo_revenue.update_traces(
                        text=geo_revenue["Contracted ARR"].apply(lambda x: f"${x:,.0f}"), 
                        textposition="outside"
                    )
                    fig_geo_revenue.update_layout(height=450)
                    st.plotly_chart(fig_geo_revenue, use_container_width=True)
                else:
                    st.write("Not enough data for Geography Revenue visualization.")
            
            # Create two columns for next row of charts
            fin_viz_row1_col1, fin_viz_row1_col2 = st.columns(2)
            
            with fin_viz_row1_col1:
                # Customer-wise Revenue Distribution
                if "Contracted ARR" in current_display_df.columns and "Customer Name" in current_display_df.columns:
                    st.subheader("Top 10 Customers by Contracted ARR")
                    revenue_by_customer = current_display_df.groupby("Customer Name", observed=True)["Contracted ARR"].sum().reset_index()
                    revenue_by_customer = revenue_by_customer.sort_values("Contracted ARR", ascending=False).head(10)
                    
                    if not revenue_by_customer.empty:
                        fig_customer_revenue = px.bar(
                            revenue_by_customer, 
                            x="Customer Name", 
                            y="Contracted ARR",
                            title="Top 10 Customers by Contracted ARR",
                            color="Contracted ARR",
                            color_continuous_scale="Blues"
                        )
                        fig_customer_revenue.update_traces(
                            text=revenue_by_customer["Contracted ARR"].apply(lambda x: f"${x:,.0f}"), 
                            textposition="outside"
                        )
                        fig_customer_revenue.update_layout(
                            height=450,
                            xaxis_tickangle=-45
                        )
                        st.plotly_chart(fig_customer_revenue, use_container_width=True)
                    else:
                        st.write("Not enough data for Customer Revenue Distribution.")
            
            with fin_viz_row1_col2:
                # Revenue Distribution by Status
                if "Contracted ARR" in current_display_df.columns and "Status (R/G/Y)" in current_display_df.columns:
                    st.subheader("Contracted ARR by Status")
                    revenue_by_status = current_display_df.groupby("Status (R/G/Y)", observed=True)["Contracted ARR"].sum().reset_index()
                    
                    if not revenue_by_status.empty:
                        # Status color map
                        status_color_map = {
                            "Red": "#d62728", "R": "#d62728", "Amber": "#ff7f0e", 
                            "Yellow": "#ffdd57", "Y": "#ff7f0e", "Green": "#2ca02c", 
                            "G": "#2ca02c", "Blank": "#cccccc", "<NA>": "#cccccc", "Unknown": "#cccccc"
                        }
                        
                        fig_status_revenue = px.pie(
                            revenue_by_status, 
                            names="Status (R/G/Y)", 
                            values="Contracted ARR",
                            title="Contracted ARR Distribution by Status",
                            color="Status (R/G/Y)",
                            color_discrete_map=status_color_map
                        )
                        fig_status_revenue.update_traces(textinfo="percent+label")
                        st.plotly_chart(fig_status_revenue, use_container_width=True)
                    else:
                        st.write("Not enough data for Revenue by Status visualization.")
            
            # Create second row of visualizations
            fin_viz_row2_col1, fin_viz_row2_col2 = st.columns(2)
            
            with fin_viz_row2_col1:
                # Industry Sector Analysis
                if "Industry Sector" in current_display_df.columns and "Contracted ARR" in current_display_df.columns:
                    st.subheader("Contracted ARR by Industry Sector")
                    industry_revenue = current_display_df.groupby("Industry Sector", observed=True)["Contracted ARR"].sum().reset_index()
                    industry_revenue = industry_revenue.sort_values("Contracted ARR", ascending=False)
                    
                    if not industry_revenue.empty:
                        fig_industry_revenue = px.pie(
                            industry_revenue, 
                            names="Industry Sector", 
                            values="Contracted ARR",
                            title="Contracted ARR by Industry Sector"
                        )
                        fig_industry_revenue.update_traces(textinfo="percent+label")
                        st.plotly_chart(fig_industry_revenue, use_container_width=True)
                    else:
                        st.write("Not enough data for Industry Sector visualization.")
            
            with fin_viz_row2_col2:
                # ARR Recognition vs Contracted Analysis
                if "Contracted ARR" in current_display_df.columns and "Recognized ARR" in current_display_df.columns:
                    st.subheader("ARR Recognition Analysis")
                    
                    # Create scatter plot showing contracted vs recognized ARR
                    fig_arr_scatter = px.scatter(
                        current_display_df,
                        x="Contracted ARR",
                        y="Recognized ARR",
                        color="Status (R/G/Y)" if "Status (R/G/Y)" in current_display_df.columns else None,
                        hover_data=["Customer Name"] if "Customer Name" in current_display_df.columns else None,
                        title="Contracted vs Recognized ARR",
                        color_discrete_map=status_color_map if "Status (R/G/Y)" in current_display_df.columns else None
                    )
                    
                    # Add diagonal line to show perfect recognition
                    max_arr = max(current_display_df["Contracted ARR"].max(), current_display_df["Recognized ARR"].max())
                    fig_arr_scatter.add_scatter(
                        x=[0, max_arr],
                        y=[0, max_arr],
                        mode="lines",
                        name="Perfect Recognition",
                        line=dict(dash="dash", color="gray")
                    )
                    
                    fig_arr_scatter.update_layout(height=450)
                    st.plotly_chart(fig_arr_scatter, use_container_width=True)
                    
            # Revenue Trends Over Time (if contract dates are available)
            if "Contract Start Date" in current_display_df.columns and "Contracted ARR" in current_display_df.columns and not current_display_df["Contract Start Date"].isnull().all():
                st.subheader("Revenue Trends Over Time")
                
                # Group by month and sum revenue
                revenue_trend = current_display_df.groupby(current_display_df["Contract Start Date"].dt.to_period("M"))["Contracted ARR"].sum().reset_index()
                revenue_trend["Contract Start Date"] = revenue_trend["Contract Start Date"].dt.to_timestamp()
                
                if not revenue_trend.empty:
                    fig_revenue_trend = px.line(
                        revenue_trend, 
                        x="Contract Start Date", 
                        y="Contracted ARR",
                        title="Contracted ARR by Contract Start Date",
                        markers=True
                    )
                    fig_revenue_trend.update_layout(height=450)
                    st.plotly_chart(fig_revenue_trend, use_container_width=True)
                else:
                    st.write("Not enough data for Revenue Trends visualization.")
                    
            # Application Analysis
            if "Application" in current_display_df.columns and "Contracted ARR" in current_display_df.columns:
                st.subheader("Revenue by Application")
                app_revenue = current_display_df.groupby("Application", observed=True)["Contracted ARR"].sum().reset_index()
                app_revenue = app_revenue.sort_values("Contracted ARR", ascending=False)
                
                if not app_revenue.empty:
                    fig_app_revenue = px.bar(
                        app_revenue, 
                        x="Application", 
                        y="Contracted ARR",
                        title="Contracted ARR by Application",
                        color="Contracted ARR",
                        color_continuous_scale="Oranges"
                    )
                    fig_app_revenue.update_traces(
                        text=app_revenue["Contracted ARR"].apply(lambda x: f"${x:,.0f}"), 
                        textposition="outside"
                    )
                    fig_app_revenue.update_layout(height=450)
                    st.plotly_chart(fig_app_revenue, use_container_width=True)
                else:
                    st.write("Not enough data for Application Revenue visualization.")
        else:
            st.warning("No data loaded/matches filters to display finance information.")
    
    elif page == "Chat Analytics":
        st.title("💬 Enhanced Chat Analytics")
        st.markdown("Ask questions about your data or check FAQs. The chatbot can now provide visualizations and detailed analysis.")

        # Use the original, unfiltered df for chat Q&A to provide broader answers
        chat_data_context = df.copy() if not df.empty else pd.DataFrame()

        display_faq(chat_data_context)
        st.markdown("---")
        st.subheader("Ask a Question")

        # Display existing messages
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                if isinstance(message["content"], tuple):
                    st.markdown(message["content"][0])
                    if message["content"][1] is not None:
                        st.plotly_chart(message["content"][1], use_container_width=True)
                else:
                    st.markdown(message["content"])

        # Chat input
        if prompt := st.chat_input("What would you like to know about your data?"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                response, fig = analyze_data_for_chat(prompt, chat_data_context)
                st.markdown(response)
                if fig is not None:
                    st.plotly_chart(fig, use_container_width=True)
                st.session_state.messages.append({"role": "assistant", "content": (response, fig)})
    
    # Common Footer for all pages with data
    st.markdown("---")
    st.markdown(
        """<div style='text-align: center; color: #333; font-size: 14px;'><small>© 2025 Avathon Analytics | Internal</small></div>""",
        unsafe_allow_html=True,
    )

# Handling for when no data is loaded or df becomes empty after initial load attempt
elif df.empty and (data_source != "Upload File" or (data_source == "Upload File" and ('uploaded_file' not in locals() or uploaded_file is None))):
    # This condition means df is empty because no data source was successfully used yet (initial state or error before filtering)
    if page == "Chat Analytics": # Special handling for chat page to show its structure even without data
        st.title("💬 Chat Analytics")
        st.markdown("Ask questions about your data or check FAQs.")
        display_faq(pd.DataFrame()) # Show FAQ structure with no data message
        st.markdown("---")
        st.subheader("Ask a Question")
        st.info("Load data on another page to ask questions about it.")
        for message in st.session_state.messages: # Still show chat history if any
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        if prompt := st.chat_input("What would you like to know?"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)
            with st.chat_message("assistant"): 
                response = "Please load data first on one of the dashboard pages before asking questions."
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
    else:
        st.info("Please load a dataset using one of the options at the top to view the dashboard.")
elif not df.empty and df_filtered.empty: 
    # This condition means data was loaded (df is not empty), but filters made df_filtered empty
    st.warning("No data matches the current filter criteria. Please adjust your filters in the sidebar.")
    if page == "Chat Analytics": # Chat page can still function with original df
        st.title("💬 Chat Analytics")
        st.markdown("Ask questions about your data or check FAQs. Note: Dashboard filters do not apply to chat Q&A on data.")
        chat_data_context = df.copy()
        display_faq(chat_data_context)
        st.markdown("---")
        st.subheader("Ask a Question")
        for message in st.session_state.messages:
            with st.chat_message(message["role"]): st.markdown(message["content"])
        if prompt := st.chat_input("What would you like to know?"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)
            with st.chat_message("assistant"):
                response = analyze_data_for_chat(prompt, chat_data_context)[0]
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})