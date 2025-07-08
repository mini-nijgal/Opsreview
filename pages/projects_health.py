import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import os

def show_page(current_display_df):
    """Display the Projects & Customer Health page"""
    
    st.title("📊 Customer Health and Revenue Analysis Dashboard")
    
    # Show data source indicator
    if "Exective" in current_display_df.columns and "Project Status (R/G/Y)" in current_display_df.columns:
        st.success("✅ Using Data1.csv structure (Ops Review data)")
    else:
        st.warning("⚠️ Not using standard Ops Review data structure")
    
    if current_display_df.empty:
        st.warning("No data available to display.")
        return
    
    # Color mapping for status
    status_color_map = {
        "Red": "#d62728", "R": "#d62728", "Amber": "#ff7f0e", 
        "Yellow": "#ffdd57", "Y": "#ff7f0e", "Green": "#2ca02c", 
        "G": "#2ca02c", "Blank": "#cccccc", "<NA>": "#cccccc", "Unknown": "#cccccc"
    }

    # Data Overview & Key Insights
    display_key_metrics(current_display_df)
    
    # Status Distribution
    display_status_distribution(current_display_df)
    
    # Client Details by Executive
    display_client_details(current_display_df)
    
    st.markdown("---")
    st.markdown("## 📈 Visualizations")
    
    # Interactive World Map
    display_world_map(current_display_df)
    
    # Geography and Customer Health visualizations
    display_geography_analysis(current_display_df)
    
    # Project Status and Customer Health in same row
    display_status_and_health_analysis(current_display_df, status_color_map)
    
    # Executive Analysis
    display_executive_analysis(current_display_df, status_color_map)
    
    # Contract Analysis
    display_contract_analysis(current_display_df)
    
    # Embedded Documents
    display_embedded_documents()

def display_key_metrics(current_display_df):
    """Display key metrics section"""
    st.markdown("## 📝 Data Overview & Key Insights")
    
    # Calculate summary statistics
    total_projects_sum = current_display_df.shape[0]
    total_churned_sum = int(pd.to_numeric(current_display_df['Churn'], errors='coerce').fillna(0).sum()) if "Churn" in current_display_df.columns else 0
    churn_rate = (total_churned_sum / total_projects_sum) * 100 if total_projects_sum > 0 else 0
    unique_customers = current_display_df["Customer Name"].nunique() if "Customer Name" in current_display_df.columns else 0
    total_usecases = current_display_df["Total Usecases/Module"].sum() if "Total Usecases/Module" in current_display_df.columns else 0
    
    # Create metric cards
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

def display_status_distribution(current_display_df):
    """Display status distribution section"""
    st.markdown("---")
    
    status_col1, status_col2 = st.columns(2)
    
    with status_col1:
        st.markdown("### 📈 Status Distribution")
        
        status_col = get_status_column(current_display_df)
        if status_col and not current_display_df[status_col].empty:
            status_counts = current_display_df[status_col].value_counts()
            total_projects_sum = current_display_df.shape[0]
            
            for status, count in status_counts.items():
                percentage = (count / total_projects_sum) * 100
                
                if status in ["Green", "G"]:
                    emoji = "🟢"
                elif status in ["Yellow", "Y", "Amber", "A"]:
                    emoji = "🟡"
                elif status in ["Red", "R"]:
                    emoji = "🔴"
                else:
                    emoji = "⚪"
                
                st.markdown(f"{emoji} **{status}:** {count} projects ({percentage:.1f}%)")
        else:
            st.markdown("*No status information available*")
    
    with status_col2:
        st.write("")

def display_client_details(current_display_df):
    """Display client details by executive"""
    st.markdown("---")
    st.markdown("### 👥 Client Details by Executive")
    
    exec_col = get_executive_column(current_display_df)
    status_col = get_status_column(current_display_df)
    
    if exec_col and status_col and "Customer Name" in current_display_df.columns:
        client_col1, client_col2 = st.columns(2)
        executives = sorted(current_display_df[exec_col].unique())
        
        for i, exec_name in enumerate(executives):
            if pd.notna(exec_name):
                exec_data = current_display_df[current_display_df[exec_col] == exec_name]
                
                with client_col1 if i % 2 == 0 else client_col2:
                    st.markdown(f"**👤 {exec_name}**")
                    
                    for status in sorted(exec_data[status_col].unique()):
                        if pd.notna(status):
                            status_data = exec_data[exec_data[status_col] == status]
                            if not status_data.empty:
                                client_list = status_data["Customer Name"].value_counts()
                                
                                if status in ["Green", "G"]:
                                    status_emoji = "🟢"
                                elif status in ["Yellow", "Y", "Amber", "A"]:
                                    status_emoji = "🟡"
                                elif status in ["Red", "R"]:
                                    status_emoji = "🔴"
                                else:
                                    status_emoji = "⚪"
                                
                                st.markdown(f"&nbsp;&nbsp;{status_emoji} **{status}:** {', '.join(client_list.index)}")
                    
                    st.markdown("")
    else:
        st.info("Client details require Executive and Status columns to be available.")

