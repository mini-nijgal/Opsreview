import streamlit as st

def setup_authentication_ui():
    """Setup authentication UI in sidebar"""
    setup_sharepoint_auth()
    setup_hubspot_auth()

def setup_sharepoint_auth():
    """Setup SharePoint authentication (optional)"""
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

def setup_hubspot_auth():
    """Setup HubSpot authentication"""
    with st.sidebar.expander("HubSpot Configuration (For Tickets)", expanded=False):
        st.write("Configure HubSpot API access for tickets data")
        hubspot_api_key = st.text_input(
            "HubSpot API Key", 
            value=st.session_state.get('hubspot_api_key', ''),
            type="password",
            key="hubspot_key_input",
            help="Get your API key from HubSpot Settings > Integrations > API key"
        )
        
        if st.button("Save HubSpot Key"):
            st.session_state.hubspot_api_key = hubspot_api_key
            st.success("HubSpot API key saved for this session")
        
        st.markdown("### How to get HubSpot API Key:")
        st.markdown("""
        1. Go to your HubSpot account
        2. Navigate to Settings (gear icon)
        3. Go to Integrations > API key
        4. Create or copy your API key
        """) 