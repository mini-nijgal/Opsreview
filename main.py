import streamlit as st
import pandas as pd
import warnings
import base64
import os
import requests
import io
from datetime import datetime

# Import page modules with error handling
try:
    from pages import projects_health, support_tickets, dinh_kyle_sheet, revenue, chat_analytics
    from utils import data_loader, auth_handler
except ImportError as e:
    st.error(f"Import error: {e}")
    st.error("Please ensure all required modules are present in the repository.")
    st.stop()

warnings.filterwarnings('ignore')

# ------------------ CONFIG ------------------
st.set_page_config(page_title="Avathon Analytics Dashboard", page_icon="📊", layout="wide")

# Hide Streamlit's default navigation and header
st.markdown("""
<style>
    /* Hide the main menu */
    #MainMenu {visibility: hidden;}
    
    /* Hide the header */
    header {visibility: hidden;}
    
    /* Hide the footer */
    footer {visibility: hidden;}
    
    /* Hide the "Made with Streamlit" footer */
    .css-1lsmgbg {display: none;}
    
    /* Hide any navigation elements above sidebar */
    .css-1d391kg, .css-1lcbmhc, .css-1outpf7 {display: none;}
    
    /* Hide the top navigation bar */
    .stSelectbox > label {display: none;}
    section[data-testid="stSidebar"] > div:first-child {margin-top: 0px;}
    
    /* Additional hiding for navigation elements */
    [data-testid="stSidebarNav"] {display: none;}
    section[data-testid="stSidebarNav"] {display: none;}
    .css-1cypcdb {display: none;}
    .css-1outpf7 {display: none;}
    
    /* Remove padding from top of sidebar */
    .css-1d391kg {padding-top: 0rem;}
    
    /* Hide any automatic page navigation */
    nav[role="navigation"] {display: none;}
    .stSidebarNav {display: none;}
    
</style>
""", unsafe_allow_html=True)

# Initialize session state for chat
if "messages" not in st.session_state:
    st.session_state.messages = []

# Initialize session state for authentication
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "username" not in st.session_state:
    st.session_state.username = ""

# Initialize session state for data source selections per page
if "page_data_sources" not in st.session_state:
    st.session_state.page_data_sources = {}

# ------------------ AUTHENTICATION ------------------

def show_login_page():
    """Display login page"""
    st.markdown(
        '<div style="text-align: center; margin-bottom: 50px; margin-top: 50px;">'
        '<h1 style="color: #1f77b4; font-family: Arial Black;">🚀 Avathon Service Analytics Dashboard</h1>'
        '<p style="font-size: 18px; color: #666;">Secure Access Portal</p>'
        '</div>',
        unsafe_allow_html=True
    )
    
    # Login form
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.container():
            st.markdown("### 🔐 Please Login to Continue")
            
            with st.form("login_form"):
                username = st.text_input("👤 Username", placeholder="Enter your username")
                password = st.text_input("🔒 Password", type="password", placeholder="Enter your password")
                login_button = st.form_submit_button("🚀 Login", use_container_width=True)
                
                if login_button:
                    # Simple authentication - you can modify these credentials
                    valid_credentials = {
                        "admin": "password123",
                        "user": "user123",
                        "demo": "demo123",
                        "avathon": "avathon2025"
                    }
                    
                    if username in valid_credentials and password == valid_credentials[username]:
                        st.session_state.authenticated = True
                        st.session_state.username = username
                        st.success("✅ Login successful! Redirecting...")
                        st.rerun()
                    else:
                        st.error("❌ Invalid username or password. Please try again.")
            
            # Show demo credentials
           

