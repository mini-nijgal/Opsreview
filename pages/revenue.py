import streamlit as st
import plotly.express as px
import pandas as pd

def show_page(current_display_df):
    """Display the Revenue page"""
    
    st.title("💰 Revenue Analysis")
    st.markdown("Revenue performance and financial analysis dashboard.")
    
    # Debug: Show available columns
    if not current_display_df.empty:
        with st.expander("🔍 Debug: Available Columns", expanded=False):
            st.write("**Available columns in the data:**")
            st.write(list(current_display_df.columns))
            st.write("**Data shape:**", current_display_df.shape)
    
    # Show data source indicator for Revenue
    revenue_columns = ["Current ARR", "Contracted ARR", "Recognized ARR", "Services Revenue"]
    found_columns = [col for col in revenue_columns if col in current_display_df.columns]
    
    if found_columns:
        st.success(f"✅ Using standard Revenue data structure (Found: {', '.join(found_columns)})")
    else:
        st.warning("⚠️ Not using standard Revenue data structure")
        if not current_display_df.empty:
            st.info(f"💡 Looking for columns: {', '.join(revenue_columns)}")
    
    if not current_display_df.empty:
        # Clean numeric columns by removing currency symbols and converting to numeric
        current_display_df = clean_revenue_data(current_display_df)
        
        # Display key metrics
        display_revenue_metrics(current_display_df)
        
        st.markdown("---")
        st.markdown("### 📈 Revenue Analysis")
        
        # Display revenue visualizations
        display_revenue_visualizations(current_display_df)
        
    else:
        st.warning("No data loaded/matches filters to display revenue information.")

def clean_revenue_data(df):
    """Clean numeric columns by removing currency symbols and converting to numeric"""
    df = df.copy()
    numeric_columns_to_clean = ["Current ARR", "Contracted ARR", "Recognized ARR", "Services Revenue"]
    
    for col in numeric_columns_to_clean:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(r'[\$,]', '', regex=True), 
                errors='coerce'
            ).fillna(0)
    
    return df

def display_revenue_metrics(current_display_df):
    """Display key revenue KPIs"""
    st.markdown("### 📊 Key Revenue KPIs")
    
    # Determine which ARR column to use
    arr_column = "Current ARR" if "Current ARR" in current_display_df.columns else "Contracted ARR"
    
    rev_kpi_row1 = st.columns(4)
    
    # Current/Contracted ARR
    total_arr = current_display_df[arr_column].sum() if arr_column in current_display_df.columns else 0
    rev_kpi_row1[0].metric(
        f"Total {arr_column}", 
        f"${total_arr:,.0f}"
    )
    
    # Recognized ARR
    total_recognized_arr = current_display_df["Recognized ARR"].sum() if "Recognized ARR" in current_display_df.columns else 0
    rev_kpi_row1[1].metric(
        "Total Recognized ARR", 
        f"${total_recognized_arr:,.0f}"
    )
    
    # Services Revenue
    total_services_revenue = current_display_df["Services Revenue"].sum() if "Services Revenue" in current_display_df.columns else 0
    rev_kpi_row1[2].metric(
        "Total Services Revenue", 
        f"${total_services_revenue:,.0f}"
    )
    
    # Total Contracts
    total_contracts = current_display_df.shape[0]
    rev_kpi_row1[3].metric("Total Contracts", f"{total_contracts:,}")
    
    # Additional KPIs
    rev_kpi_row2 = st.columns(3)
    
    # Total Customers
    total_customers = current_display_df["Customer Name"].nunique() if "Customer Name" in current_display_df.columns else 0
    rev_kpi_row2[0].metric("Total Customers", f"{total_customers:,}")
    
    # ARR Recognition Rate
    arr_recognition_rate = (total_recognized_arr / total_arr * 100) if total_arr > 0 else 0
    rev_kpi_row2[1].metric("ARR Recognition Rate", f"{arr_recognition_rate:.1f}%")
    
    # Average Contract Value
    avg_contract_value = total_arr / total_customers if total_customers > 0 else 0
    rev_kpi_row2[2].metric("Avg Contract Value", f"${avg_contract_value:,.0f}")

