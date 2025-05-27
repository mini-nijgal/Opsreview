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

# --- SharePoint Authentication UI ---
# Add collapsible authentication section in sidebar
with st.sidebar.expander("SharePoint Authentication", expanded="sharepoint_username" not in st.session_state):
    st.write("Enter SharePoint credentials to access data")
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
    st.markdown("### Finding Correct SharePoint URLs")
    st.markdown("""
    To find the correct document paths:
    1. Navigate to your document in SharePoint
    2. Click the "Copy link" button
    3. Instead of using the sharing link, note the URL in your browser's address bar
    4. Use the format: `https://domain.sharepoint.com/sites/sitename/Shared%20Documents/path/to/file.xlsx`
    
    If you're getting authentication errors:
    - Make sure you're using your full email address
    - Try an app password if you have multi-factor authentication enabled
    - Ask your SharePoint administrator for the correct direct document paths
    """)


# ------------------ DATA SELECTION ------------------
def read_data_from_url(url):
    try:
        return pd.read_csv(url, encoding="ISO-8859-1")
    except Exception as e:
        st.error(f"Error reading data from URL: {e}")
        return None

# Define the SharePoint URLs for different data sources
SHAREPOINT_URLS = {
    "ops_review": {
        "url": "https://sparkc.sharepoint.com/sites/ProfessionalServicesGroup/Shared%20Documents/General/OpsReviewData.xlsx",
        "sheet": "Master"
    },
    "finance": {
        "url": "https://sparkc.sharepoint.com/sites/Revenue-Services/Shared%20Documents/General/FinanceData.xlsx",
        "sheet": None  # Default sheet
    },
    "tickets": {
        "url": "https://sparkc.sharepoint.com/sites/ProfessionalServicesGroup/Shared%20Documents/General/TicketsData.xlsx",
        "sheet": "Tickets"
    },
    "weekly_status_pdf": {
        "url": "https://sparkc.sharepoint.com/sites/ProfessionalServicesGroup/Shared%20Documents/General/WeeklyStatus.pdf"
    }
}

data_source = st.radio("Choose data source:", ("Use SharePoint Data", "Upload File", "Enter URL", "Use Default File"))
# df needs to be accessible globally for the chat function if it's to query data
# Initialize df as None or an empty DataFrame
df = pd.DataFrame() # Initialize as empty DataFrame

