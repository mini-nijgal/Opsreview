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

# Authentication and configuration sections
auth_handler.setup_authentication_ui()

# ------------------ DATA LOADING ------------------

# Data source selection
data_source = st.radio("Choose data source:", ("Use Google Sheets Data", "Upload File", "Enter URL", "Use Default File"))

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