def show_logout_option():
    """Show logout option in sidebar"""
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"👤 **Logged in as:** {st.session_state.username}")
    
    if st.sidebar.button("🚪 Logout", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.username = ""
        st.rerun()

# Check authentication status
if not st.session_state.authenticated:
    show_login_page()
    st.stop()  # Stop execution here if not authenticated

# ------------------ SIDEBAR SETUP ------------------

# Display logo at top of sidebar
def display_sidebar_animated_gif(gif_path, width=250):
    """Display animated GIF in sidebar using HTML"""
    try:
        with open(gif_path, "rb") as gif_file:
            contents = gif_file.read()
            data_url = base64.b64encode(contents).decode("utf-8")
        
        st.sidebar.markdown(
            f'<div style="display: flex; justify-content: center; margin-bottom: 30px; margin-top: 10px;">'
            f'<img src="data:image/gif;base64,{data_url}" width="{width}" style="border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">'
            f'</div>',
            unsafe_allow_html=True
        )
        return True
    except Exception as e:
        st.sidebar.error(f"Could not load logo: {str(e)}")
        return False

# Display logo or fallback
logo_path = "Untitled design.gif"
if os.path.exists(logo_path):
    display_sidebar_animated_gif(logo_path, width=250)
else:
    st.sidebar.markdown(
        '<div style="text-align: center; margin-bottom: 30px; margin-top: 10px;">'
        '<h3 style="color: #1f77b4; font-family: Arial Black;">🚀 Avathon Analytics</h3>'
        '</div>',
        unsafe_allow_html=True
    )

# Navigation
st.sidebar.title("Navigation")
page = st.sidebar.selectbox(
    "Go to",
    ("Projects & Customer Health", "Support Tickets", "Dinh and Kyle Sheet", "Revenue", "Chat Analytics")
)

# Show logout option
show_logout_option()

# Authentication and configuration sections
auth_handler.setup_authentication_ui()

# ------------------ DATA LOADING ------------------

# Page-specific default data sources
page_defaults = {
    "Projects & Customer Health": "Use Google Sheets Data",
    "Support Tickets": "Use Default File", 
    "Revenue": "Use Default File",
    "Dinh and Kyle Sheet": "Use Default File",
    "Chat Analytics": "Use Default File"
}

# Get default for current page (use stored preference or page default)
if page in st.session_state.page_data_sources:
    current_default = st.session_state.page_data_sources[page]
else:
    current_default = page_defaults.get(page, "Use Default File")

# Data source selection with page-specific default
data_source_options = ("Use Google Sheets Data", "Upload File", "Enter URL", "Use Default File")
default_index = data_source_options.index(current_default)

data_source = st.radio(
    f"Choose data source for {page}:", 
    data_source_options,
    index=default_index,
    help=f"Default for {page}: {page_defaults.get(page, 'Use Default File')}"
)

# Store the user's selection for this page
st.session_state.page_data_sources[page] = data_source

# Load data based on selected source and page
df, df_filtered = data_loader.load_data(data_source, page)

# Apply filters
if not df_filtered.empty:
    df_filtered = data_loader.apply_filters(df_filtered)

# ------------------ PAGE ROUTING ------------------

# Route to appropriate page based on selection
if not df_filtered.empty or page == "Chat Analytics":
    if page == "Projects & Customer Health":
        projects_health.show_page(df_filtered)
    elif page == "Support Tickets":
        support_tickets.show_page(df_filtered)
    elif page == "Dinh and Kyle Sheet":
        dinh_kyle_sheet.show_page()
    elif page == "Revenue":
        revenue.show_page(df_filtered)
    elif page == "Chat Analytics":
        chat_analytics.show_page(df)
    
    # Common Footer
    st.markdown("---")
    st.markdown(
        """<div style='text-align: center; color: #333; font-size: 14px;'><small>© 2025 Avathon Analytics | Internal</small></div>""",
        unsafe_allow_html=True,
    )

# Handle empty data scenarios
elif df.empty and (data_source != "Upload File" or (data_source == "Upload File" and ('uploaded_file' not in locals() or uploaded_file is None))):
    if page == "Chat Analytics":
        chat_analytics.show_page(pd.DataFrame())
    else:
        st.info("Please load a dataset using one of the options at the top to view the dashboard.")
elif not df.empty and df_filtered.empty:
    st.warning("No data matches the current filter criteria. Please adjust your filters in the sidebar.")
    if page == "Chat Analytics":
        chat_analytics.show_page(df) 