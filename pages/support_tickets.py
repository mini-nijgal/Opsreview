import streamlit as st
import plotly.express as px
import pandas as pd
import streamlit.components.v1 as components

def show_page(current_display_df):
    """Display the Support Tickets page"""
    
    st.title("🎫 Tickets Dashboard")
    st.markdown("Insights into support tickets and resolutions.")
    
    # Add Hubspot and Jira links in a prominent section
    display_integration_links()
    
    st.markdown("---")
    
    if not current_display_df.empty:
        # Key metrics for tickets
        display_ticket_metrics(current_display_df)
        
        st.markdown("---")
        
        # Ticket visualizations
        display_ticket_visualizations(current_display_df)
        
        # Google Sheets iframe
        display_google_sheets_iframe()
        
    else:
        st.warning("No data loaded/matches filters to display ticket information.")

def display_integration_links():
    """Display HubSpot, Jira, and APM integration links"""
    st.markdown("## 🔗 Ticket Integration Links")
    tickets_col1, tickets_col2, tickets_col3 = st.columns(3)
    
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
    
    with tickets_col3:
        st.markdown("""
        ### APM Tickets
        [Access APM Service Desk](https://sparkcognition.atlassian.net/jira/servicedesk/projects/RBS/queues/custom/567)
        """)
        st.components.v1.html(
            """
            <a href="https://sparkcognition.atlassian.net/jira/servicedesk/projects/RBS/queues/custom/567" 
               target="_blank" 
               style="display: inline-block; padding: 10px 20px; background-color: #00875a; color: white; 
               text-decoration: none; border-radius: 5px; font-weight: bold; margin-top: 10px;">
               Open APM Tickets
            </a>
            """, 
            height=60
        )

def display_ticket_metrics(current_display_df):
    """Display key ticket metrics"""
    st.markdown("### 📊 Ticket Metrics")
    ticket_kpi_row = st.columns(4)
    
    # Total tickets
    total_tickets = current_display_df.shape[0]
    ticket_kpi_row[0].metric("Total Tickets", f"{total_tickets:,}")
    
    # Status-based metrics (HubSpot uses "Status" column)
    status_col = get_status_column(current_display_df)
    
    if status_col and not current_display_df[status_col].empty:
        status_counts = current_display_df[status_col].value_counts()
        
        # Open/New tickets
        open_statuses = ["Open", "New", "In Progress", "Waiting", "new", "open", "in progress"]
        open_tickets = current_display_df[current_display_df[status_col].isin(open_statuses)].shape[0]
        ticket_kpi_row[1].metric("Open Tickets", f"{open_tickets:,}")
        
        # Closed tickets
        closed_statuses = ["Closed", "Resolved", "Solved", "closed", "resolved", "solved"]
        closed_tickets = current_display_df[current_display_df[status_col].isin(closed_statuses)].shape[0]
        ticket_kpi_row[2].metric("Closed Tickets", f"{closed_tickets:,}")
    else:
        ticket_kpi_row[1].metric("Open Tickets", "N/A")
        ticket_kpi_row[2].metric("Closed Tickets", "N/A")
    
    # Priority-based metrics
    priority_col = get_priority_column(current_display_df)
    
    if priority_col and not current_display_df[priority_col].empty:
        high_priority_values = ["High", "Critical", "Urgent", "high", "critical", "urgent"]
        high_priority = current_display_df[current_display_df[priority_col].isin(high_priority_values)].shape[0]
        ticket_kpi_row[3].metric("High Priority", f"{high_priority:,}")
    else:
        # Show recent tickets instead
        if "Created Date" in current_display_df.columns:
            recent_tickets = current_display_df[current_display_df["Created Date"] > pd.Timestamp.now() - pd.Timedelta(days=7)].shape[0]
            ticket_kpi_row[3].metric("Last 7 Days", f"{recent_tickets:,}")
        else:
            ticket_kpi_row[3].metric("Categories", f"{current_display_df['Category'].nunique() if 'Category' in current_display_df.columns else 'N/A'}")

def display_ticket_visualizations(current_display_df):
    """Display ticket analysis visualizations"""
    viz_col1, viz_col2 = st.columns(2)
    
    with viz_col1:
        display_ticket_status_chart(current_display_df)
    
    with viz_col2:
        display_ticket_priority_chart(current_display_df)
    
    # Tickets Over Time
    display_tickets_timeline(current_display_df)
    
    # Tickets by Category
    display_tickets_by_category(current_display_df)
    
    # Tickets by Application
    display_tickets_by_application(current_display_df)