def display_world_map(current_display_df):
    """Display interactive world map"""
    if "Geography - Location" in current_display_df.columns or "Geography" in current_display_df.columns:
        st.subheader("🌍 Interactive World Map - Global Project Distribution")
        
        # Location coordinates mapping
        location_coords = {
            'USA': {'lat': 39.8283, 'lon': -98.5795, 'country': 'United States'},
            'United States': {'lat': 39.8283, 'lon': -98.5795, 'country': 'United States'},
            'Houston, Texas': {'lat': 29.7604, 'lon': -95.3698, 'country': 'United States'},
            'Austin': {'lat': 30.2672, 'lon': -97.7431, 'country': 'United States'},
            'Texas': {'lat': 31.9686, 'lon': -99.9018, 'country': 'United States'},
            'Canada': {'lat': 56.1304, 'lon': -106.3468, 'country': 'Canada'},
            'Mumbai, India': {'lat': 19.0760, 'lon': 72.8777, 'country': 'India'},
            'Navi Mumbai': {'lat': 19.0330, 'lon': 73.0297, 'country': 'India'},
            'Chennai': {'lat': 13.0827, 'lon': 80.2707, 'country': 'India'},
            'Kolkata': {'lat': 22.5726, 'lon': 88.3639, 'country': 'India'},
            'Gujarat': {'lat': 23.0225, 'lon': 72.5714, 'country': 'India'},
            'Odissa': {'lat': 20.9517, 'lon': 85.0985, 'country': 'India'},
            'Pakistan': {'lat': 30.3753, 'lon': 69.3451, 'country': 'Pakistan'},
            'Saudi Arabia': {'lat': 23.8859, 'lon': 45.0792, 'country': 'Saudi Arabia'},
            'Singapore': {'lat': 1.3521, 'lon': 103.8198, 'country': 'Singapore'},
            'Austrialla': {'lat': -25.2744, 'lon': 133.7751, 'country': 'Australia'},
            'Australia': {'lat': -25.2744, 'lon': 133.7751, 'country': 'Australia'},
            'Ireland': {'lat': 53.1424, 'lon': -7.6921, 'country': 'Ireland'},
            'Finland': {'lat': 61.9241, 'lon': 25.7482, 'country': 'Finland'},
            'Colombia': {'lat': 4.5709, 'lon': -74.2973, 'country': 'Colombia'},
            'EU': {'lat': 54.5260, 'lon': 15.2551, 'country': 'Europe'},
            'NAM': {'lat': 45.0000, 'lon': -100.0000, 'country': 'North America'},
            'APAC': {'lat': 35.0000, 'lon': 105.0000, 'country': 'Asia Pacific'},
            'MEA': {'lat': 26.0667, 'lon': 50.5577, 'country': 'Middle East & Africa'},
            'LATAM': {'lat': -8.7832, 'lon': -55.4915, 'country': 'Latin America'}
        }
        
        # Prepare map data
        map_data = []
        location_col = "Geography - Location" if "Geography - Location" in current_display_df.columns else "Geography"
        
        for location in current_display_df[location_col].dropna().unique():
            location_str = str(location).strip()
            if location_str in location_coords:
                location_data = current_display_df[current_display_df[location_col] == location]
                project_count = len(location_data)
                customer_count = location_data["Customer Name"].nunique() if "Customer Name" in location_data.columns else 0
                
                customers = location_data["Customer Name"].unique() if "Customer Name" in location_data.columns else []
                customer_list = ", ".join(customers[:5])
                if len(customers) > 5:
                    customer_list += f" and {len(customers) - 5} more"
                
                status_col = get_status_column(current_display_df)
                status_info = ""
                if status_col and not location_data[status_col].empty:
                    status_counts = location_data[status_col].value_counts()
                    status_info = " | ".join([f"{status}: {count}" for status, count in status_counts.items()])
                
                map_data.append({
                    'location': location_str,
                    'lat': location_coords[location_str]['lat'],
                    'lon': location_coords[location_str]['lon'],
                    'country': location_coords[location_str]['country'],
                    'projects': project_count,
                    'customers': customer_count,
                    'customer_list': customer_list,
                    'status_info': status_info,
                    'size': min(project_count * 10, 100)
                })
        
        if map_data:
            map_df = pd.DataFrame(map_data)
            
            fig_map = px.scatter_geo(
                map_df,
                lat='lat',
                lon='lon',
                size='projects',
                color='projects',
                hover_name='location',
                hover_data={
                    'country': True,
                    'projects': True,
                    'customers': True,
                    'customer_list': True,
                    'status_info': True,
                    'lat': False,
                    'lon': False
                },
                color_continuous_scale='Viridis',
                size_max=50,
                title="🌍 Global Project Distribution"
            )
            
            fig_map.update_traces(
                marker=dict(line=dict(width=2, color='white'), opacity=0.8),
                hovertemplate="<b>%{hovertext}</b><br>" +
                              "Country: %{customdata[0]}<br>" +
                              "Projects: %{customdata[1]}<br>" +
                              "Customers: %{customdata[2]}<br>" +
                              "Customer List: %{customdata[3]}<br>" +
                              "Status: %{customdata[4]}<br>" +
                              "<extra></extra>"
            )
            
            fig_map.update_layout(
                title={'text': "🌍 Global Project Distribution", 'x': 0.5, 'xanchor': 'center'},
                height=650,
                geo=dict(
                    showframe=False, showcoastlines=True, coastlinecolor="#2E86AB",
                    coastlinewidth=2, showland=True, landcolor='#F8F9FA',
                    showocean=True, oceancolor='#E3F2FD', showlakes=True,
                    lakecolor='#E3F2FD', projection_type='natural earth', bgcolor='white'
                )
            )
            
            st.plotly_chart(fig_map, use_container_width=True)
            
            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Locations", len(map_df))
            with col2:
                st.metric("Total Projects", map_df['projects'].sum())
            with col3:
                st.metric("Total Customers", map_df['customers'].sum())
            with col4:
                top_location = map_df.loc[map_df['projects'].idxmax(), 'location']
                st.metric("Top Location", top_location)
            
            with st.expander("📍 View Detailed Location Breakdown"):
                display_df = map_df[['location', 'country', 'projects', 'customers', 'customer_list']].copy()
                display_df.columns = ['Location', 'Country/Region', 'Projects', 'Customers', 'Customer Names']
                display_df = display_df.sort_values('Projects', ascending=False)
                st.dataframe(display_df, use_container_width=True)
        else:
            st.info("No location data available for mapping.")