with st.container():
    if data_source == "Use SharePoint Data":
        if 'sharepoint_username' not in st.session_state or 'sharepoint_password' not in st.session_state:
            st.warning("Please enter SharePoint credentials in the sidebar to access the data.")
        else:
            # Load data based on the selected page
            if page == "Ops Review":
                with st.spinner("Loading Ops Review data from SharePoint..."):
                    df_loaded = read_excel_from_sharepoint(
                        SHAREPOINT_URLS["ops_review"]["url"], 
                        SHAREPOINT_URLS["ops_review"]["sheet"]
                    )
            elif page == "Finance":
                with st.spinner("Loading Finance data from SharePoint..."):
                    df_loaded = read_excel_from_sharepoint(
                        SHAREPOINT_URLS["finance"]["url"],
                        SHAREPOINT_URLS["finance"]["sheet"]
                    )
            elif page == "Tickets":
                with st.spinner("Loading Tickets data from SharePoint..."):
                    df_loaded = read_excel_from_sharepoint(
                        SHAREPOINT_URLS["tickets"]["url"],
                        SHAREPOINT_URLS["tickets"]["sheet"]
                    )
            else:
                # Default to Ops Review data for Chat Analytics
                with st.spinner("Loading data from SharePoint..."):
                    df_loaded = read_excel_from_sharepoint(
                        SHAREPOINT_URLS["ops_review"]["url"],
                        SHAREPOINT_URLS["ops_review"]["sheet"]
                    )
            
            if not df_loaded.empty:
                df = df_loaded
                st.success(f"Data loaded successfully from SharePoint for {page}!")
            else:
                st.error("Failed to load data from SharePoint.")
                st.markdown("""
                ### SharePoint Troubleshooting
                
                If you're having issues with SharePoint authentication:
                
                1. **Verify Credentials**: Double-check your username and password
                2. **Check URL Format**: Make sure you're using document library URLs, not sharing links 
                3. **File Permissions**: Ensure you have access permissions to the files
                4. **Modern Authentication**: Try using an app password if your account uses 2FA
                
                You can also use one of the other data source options below:
                """)
    elif data_source == "Upload File":
        uploaded_file = st.file_uploader("Upload a file", type=["csv", "xlsx", "xls"])
        if uploaded_file:
            try:
                if uploaded_file.name.endswith(('.xlsx', '.xls')):
                    df_loaded = pd.read_excel(uploaded_file)
                else:
                    df_loaded = pd.read_csv(uploaded_file, encoding="ISO-8859-1")
                df = df_loaded # Assign to the global df
                st.success("Data loaded successfully!")
            except Exception as e:
                st.error(f"Error: {e}")
                df = pd.DataFrame() # Reset df on error
    elif data_source == "Enter URL":
        url = st.text_input("Enter the URL of the CSV file:")
        if url:
            df_loaded = read_data_from_url(url)
            if df_loaded is not None:
                df = df_loaded # Assign to the global df
                st.success("Data loaded successfully from URL!")
            else:
                df = pd.DataFrame() # Reset df on error
    elif data_source == "Use Default File":
        try:
            default_file_path = "Data1.csv"
            if not os.path.exists(default_file_path):
                script_dir = os.path.dirname(__file__)
                default_file_path = os.path.join(script_dir, "Data1.csv")
            if os.path.exists(default_file_path):
                df_loaded = pd.read_csv(default_file_path)
                df = df_loaded # Assign to the global df
                st.success("Default data loaded.")
            else:
                st.error(f"Default file Data1.csv not found. Searched in: {os.path.abspath(default_file_path)}")
                df = pd.DataFrame() # Reset df
        except Exception as e:
            st.error(f"Error loading default file: {e}")
            df = pd.DataFrame() # Reset df

# Create a copy for filtering, so the original df remains for the chat
df_filtered = df.copy()