def display_revenue_visualizations(current_display_df):
    """Display revenue analysis visualizations"""
    arr_column = "Current ARR" if "Current ARR" in current_display_df.columns else "Contracted ARR"
    
    # Revenue by Geography
    display_revenue_by_geography(current_display_df, arr_column)
    
    # Customer and Industry visualizations
    rev_viz_row1_col1, rev_viz_row1_col2 = st.columns(2)
    
    with rev_viz_row1_col1:
        display_top_customers_revenue(current_display_df, arr_column)
    
    with rev_viz_row1_col2:
        display_revenue_by_industry_or_application(current_display_df, arr_column)
    
    # Revenue trends over time
    display_revenue_trends(current_display_df, arr_column)
    
    # ARR vs Recognized ARR Analysis
    display_arr_recognition_analysis(current_display_df, arr_column)
    
    # Revenue by Application
    display_revenue_by_application(current_display_df, arr_column)

def display_revenue_by_geography(current_display_df, arr_column):
    """Display revenue by geography"""
    if "Geography" in current_display_df.columns and arr_column in current_display_df.columns:
        st.subheader(f"{arr_column} by Geography")
        geo_revenue = current_display_df.groupby("Geography", observed=True)[arr_column].sum().reset_index()
        geo_revenue = geo_revenue.sort_values(arr_column, ascending=False)
        
        if not geo_revenue.empty:
            fig_geo_revenue = px.bar(
                geo_revenue, 
                x="Geography", 
                y=arr_column,
                title=f"{arr_column} by Geography",
                color=arr_column,
                color_continuous_scale="Viridis"
            )
            fig_geo_revenue.update_traces(
                text=geo_revenue[arr_column].apply(lambda x: f"${x:,.0f}"), 
                textposition="outside"
            )
            fig_geo_revenue.update_layout(height=450)
            st.plotly_chart(fig_geo_revenue, use_container_width=True)
        else:
            st.write("Not enough data for Geography Revenue visualization.")

def display_top_customers_revenue(current_display_df, arr_column):
    """Display top customers by revenue"""
    if arr_column in current_display_df.columns and "Customer Name" in current_display_df.columns:
        st.subheader(f"Top 10 Customers by {arr_column}")
        revenue_by_customer = current_display_df.groupby("Customer Name", observed=True)[arr_column].sum().reset_index()
        revenue_by_customer = revenue_by_customer.sort_values(arr_column, ascending=False).head(10)
        
        if not revenue_by_customer.empty:
            fig_customer_revenue = px.bar(
                revenue_by_customer, 
                x="Customer Name", 
                y=arr_column,
                title=f"Top 10 Customers by {arr_column}",
                color=arr_column,
                color_continuous_scale="Greens"
            )
            fig_customer_revenue.update_traces(
                text=revenue_by_customer[arr_column].apply(lambda x: f"${x:,.0f}"), 
                textposition="outside"
            )
            fig_customer_revenue.update_layout(
                height=450,
                xaxis_tickangle=-45
            )
            st.plotly_chart(fig_customer_revenue, use_container_width=True)
        else:
            st.write("Not enough data for Customer Revenue Distribution.")