def display_geography_analysis(current_display_df):
    """Display geography analysis"""
    if "Geography" in current_display_df.columns:
        st.subheader("Clients by Geography")
        
        geo_clients = current_display_df.groupby("Geography")["Customer Name"].apply(
            lambda x: list(x.unique())
        ).reset_index()
        geo_clients["Client_Count"] = geo_clients["Customer Name"].apply(len)
        geo_clients["Client_Names"] = geo_clients["Customer Name"].apply(lambda x: ", ".join(x))
        
        if not geo_clients.empty:
            fig_geo_clients = px.bar(
                geo_clients,
                x="Geography",
                y="Client_Count",
                title="Number of Clients by Geography",
                color="Client_Count",
                color_continuous_scale="Viridis",
                hover_data=["Client_Names"]
            )
            
            fig_geo_clients.update_traces(
                text=geo_clients["Client_Count"],
                textposition="outside",
                hovertemplate="<b>%{x}</b><br>Number of Clients: %{y}<br>Clients: %{customdata[0]}<br><extra></extra>"
            )
            
            fig_geo_clients.update_layout(height=500, showlegend=False)
            st.plotly_chart(fig_geo_clients, use_container_width=True)
            
            with st.expander("View Client Details by Geography"):
                for _, row in geo_clients.iterrows():
                    st.write(f"**{row['Geography']}** ({row['Client_Count']} clients):")
                    st.write(f"  {row['Client_Names']}")
                    st.write("")