# ------------------ FILTERS ------------------
if not df_filtered.empty:
    df_filtered.columns = df_filtered.columns.str.strip().str.replace('ï»¿', '', regex=False)

    for col in ["Contract Start Date", "Contract End Date", "Project Start Date"]:
        if col in df_filtered.columns:
            df_filtered[col] = pd.to_datetime(df_filtered[col], errors='coerce')
    # Ensure string columns for filters
    for col in ["Exective", "Project Status (R/G/Y)", "Churn", "Customer Name", "Geography", "Application", "Customer Health"]:
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

    if "Exective" in df_filtered.columns:
        executives = sorted(df_filtered["Exective"].unique())
        exec_filter = st.sidebar.multiselect("Filter by Executive", options=executives, default=[])
        if exec_filter:
            df_filtered = df_filtered[df_filtered["Exective"].isin(exec_filter)]
        
    if "Project Status (R/G/Y)" in df_filtered.columns:
        status_unique = sorted(df_filtered["Project Status (R/G/Y)"].unique())
        status_filter = st.sidebar.multiselect("Filter by Project Status", options=status_unique, default=[])
        if status_filter:
            df_filtered = df_filtered[df_filtered["Project Status (R/G/Y)"].isin(status_filter)]

    # New Customer Health filter
    if "Customer Health" in df_filtered.columns:
        health_options = ["Green", "Yellow", "Red"]
        available_health = [h for h in health_options if h in df_filtered["Customer Health"].unique()]
        if available_health:
            health_filter = st.sidebar.multiselect("Filter by Customer Health", options=available_health, default=[])
            if health_filter:
                df_filtered = df_filtered[df_filtered["Customer Health"].isin(health_filter)]
    
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
        status_color_map = {
            "Red": "#d62728", "R": "#d62728", "Amber": "#ff7f0e", 
            "Yellow": "#ffdd57", "Y": "#ff7f0e", "Green": "#2ca02c", 
            "G": "#2ca02c", "Blank": "#cccccc", "<NA>": "#cccccc", "Unknown": "#cccccc"
        }
        st.markdown("## 🚀 Key Metrics")
        # ... (KPIs as before, using current_display_df)
        total_projects = current_display_df.shape[0]
        total_revenue = current_display_df["Revenue"].sum()
        total_churned = int(pd.to_numeric(current_display_df['Churn'], errors='coerce').fillna(0).sum())
        unique_customers = current_display_df["Customer Name"].nunique()
        sum_nrr = current_display_df["NRR"].sum()
        sum_total_usecases = current_display_df["Total Usecases/Module"].sum()
        sum_grr = current_display_df["GRR"].sum()
        sum_services_revenue = current_display_df["Services Revenue"].sum()

        kpi_cols = st.columns(7)
        kpi_cols[0].metric("Churned Projects", f"{total_churned:,}")
        kpi_cols[1].metric("Unique Customers", f"{unique_customers:,}")
        kpi_cols[2].metric("Sum of NRR", f"${sum_nrr:,.0f}")
        kpi_cols[3].metric("Sum of Revenue", f"${total_revenue:,.0f}")
        kpi_cols[4].metric("Sum of Usecases", f"{sum_total_usecases:,.0f}")
        kpi_cols[5].metric("Sum of GRR", f"${sum_grr:,.0f}")
        kpi_cols[6].metric("Sum Services Rev", f"${sum_services_revenue:,.0f}")

        st.markdown("---")
        st.markdown("## 📈 Visualizations")
        
        if "Geography" in current_display_df.columns and "Customer Name" in current_display_df.columns:
            # Get geography-customer data
            geo_cust_counts = current_display_df.groupby(["Geography", "Customer Name"], observed=True).size().reset_index(name="Count")
            if not geo_cust_counts.empty:
                # Fix for multiple customers - optimize visualization for scalability
                
                # Get top customers by count to limit visual clutter if there are many
                top_customers = current_display_df["Customer Name"].value_counts().nlargest(15).index.tolist()
                
                # If filters are active and we have fewer than 15 customers, use all of them
                selected_customers = cust_filter if 'cust_filter' in locals() and cust_filter else top_customers
                
                # Ensure we don't have too many or too few customers for visualization
                if len(selected_customers) > 15:
                    # Too many will be cluttered, so limit to top 15
                    viz_customers = selected_customers[:15]
                    st.info(f"Showing top 15 of {len(selected_customers)} selected customers in the visualization for clarity.")
                elif len(selected_customers) == 0:
                    # If no customers are explicitly selected, use top 10
                    viz_customers = top_customers[:10]
                else:
                    # Use the selected customers as is
                    viz_customers = selected_customers
                
                # Filter data for the visualization
                filtered_geo_cust = geo_cust_counts[geo_cust_counts["Customer Name"].isin(viz_customers)]
                
                # Create the stacked bar chart with improved layout
                fig_geo_cust_stacked = px.bar(
                    filtered_geo_cust,
                    x="Geography", 
                    y="Count", 
                    color="Customer Name",
                    title=f"Project Count by Geography and Customer ({len(viz_customers)} Customers)", 
                    barmode="stack"
                )
                
                # Improve layout for better readability with multiple customers
                fig_geo_cust_stacked.update_layout(
                    height=600,  # Taller chart for better visibility
                    legend=dict(
                        orientation="h",  # Horizontal legend
                        yanchor="bottom",
                        y=-0.3,  # Position below chart
                        xanchor="center",
                        x=0.5,
                        title=None  # No legend title needed
                    ),
                    margin=dict(b=150)  # Add bottom margin for legend
                )
                
                # If we have many customers, make the legend more compact
                if len(viz_customers) > 8:
                    fig_geo_cust_stacked.update_layout(
                        legend=dict(
                            font=dict(size=10)  # Smaller font for legend
                        )
                    )
                
                st.plotly_chart(fig_geo_cust_stacked, use_container_width=True)
            else: st.write("Not enough data for 'Project Count by Geography and Customer Name'.")
        else: st.write("Required columns ('Geography', 'Customer Name') not found.")

        # ... (Rest of Ops Review charts and content as before, using current_display_df) ...
        viz_row2_col1, viz_row2_col2 = st.columns(2)
        with viz_row2_col1:
            if "Exective" in current_display_df.columns:
                exec_counts = current_display_df["Exective"].value_counts().reset_index()
                exec_counts.columns = ["Exective", "Count"]
                if not exec_counts.empty:
                    fig_exec_donut = px.pie(
                        exec_counts, values="Count", names="Exective",
                        title="Project Count by Executive", hole=0.4
                    )
                    fig_exec_donut.update_traces(textinfo="percent+label")
                    fig_exec_donut.update_layout(height=400)
                    st.plotly_chart(fig_exec_donut, use_container_width=True)
                else: st.write("Not enough data for 'Project Count by Executive' donut chart.")
            else: st.write("Column 'Exective' not found for donut chart.")

        with viz_row2_col2:
            if "Exective" in current_display_df.columns and "Project Status (R/G/Y)" in current_display_df.columns:
                exec_status_counts = current_display_df.groupby(["Exective", "Project Status (R/G/Y)"], observed=True).size().reset_index(name="Count")
                if not exec_status_counts.empty:
                    fig_exec_status_bar = px.bar(
                        exec_status_counts, x="Exective", y="Count", color="Project Status (R/G/Y)",
                        title="Project Status by Executive", barmode="group", color_discrete_map=status_color_map
                    )
                    fig_exec_status_bar.update_layout(height=400)
                    st.plotly_chart(fig_exec_status_bar, use_container_width=True)
                else: st.write("Not enough data for 'Project Status by Executive' bar chart.")
            else: st.write("Required columns for 'Project Status by Executive' not found.")

        viz_row3_col1, viz_row3_col2 = st.columns(2)
        with viz_row3_col1:
            if "Project Status (R/G/Y)" in current_display_df.columns and not current_display_df["Project Status (R/G/Y)"].empty:
                status_values = current_display_df["Project Status (R/G/Y)"] 
                status_counts_df = status_values.value_counts().reset_index()
                status_counts_df.columns = ['Status', 'Count']
                fig_status_pie = px.pie(
                    status_counts_df, values="Count", names="Status", 
                    title="Overall Project Status Distribution", color="Status", color_discrete_map=status_color_map
                )
                fig_status_pie.update_traces(hoverinfo="label+percent+value", textinfo="percent+label")
                fig_status_pie.update_layout(height=400)
                st.plotly_chart(fig_status_pie, use_container_width=True)
            else: st.write("Not enough data for 'Project Status Distribution' chart.")
        
        with viz_row3_col2:
            if "Contract End Date" in current_display_df.columns and not current_display_df["Contract End Date"].isnull().all():
                contract_trend = current_display_df.groupby(current_display_df["Contract End Date"].dt.to_period("M")).size().reset_index(name="Contracts")
                contract_trend["Contract End Date"] = contract_trend["Contract End Date"].dt.to_timestamp()
                if not contract_trend.empty:
                    fig_contracts_time = px.line(
                        contract_trend, x="Contract End Date", y="Contracts",
                        title="Contracts Ending Over Time", markers=True, line_shape="spline"
                    )
                    fig_contracts_time.update_layout(height=400)
                    st.plotly_chart(fig_contracts_time, use_container_width=True)
                else:
                    st.write("Not enough data for 'Contracts Ending Over Time' chart.")
            else: st.write("Column 'Contract End Date' not found or empty for 'Contracts Ending Over Time' chart.")
        
        st.markdown("## 📝 Detailed Data Summary")
        # ... (Summary text code as before, using current_display_df for calculations)
        total_projects_sum = current_display_df.shape[0]
        total_revenue_sum = current_display_df["Revenue"].sum()
        total_churned_sum = int(pd.to_numeric(current_display_df['Churn'], errors='coerce').fillna(0).sum())
        churn_rate = (total_churned_sum / total_projects_sum) * 100 if total_projects_sum > 0 else 0
        avg_revenue = (total_revenue_sum / total_projects_sum) if total_projects_sum > 0 else 0
        top_exec_name = None
        top_exec_count_val = 0
        if "Exective" in current_display_df.columns and not current_display_df['Exective'].dropna().empty:
            top_exec_series = current_display_df["Exective"].value_counts()
            if not top_exec_series.empty:
                top_exec_name = top_exec_series.idxmax()
                top_exec_count_val = top_exec_series.max()
        status_dist_summary_text = "Not available"
        if "Project Status (R/G/Y)" in current_display_df.columns and not current_display_df["Project Status (R/G/Y)"].empty:
            status_counts_val = current_display_df["Project Status (R/G/Y)"].value_counts(normalize=True) * 100
            status_dist_dict = status_counts_val.to_dict()
            status_dist_summary_text = ", ".join([f"{k}: {v:.1f}%" for k, v in status_dist_dict.items()])
        summary_text_ops = f"""
        - Total projects analyzed: **{total_projects_sum:,}**
        - Total revenue from selection: **${total_revenue_sum:,.0f}**
        - Average revenue per project: **${avg_revenue:,.0f}**
        - Total churned projects in selection: **{total_churned_sum:,}** ({churn_rate:.2f}% churn rate)
        """
        if top_exec_name:
            summary_text_ops += f"- Top executive by project count: **{top_exec_name}** ({top_exec_count_val} projects)\n"
        summary_text_ops += f"- Project status distribution: {status_dist_summary_text}\n"
        st.markdown(summary_text_ops)

        st.markdown("---"); st.markdown("## 📄 Embedded Documents")
        st.markdown("### SharePoint Presentation")
        components.iframe(src="https://sparkc.sharepoint.com/:p:/s/ProfessionalServicesGroup/EV7F-1-nHr5BkrR6-MbTuPYBSISt1dQ9BdkuX3MUYm94NA?e=JOkhCh", height=450, width=1000, scrolling=True)
        
        st.markdown("### Weekly Project Status PDF")
        # Show PDF from SharePoint
        def show_sharepoint_pdf(url):
            if 'sharepoint_username' not in st.session_state or 'sharepoint_password' not in st.session_state:
                st.warning("Please authenticate with SharePoint using the sidebar to view the PDF.")
                return
                
            with st.spinner("Loading PDF from SharePoint..."):
                pdf_content = get_pdf_from_sharepoint(url)
                
                if pdf_content:
                    # Create a temp file to hold the PDF
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                        tmp_file.write(pdf_content)
                        tmp_path = tmp_file.name
                    
                    # Read and display the PDF
                    try:
                        with open(tmp_path, "rb") as f:
                            base64_pdf = base64.b64encode(f.read()).decode('utf-8')
                        st.markdown(f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="650" type="application/pdf" style="border: 1px solid #ddd;"></iframe>', unsafe_allow_html=True)
                        
                        # Also try to parse some info from the PDF
                        with open(tmp_path, "rb") as f:
                            try:
                                pdf_reader = PyPDF2.PdfReader(f)
                                num_pages = len(pdf_reader.pages)
                                first_page_text = pdf_reader.pages[0].extract_text()
                                
                                # Display basic PDF info
                                with st.expander("PDF Information"):
                                    st.write(f"Number of pages: {num_pages}")
                                    st.write("First page preview:")
                                    st.text(first_page_text[:500] + "...")
                            except Exception as e:
                                st.error(f"Could not parse PDF content: {str(e)}")
                        
                        # Clean up the temp file
                        os.unlink(tmp_path)
                    except Exception as e:
                        st.error(f"Error displaying PDF: {str(e)}")
                        if os.path.exists(tmp_path):
                            os.unlink(tmp_path)
                else:
                    st.error("Failed to retrieve PDF from SharePoint.")
        
        # Use the function to display SharePoint PDF
        show_sharepoint_pdf(SHAREPOINT_URLS["weekly_status_pdf"]["url"])
        
        # Legacy code for local PDF (as fallback)
        if 'sharepoint_username' not in st.session_state or 'sharepoint_password' not in st.session_state:
            st.warning("SharePoint authentication not provided. Falling back to local PDF if available.")
            # Original local PDF display function
            def show_local_pdf(pdf_file_path):
                script_dir = os.path.dirname(__file__)
                abs_pdf_file_path = os.path.join(script_dir, pdf_file_path)
                if not os.path.exists(abs_pdf_file_path): abs_pdf_file_path = os.path.abspath(pdf_file_path)
                if os.path.exists(abs_pdf_file_path):
                    with open(abs_pdf_file_path, "rb") as f: base64_pdf = base64.b64encode(f.read()).decode('utf-8')
                    st.markdown(f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="650" type="application/pdf" style="border: 1px solid #ddd;"></iframe>', unsafe_allow_html=True)
                else: st.error(f"PDF file '{pdf_file_path}' not found. Looked for: '{abs_pdf_file_path}'")
            
            show_local_pdf("Weekly Project Status 7.05.2025.pdf")

    elif page == "Tickets":
        st.title("🎫 Tickets Dashboard")
        st.markdown("Insights into support tickets and resolutions.")
        
        if not current_display_df.empty:
            # Key metrics
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
                # If no status column exists, show other metrics
                customers_with_tickets = current_display_df["Customer Name"].nunique() if "Customer Name" in current_display_df else 0
                ticket_kpi_row[1].metric("Customers with Tickets", f"{customers_with_tickets:,}")
                
                avg_revenue = current_display_df["Revenue"].mean() if "Revenue" in current_display_df and current_display_df['Revenue'].notna().any() else 0
                ticket_kpi_row[2].metric("Avg. Revenue", f"${avg_revenue:,.0f}")
            
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
        
        if not current_display_df.empty:
            # Add metric cards showing key KPIs
            st.markdown("### 📊 Key Financial KPIs")
            fin_kpi_row1 = st.columns(3)
            
            # GRR - Gross Retention Rate
            total_grr = current_display_df["GRR"].sum() if "GRR" in current_display_df.columns else 0
            fin_kpi_row1[0].metric(
                "Gross Retention Rate (GRR)", 
                f"${total_grr:,.0f}",
                delta=f"{(total_grr/current_display_df.shape[0]):,.2f} per project" if current_display_df.shape[0] > 0 else None
            )
            
            # NRR - Net Retention Rate
            total_nrr = current_display_df["NRR"].sum() if "NRR" in current_display_df.columns else 0
            fin_kpi_row1[1].metric(
                "Net Retention Rate (NRR)", 
                f"${total_nrr:,.0f}",
                delta=f"{(total_nrr/current_display_df.shape[0]):,.2f} per project" if current_display_df.shape[0] > 0 else None
            )
            
            # Revenue
            total_revenue_fin = current_display_df["Revenue"].sum() if "Revenue" in current_display_df.columns else 0
            fin_kpi_row1[2].metric(
                "Total Revenue", 
                f"${total_revenue_fin:,.0f}",
                delta=f"{(total_revenue_fin/current_display_df.shape[0]):,.2f} per project" if current_display_df.shape[0] > 0 else None
            )
            
            # Additional KPIs
            fin_kpi_row2 = st.columns(3)
            
            # Active Projects
            active_projects_fin = 0
            if "Project Status (R/G/Y)" in current_display_df.columns:
                active_projects_fin = current_display_df[current_display_df["Project Status (R/G/Y)"].astype(str).str.title().isin(["Green", "Amber", "G", "Y", "Yellow"])].shape[0]
            else: active_projects_fin = current_display_df.shape[0] 
            
            fin_kpi_row2[0].metric("Active Projects", f"{active_projects_fin:,}")
            
            # Services Revenue
            services_revenue = current_display_df["Services Revenue"].sum() if "Services Revenue" in current_display_df.columns else 0
            fin_kpi_row2[1].metric("Services Revenue", f"${services_revenue:,.0f}")
            
            # Total Customers
            total_customers = current_display_df["Customer Name"].nunique() if "Customer Name" in current_display_df.columns else 0
            fin_kpi_row2[2].metric("Total Customers", f"{total_customers:,}")
            
            st.markdown("---")
            st.markdown("### 📈 Revenue Analysis")
            
            # Revenue Trends Over Time
            if "Contract End Date" in current_display_df.columns and "Revenue" in current_display_df.columns and not current_display_df["Contract End Date"].isnull().all():
                st.subheader("Revenue Trends Over Time")
                # Group by month and sum revenue
                revenue_trend = current_display_df.groupby(current_display_df["Contract End Date"].dt.to_period("M"))["Revenue"].sum().reset_index()
                revenue_trend["Contract End Date"] = revenue_trend["Contract End Date"].dt.to_timestamp()
                
                if not revenue_trend.empty:
                    fig_revenue_trend = px.line(
                        revenue_trend, 
                        x="Contract End Date", 
                        y="Revenue",
                        title="Revenue by Contract End Date",
                        markers=True
                    )
                    fig_revenue_trend.update_layout(height=450)
                    st.plotly_chart(fig_revenue_trend, use_container_width=True)
                else:
                    st.write("Not enough data for Revenue Trends visualization.")
            
            # Customer-wise Revenue Distribution
            if "Revenue" in current_display_df.columns and "Customer Name" in current_display_df.columns and not current_display_df["Customer Name"].empty:
                st.subheader("Customer Revenue Distribution")
                revenue_by_customer = current_display_df.groupby("Customer Name", observed=True)["Revenue"].sum().reset_index()
                revenue_by_customer = revenue_by_customer.sort_values("Revenue", ascending=False).head(10)
                
                if not revenue_by_customer.empty:
                    fig_customer_revenue = px.bar(
                        revenue_by_customer, 
                        x="Customer Name", 
                        y="Revenue",
                        title="Top 10 Customers by Revenue",
                        color="Revenue",
                        color_continuous_scale="Viridis"
                    )
                    fig_customer_revenue.update_traces(
                        text=revenue_by_customer["Revenue"].apply(lambda x: f"${x:,.0f}"), 
                        textposition="outside"
                    )
                    fig_customer_revenue.update_layout(height=450)
                    st.plotly_chart(fig_customer_revenue, use_container_width=True)
                else:
                    st.write("Not enough data for Customer Revenue Distribution.")
                    
            # Revenue Distribution by Status
            if "Revenue" in current_display_df.columns and "Project Status (R/G/Y)" in current_display_df.columns:
                st.subheader("Revenue by Project Status")
                revenue_by_status = current_display_df.groupby("Project Status (R/G/Y)", observed=True)["Revenue"].sum().reset_index()
                
                if not revenue_by_status.empty:
                    # Status color map
                    status_color_map = {
                        "Red": "#d62728", "R": "#d62728", "Amber": "#ff7f0e", 
                        "Yellow": "#ffdd57", "Y": "#ff7f0e", "Green": "#2ca02c", 
                        "G": "#2ca02c", "Blank": "#cccccc", "<NA>": "#cccccc", "Unknown": "#cccccc"
                    }
                    
                    fig_status_revenue = px.pie(
                        revenue_by_status, 
                        names="Project Status (R/G/Y)", 
                        values="Revenue",
                        title="Revenue Distribution by Project Status",
                        color="Project Status (R/G/Y)",
                        color_discrete_map=status_color_map
                    )
                    fig_status_revenue.update_traces(textinfo="percent+label")
                    st.plotly_chart(fig_status_revenue, use_container_width=True)
                else:
                    st.write("Not enough data for Revenue by Project Status visualization.")
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