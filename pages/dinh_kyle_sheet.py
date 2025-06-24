import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import os

def show_page():
    """Display the Dinh and Kyle Sheet page"""
    
    st.title("📊 Dinh and Kyle Sheet")
    st.markdown("Financial performance analysis using May 2025 Revenue data.")
    
    # Load May 2025 Excel file
    may_excel_data = load_may_revenue_excel()
    
    if may_excel_data:
        st.success(f"✅ May 2025 Revenue Excel loaded with {len(may_excel_data)} sheets")
        
        # Sheet selector
        selected_sheet = st.selectbox("Select sheet to analyze:", list(may_excel_data.keys()))
        
        if selected_sheet and selected_sheet in may_excel_data:
            sheet_df = may_excel_data[selected_sheet]
            
            if not sheet_df.empty:
                st.subheader(f"📊 {selected_sheet} - May 2025 Revenue Excel")
                
                # Create Excel-like embedded view
                excel_html = create_excel_embed(sheet_df, selected_sheet)
                st.components.v1.html(excel_html, height=750, scrolling=True)
                
                # Add a simple info section below
                st.markdown("---")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.info(f"**Rows:** {len(sheet_df)}")
                with col2:
                    st.info(f"**Columns:** {len(sheet_df.columns)}")
                with col3:
                    st.info(f"**Sheet:** {selected_sheet}")
                
            else:
                st.warning(f"Sheet '{selected_sheet}' is empty")
    else:
        st.info("💡 Add 'May'25 Revenue.xlsx' file to the same directory as dashboard.py to see May 2025 financial analysis")

def load_may_revenue_excel():
    """Load May 2025 Excel file"""
    try:
        excel_file_path = os.path.join(os.path.dirname(__file__), "..", "May'25 Revenue.xlsx")
        if os.path.exists(excel_file_path):
            # Load all sheets
            excel_data = {}
            with pd.ExcelFile(excel_file_path) as xls:
                for sheet_name in xls.sheet_names:
                    excel_data[sheet_name] = pd.read_excel(excel_file_path, sheet_name=sheet_name)
            return excel_data
        else:
            st.warning(f"Excel file 'May'25 Revenue.xlsx' not found in {os.path.dirname(excel_file_path)}")
            return None
    except Exception as e:
        st.error(f"Error loading May 2025 Excel file: {e}")
        return None

def create_excel_embed(df, sheet_name):
    """Create an Excel-like HTML table embed"""
    # Convert DataFrame to HTML with Excel-like styling
    html_table = df.to_html(
        index=True,
        classes='excel-table',
        table_id='excel-embed',
        escape=False,
        border=0
    )
    
    # Add Excel-like CSS styling
    excel_css = """
    <style>
    .excel-table {
        border-collapse: collapse;
        width: 100%;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        font-size: 12px;
        background-color: white;
        border: 1px solid #d0d7de;
    }
    .excel-table th {
        background-color: #f6f8fa;
        border: 1px solid #d0d7de;
        padding: 8px 12px;
        text-align: left;
        font-weight: 600;
        color: #24292f;
    }
    .excel-table td {
        border: 1px solid #d0d7de;
        padding: 6px 12px;
        text-align: left;
        background-color: white;
    }
    .excel-table tr:nth-child(even) td {
        background-color: #f6f8fa;
    }
    .excel-table tr:hover td {
        background-color: #e6f3ff;
    }
    #excel-container {
        max-height: 700px;
        overflow: auto;
        border: 2px solid #d0d7de;
        border-radius: 6px;
        background-color: white;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .excel-header {
        background-color: #0969da;
        color: white;
        padding: 10px 15px;
        font-weight: bold;
        border-radius: 4px 4px 0 0;
        margin-bottom: 0;
    }
    </style>
    """
    
    # Combine CSS and HTML
    excel_embed = f"""
    {excel_css}
    <div class="excel-header">📊 {sheet_name} - Excel Sheet View</div>
    <div id="excel-container">
        {html_table}
    </div>
    """
    
    return excel_embed 