def display_status_and_health_analysis(current_display_df, status_color_map):
    """Display project status and customer health analysis in the same row"""
    viz_status_health_col1, viz_status_health_col2 = st.columns(2)
    
    # Project Status Distribution (Left Column)
    with viz_status_health_col1:
        status_col = get_status_column(current_display_df)
        
        if status_col and not current_display_df[status_col].empty:
            st.subheader("Project Status Distribution")
            status_counts_df = current_display_df[status_col].value_counts().reset_index()
            status_counts_df.columns = ['Status', 'Count']
            
            fig_status_pie = px.pie(
                status_counts_df, 
                values="Count", 
                names="Status", 
                title="Project Status Distribution",
                color="Status", 
                color_discrete_map=status_color_map
            )
            
            fig_status_pie.update_traces(
                textinfo="percent+label+value",
                textposition="auto",
                hovertemplate="<b>%{label}</b><br>Projects: %{value}<br>Percentage: %{percent}<br><extra></extra>"
            )
            
            fig_status_pie.update_layout(height=500)
            st.plotly_chart(fig_status_pie, use_container_width=True)
        else:
            st.write("Not enough data for Project Status Distribution chart.")
    
    # Customer Health Distribution (Right Column)
    with viz_status_health_col2:
        health_col = get_health_column(current_display_df)
        
        if health_col and not current_display_df[health_col].empty:
            st.subheader("Customer Health Distribution")
            health_counts = current_display_df[health_col].value_counts().reset_index()
            health_counts.columns = ["Health", "Count"]
            
            if not health_counts.empty:
                # Add detailed information for hover
                health_details = []
                for health_status in health_counts["Health"]:
                    health_data = current_display_df[current_display_df[health_col] == health_status]
                    
                    if "Customer Name" in current_display_df.columns:
                        client_list = health_data["Customer Name"].value_counts()
                        clients_text = ", ".join(client_list.index)
                    else:
                        clients_text = "No client data"
                    
                    exec_col = get_executive_column(current_display_df)
                    if exec_col:
                        exec_list = health_data[exec_col].value_counts()
                        executives_text = ", ".join(exec_list.index)
                    else:
                        executives_text = "No executive data"
                    
                    health_details.append({"clients": clients_text, "executives": executives_text})
                
                health_counts["Clients"] = [detail["clients"] for detail in health_details]
                health_counts["Executives"] = [detail["executives"] for detail in health_details]
                
                health_color_map = {
                    "Green": "#2ca02c", "Yellow": "#ffdd57", "Amber": "#ff7f0e",
                    "Red": "#d62728", "Good": "#2ca02c", "Fair": "#ff7f0e", "Poor": "#d62728"
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
                    hovertemplate="<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<br>Clients: %{customdata[0]}<br>Executives: %{customdata[1]}<br><extra></extra>"
                )
                
                fig_health_donut.update_layout(height=500)
                st.plotly_chart(fig_health_donut, use_container_width=True)
            else:
                st.write("Not enough data for Customer Health chart.")
        else:
            st.write("Customer Health column not found or empty.")

def display_executive_analysis(current_display_df, status_color_map):
    """Display executive analysis charts"""
    viz_row2_col1, viz_row2_col2 = st.columns(2)
    
    with viz_row2_col1:
        exec_col = get_executive_column(current_display_df)
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
                        all_clients = ", ".join(client_list.index)
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
                    hovertemplate="<b>%{label}</b><br>Projects: %{value}<br>Clients: %{customdata[0]}<br><extra></extra>"
                )
                fig_exec_donut.update_layout(height=400)
                st.plotly_chart(fig_exec_donut, use_container_width=True)
    
    with viz_row2_col2:
        exec_col = get_executive_column(current_display_df)
        status_col = get_status_column(current_display_df)
        
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
                        all_clients = ", ".join(client_list.index)
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
                fig_exec_status_bar.update_layout(height=400)
                st.plotly_chart(fig_exec_status_bar, use_container_width=True)