def display_revenue_by_industry_or_application(current_display_df, arr_column):
    """Display revenue by industry sector or application"""
    if arr_column in current_display_df.columns and "Industry Sector" in current_display_df.columns:
        st.subheader(f"{arr_column} by Industry Sector")
        revenue_by_industry = current_display_df.groupby("Industry Sector", observed=True)[arr_column].sum().reset_index()
        
        if not revenue_by_industry.empty:
            fig_industry_revenue = px.pie(
                revenue_by_industry, 
                names="Industry Sector", 
                values=arr_column,
                title=f"{arr_column} Distribution by Industry Sector"
            )
            fig_industry_revenue.update_traces(textinfo="percent+label")
            st.plotly_chart(fig_industry_revenue, use_container_width=True)
        else:
            st.write("Not enough data for Industry Sector visualization.")
    elif arr_column in current_display_df.columns and "Application" in current_display_df.columns:
        # Fallback to Application if Industry Sector not available
        st.subheader(f"{arr_column} by Application")
        revenue_by_app = current_display_df.groupby("Application", observed=True)[arr_column].sum().reset_index()
        
        if not revenue_by_app.empty:
            fig_app_revenue = px.pie(
                revenue_by_app, 
                names="Application", 
                values=arr_column,
                title=f"{arr_column} Distribution by Application"
            )
            fig_app_revenue.update_traces(textinfo="percent+label")
            st.plotly_chart(fig_app_revenue, use_container_width=True)
        else:
            st.write("Not enough data for Application visualization.")

def display_revenue_trends(current_display_df, arr_column):
    """Display revenue trends over time"""
    if "Contract Start Date" in current_display_df.columns and arr_column in current_display_df.columns and not current_display_df["Contract Start Date"].isnull().all():
        st.subheader("Revenue Trends Over Time")
        
        # Group by month and sum revenue
        revenue_trend = current_display_df.groupby(current_display_df["Contract Start Date"].dt.to_period("M"))[arr_column].sum().reset_index()
        revenue_trend["Contract Start Date"] = revenue_trend["Contract Start Date"].dt.to_timestamp()
        
        if not revenue_trend.empty:
            fig_revenue_trend = px.line(
                revenue_trend, 
                x="Contract Start Date", 
                y=arr_column,
                title=f"{arr_column} by Contract Start Date",
                markers=True
            )
            fig_revenue_trend.update_layout(height=450)
            st.plotly_chart(fig_revenue_trend, use_container_width=True)
        else:
            st.write("Not enough data for Revenue Trends visualization.")

def display_arr_recognition_analysis(current_display_df, arr_column):
    """Display ARR vs Recognized ARR analysis"""
    if arr_column in current_display_df.columns and "Recognized ARR" in current_display_df.columns:
        st.subheader("ARR Recognition Analysis")
        
        # Create scatter plot showing current vs recognized ARR
        fig_arr_scatter = px.scatter(
            current_display_df,
            x=arr_column,
            y="Recognized ARR",
            color="Geography" if "Geography" in current_display_df.columns else None,
            hover_data=["Customer Name"] if "Customer Name" in current_display_df.columns else None,
            title=f"{arr_column} vs Recognized ARR"
        )
        
        # Add diagonal line to show perfect recognition
        max_arr = max(current_display_df[arr_column].max(), current_display_df["Recognized ARR"].max())
        fig_arr_scatter.add_scatter(
            x=[0, max_arr],
            y=[0, max_arr],
            mode="lines",
            name="Perfect Recognition",
            line=dict(dash="dash", color="gray")
        )
        
        fig_arr_scatter.update_layout(height=450)
        st.plotly_chart(fig_arr_scatter, use_container_width=True)

def display_revenue_by_application(current_display_df, arr_column):
    """Display revenue by application"""
    if "Application" in current_display_df.columns and arr_column in current_display_df.columns:
        st.subheader(f"{arr_column} by Application")
        app_revenue = current_display_df.groupby("Application", observed=True)[arr_column].sum().reset_index()
        app_revenue = app_revenue.sort_values(arr_column, ascending=False)
        
        if not app_revenue.empty:
            fig_app_revenue = px.bar(
                app_revenue, 
                x="Application", 
                y=arr_column,
                title=f"{arr_column} by Application",
                color=arr_column,
                color_continuous_scale="Oranges"
            )
            fig_app_revenue.update_traces(
                text=app_revenue[arr_column].apply(lambda x: f"${x:,.0f}"), 
                textposition="outside"
            )
            fig_app_revenue.update_layout(height=450)
            st.plotly_chart(fig_app_revenue, use_container_width=True)
        else:
            st.write("Not enough data for Application Revenue visualization.") 