def display_ticket_status_chart(current_display_df):
    """Display ticket status distribution chart"""
    status_col = get_status_column(current_display_df)
    
    if status_col and not current_display_df[status_col].empty:
        st.subheader("Ticket Status Distribution")
        status_counts = current_display_df[status_col].value_counts().reset_index()
        status_counts.columns = ["Status", "Count"]
        
        # Create color mapping for status
        status_color_map = {
            "Open": "#ff7f0e", "New": "#2ca02c", "In Progress": "#1f77b4",
            "Closed": "#d62728", "Resolved": "#9467bd", "Waiting": "#8c564b"
        }
        
        fig_status_pie = px.pie(
            status_counts,
            values="Count",
            names="Status",
            title="Ticket Status Distribution",
            color="Status",
            color_discrete_map=status_color_map
        )
        fig_status_pie.update_traces(textinfo="percent+label+value")
        st.plotly_chart(fig_status_pie, use_container_width=True)

def display_ticket_priority_chart(current_display_df):
    """Display ticket priority distribution chart"""
    priority_col = get_priority_column(current_display_df)
    
    if priority_col and not current_display_df[priority_col].empty:
        st.subheader("Ticket Priority Distribution")
        priority_counts = current_display_df[priority_col].value_counts().reset_index()
        priority_counts.columns = ["Priority", "Count"]
        
        # Create color mapping for priority
        priority_color_map = {
            "High": "#d62728", "Critical": "#ff0000", "Urgent": "#ff4500",
            "Medium": "#ff7f0e", "Normal": "#2ca02c", "Low": "#1f77b4"
        }
        
        fig_priority_donut = px.pie(
            priority_counts,
            values="Count",
            names="Priority",
            title="Ticket Priority Distribution",
            hole=0.4,
            color="Priority",
            color_discrete_map=priority_color_map
        )
        fig_priority_donut.update_traces(textinfo="percent+label+value")
        st.plotly_chart(fig_priority_donut, use_container_width=True)

def display_tickets_timeline(current_display_df):
    """Display tickets created over time"""
    if "Created Date" in current_display_df.columns:
        st.subheader("Tickets Created Over Time")
        
        # Group by date
        tickets_by_date = current_display_df.copy()
        tickets_by_date["Created Date"] = pd.to_datetime(tickets_by_date["Created Date"]).dt.date
        daily_tickets = tickets_by_date.groupby("Created Date").size().reset_index(name="Count")
        
        fig_timeline = px.line(
            daily_tickets,
            x="Created Date",
            y="Count",
            title="Daily Ticket Creation Trend",
            markers=True
        )
        fig_timeline.update_layout(height=400)
        st.plotly_chart(fig_timeline, use_container_width=True)

def display_tickets_by_category(current_display_df):
    """Display tickets by category"""
    if "Category" in current_display_df.columns and not current_display_df["Category"].empty:
        st.subheader("Tickets by Category")
        category_counts = current_display_df["Category"].value_counts().reset_index()
        category_counts.columns = ["Category", "Count"]
        
        fig_categories = px.bar(
            category_counts,
            x="Category",
            y="Count",
            title="Tickets by Category",
            color="Count",
            color_continuous_scale="Blues"
        )
        fig_categories.update_layout(height=400)
        st.plotly_chart(fig_categories, use_container_width=True)

def display_tickets_by_application(current_display_df):
    """Display tickets by application"""
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

def display_google_sheets_iframe():
    """Display Google Sheets Tickets tab iframe"""
    st.markdown("---")
    st.subheader("📋 Live Tickets Data from Google Sheets")
    
    # Embed Google Sheets Tickets tab - updated URL
    google_sheets_url = "https://docs.google.com/spreadsheets/d/1EXephHztcb8-vrqGSiqiVH2ieibbSRraiSwohw8sic4/edit?usp=sharing"
    
    st.components.v1.iframe(
        src=google_sheets_url,
        width=None,
        height=600,
        scrolling=True
    )
    
    st.markdown("*Live view of the Tickets tab from Google Sheets*")

# Helper functions
def get_status_column(df):
    """Get the status column name"""
    for col in ["Status", "Ticket Status", "hs_pipeline_stage"]:
        if col in df.columns:
            return col
    return None

def get_priority_column(df):
    """Get the priority column name"""
    for col in ["Priority", "Ticket Priority", "hs_ticket_priority"]:
        if col in df.columns:
            return col
    return None 