def display_contract_analysis(current_display_df):
    """Display contract end date analysis"""
    if "Contract End Date" in current_display_df.columns and not current_display_df["Contract End Date"].isnull().all():
        st.subheader("Projects by Contract End Date")
        
        contract_project_data = current_display_df[["Contract End Date", "Customer Name"]].dropna()
        
        if not contract_project_data.empty:
            contract_project_data["End_Year"] = contract_project_data["Contract End Date"].dt.year
            contract_trend_year = contract_project_data.groupby(["End_Year", "Customer Name"]).size().reset_index(name="Project_Count")
            
            # Maximize pastel colors, then add patterns on top when cycling through
            unique_customers = contract_trend_year["Customer Name"].unique()
            num_customers = len(unique_customers)
            
            # Beautiful distinct pastel colors (optimized for 15 unique solids)
            pastel_colors = [
                '#FFB3BA',  # Light pink
                '#BAFFC9',  # Light mint green  
                '#BAE1FF',  # Light sky blue
                '#FFFFBA',  # Light yellow
                '#FFD1BA',  # Light peach
                '#E1BAFF',  # Light lavender
                '#FFBAF3',  # Light magenta
                '#C9FFBA',  # Light lime
                '#BABFFF',  # Light periwinkle
                '#F3FFBA',  # Light cream
                '#FFBAC9',  # Light coral
                '#BAFFE1',  # Light aqua
                '#D1BAFF',  # Light purple
                '#FFF3BA',  # Light lemon
                '#FFBAD1'   # Light rose
            ]
            
            # Clean, professional patterns for when we cycle through colors
            patterns = ["", ".", "/", "\\", "|", "+", "x"]  # Solid first, then patterns
            
            # Smart assignment: use all pastels first, then add patterns on top
            customer_colors = {}
            customer_patterns = {}
            
            for i, customer in enumerate(unique_customers):
                # Assign pastel color (cycle through the full palette)
                color_index = i % len(pastel_colors)
                customer_colors[customer] = pastel_colors[color_index]
                
                # Assign pattern: solid for first 15, then patterns for 16+
                if i < 15:
                    # First 15 customers - all solid pastels
                    customer_patterns[customer] = ""
                else:
                    # Customer 16+ - cycle through pastels with patterns
                    pattern_round = (i - 15) // len(pastel_colors)
                    pattern_index = (pattern_round % (len(patterns) - 1)) + 1  # Skip solid pattern ""
                    customer_patterns[customer] = patterns[pattern_index]
            
            # Add pattern column to dataframe
            contract_trend_year['Pattern'] = contract_trend_year['Customer Name'].map(customer_patterns)
            
            fig_contracts_stacked = px.bar(
                contract_trend_year,
                x="End_Year",
                y="Project_Count", 
                color="Customer Name",
                pattern_shape="Pattern",
                title="🎯 Projects by Contract End Date (Stacked)",
                barmode="stack",
                color_discrete_map=customer_colors
            )
            
            # Enhanced styling: Keep pastel colors as background with visible patterns
            fig_contracts_stacked.update_traces(
                marker=dict(
                    line=dict(color='white', width=2),  # White borders around all bars
                    pattern=dict(
                        fillmode='overlay',  # Overlay pattern on pastel color
                        fgcolor='rgba(0,0,0,0.6)',  # Semi-transparent dark pattern lines
                        size=10,  # Slightly larger pattern size for visibility
                        solidity=0.4  # Pattern density
                    )
                )
            )
            
            fig_contracts_stacked.update_layout(
                height=500,
                xaxis_title="Contract End Year",
                yaxis_title="Number of Projects",
                margin=dict(l=50, r=150, t=50, b=50)
            )
            
            if len(contract_trend_year["End_Year"].unique()) > 1:
                year_range = contract_trend_year["End_Year"].max() - contract_trend_year["End_Year"].min()
                fig_contracts_stacked.update_xaxes(
                    tickmode="linear",
                    dtick=1 if year_range <= 10 else 2
                )
            
            st.plotly_chart(fig_contracts_stacked, use_container_width=True)

def display_embedded_documents():
    """Display embedded PDF documents"""
    st.markdown("---")
    st.markdown("## 📄 Weekly Project Status Documents")
    
    # PDF information
    pdf_files = {
        "Weekly Project Status 7.05.2025": "Weekly%20Project%20Status%207.05.2025.pdf",
        "Weekly Project Status 4June2025": "Weekly%20Project%20Status%204June2025.pdf"
    }
    
    # Display available documents
    st.markdown("### 📊 Available Status Reports")
    
    # PDF viewer state
    if "selected_pdf_viewer" not in st.session_state:
        st.session_state.selected_pdf_viewer = None

    for pdf_name, pdf_file in pdf_files.items():
        # Create GitHub raw URL for download
        github_url = f"https://github.com/mini-nijgal/Opsreview/raw/main/{pdf_file}"
        
        # Create a nice display for each PDF
        with st.container():
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                st.markdown(f"**📋 {pdf_name}**")
                st.caption("Project status report with comprehensive metrics and updates")
            
            with col2:
                # View PDF button that embeds inline
                if st.button(f"🔗 View PDF", key=f"view_{pdf_name}", use_container_width=True):
                    st.session_state.selected_pdf_viewer = (pdf_name, github_url)
                    st.rerun()
                
            with col3:
                # Download link
                st.markdown(f"[💾 **Download**]({github_url})")
    
    # Display embedded PDF viewer if selected
    if st.session_state.selected_pdf_viewer:
        pdf_name, pdf_url = st.session_state.selected_pdf_viewer
        
        st.markdown("---")
        col1, col2 = st.columns([4, 1])
        
        with col1:
            st.markdown(f"### 📖 Viewing: {pdf_name}")
        
        with col2:
            if st.button("❌ Close Viewer", use_container_width=True):
                st.session_state.selected_pdf_viewer = None
                st.rerun()
        
        # Embed PDF using Google Docs viewer
        viewer_url = f"https://docs.google.com/viewer?url={pdf_url}&embedded=true"
        
        st.markdown(f"""
        <div style="border: 1px solid #ddd; border-radius: 10px; overflow: hidden; margin: 10px 0;">
            <iframe src="{viewer_url}" 
                    width="100%" 
                    height="600" 
                    style="border: none;">
                <p>Your browser does not support iframes. 
                   <a href="{pdf_url}" target="_blank">Click here to view the PDF</a>
                </p>
            </iframe>
        </div>
        """, unsafe_allow_html=True)
        
        # Alternative viewing options
        st.markdown("**Alternative viewing options:**")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown(f"[🔗 **Open in New Tab**]({pdf_url})")
        
        with col2:
            st.markdown(f"[📱 **Mobile View**](https://docs.google.com/viewer?url={pdf_url})")
            
        with col3:
            st.markdown(f"[💾 **Download PDF**]({pdf_url})")
    
    # Instructions
    st.markdown("---")
    st.info("""
    📌 **How to view PDFs:**
    - Click **"🔗 View PDF"** to open inline viewer below (no popup!)
    - Click **"💾 Download"** to save the file locally
    - Use **"❌ Close Viewer"** to hide the embedded PDF
    - Alternative viewing options provided when PDF is open
    """)
    
    # Alternative: Show PDF selector with direct links
    st.markdown("### 🔍 Quick Access")
    selected_pdf = st.selectbox(
        "Select a report to view:",
        list(pdf_files.keys()),
        help="Choose a weekly status report"
    )
    
    if selected_pdf:
        selected_url = f"https://github.com/mini-nijgal/Opsreview/raw/main/{pdf_files[selected_pdf]}"
        
        # Large, prominent buttons
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            # Use the same embedded viewer for consistency
            if st.button(f"🔗 View {selected_pdf}", key="quick_view", use_container_width=True):
                st.session_state.selected_pdf_viewer = (selected_pdf, selected_url)
                st.rerun()
        
        with col2:
            st.markdown(f"""
            <a href="{selected_url}" download>
                <button style="
                    background-color: #2196F3;
                    border: none;
                    color: white;
                    padding: 10px 20px;
                    text-align: center;
                    font-size: 16px;
                    margin: 4px 2px;
                    cursor: pointer;
                    border-radius: 8px;
                    width: 100%;
                ">💾 Download PDF</button>
            </a>
            """, unsafe_allow_html=True)
        
        with col3:
            # Show URL for debugging
            st.code(selected_url, language=None)

# Helper functions
def get_executive_column(df):
    """Get the executive column name"""
    if "Exective" in df.columns:
        return "Exective"
    elif "Owner" in df.columns:
        return "Owner"
    return None

def get_status_column(df):
    """Get the status column name"""
    if "Project Status (R/G/Y)" in df.columns:
        return "Project Status (R/G/Y)"
    elif "Status (R/G/Y)" in df.columns:
        return "Status (R/G/Y)"
    return None

def get_health_column(df):
    """Get the customer health column name"""
    for col in df.columns:
        if "customer health" in col.lower():
            return col
    return None 