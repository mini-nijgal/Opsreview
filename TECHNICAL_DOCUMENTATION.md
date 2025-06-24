# Avathon Analytics Dashboard - Technical Documentation

## Table of Contents
1. [Application Architecture](#application-architecture)
2. [Main Application Structure](#main-application-structure)
3. [Page Modules Documentation](#page-modules-documentation)
4. [Utility Modules](#utility-modules)
5. [Data Flow & Integration](#data-flow--integration)
6. [Deployment & Configuration](#deployment--configuration)

---

## Application Architecture

### Overview
The Avathon Analytics Dashboard is a multi-page Streamlit application built with a modular architecture. It provides comprehensive business intelligence across project health, support tickets, revenue analysis, and AI-powered analytics.

### Technology Stack
- **Frontend**: Streamlit (Python web framework)
- **Data Processing**: Pandas, NumPy
- **Visualization**: Plotly Express
- **AI Integration**: Hugging Face, OpenAI, Anthropic Claude
- **Data Sources**: Google Sheets API, HubSpot API, CSV files
- **Authentication**: Custom API key management

### Project Structure
```
├── main.py                 # Main application entry point
├── dashboard.py           # Compatibility layer for deployment
├── pages/                 # Page modules
│   ├── projects_health.py # Project & customer health analytics
│   ├── support_tickets.py # Ticket management & analysis
│   ├── revenue.py         # Financial performance analytics
│   ├── chat_analytics.py  # AI-powered conversational analytics
│   └── dinh_kyle_sheet.py # Embedded Google Sheets
├── utils/                 # Utility modules
│   ├── data_loader.py     # Data loading & management
│   └── auth_handler.py    # Authentication management
└── requirements.txt       # Python dependencies
```

---

## Main Application Structure

### File: `main.py`
**Purpose**: Entry point and routing controller for the entire dashboard

#### Key Components:

##### 1. Configuration & Styling
```python
st.set_page_config(page_title="Avathon Analytics Dashboard", page_icon="📊", layout="wide")
```
- Wide layout configuration for better data visualization
- Custom CSS injection to hide Streamlit default elements
- Brand-consistent styling and navigation

##### 2. Logo Display System
```python
def display_sidebar_animated_gif(gif_path, width=250):
    with open(gif_path, "rb") as gif_file:
        contents = gif_file.read()
        data_url = base64.b64encode(contents).decode("utf-8")
```
**Functionality:**
- Converts GIF to base64 for embedding
- Provides fallback text logo if file loading fails
- Custom HTML/CSS styling for professional appearance

##### 3. Navigation & Routing
```python
page = st.sidebar.selectbox("Go to", ("Projects & Customer Health", "Support Tickets", ...))
```
**Routing Logic:**
- Sidebar-based navigation menu
- Dynamic page routing to module functions
- State preservation across navigation

##### 4. Data Management
- Multi-source data loading integration
- Dynamic filtering system
- Page-specific data requirements handling

---

## Page Modules Documentation

## 1. Projects & Customer Health (`projects_health.py`)

### Purpose
Comprehensive project and customer health analytics dashboard providing insights into project status, customer health, geographic distribution, and executive performance.

### Key Functions & Code Analysis

#### `show_page(current_display_df)`
**Main Entry Point**
```python
def show_page(current_display_df):
    st.title("📊 Customer Health and Revenue Analysis Dashboard")
    
    # Data validation
    if "Exective" in current_display_df.columns and "Project Status (R/G/Y)" in current_display_df.columns:
        st.success("✅ Using Data1.csv structure (Ops Review data)")
    else:
        st.warning("⚠️ Not using standard Ops Review data structure")
```
**Functionality:**
- Validates incoming data structure for operations review compatibility
- Orchestrates all dashboard components in logical flow
- Handles empty data scenarios with user-friendly messages

#### `display_status_and_health_analysis()`
**Combined Chart Display**
```python
def display_status_and_health_analysis(current_display_df, status_color_map):
    viz_status_health_col1, viz_status_health_col2 = st.columns(2)
    
    # Project Status Distribution (Left)
    with viz_status_health_col1:
        fig_status_pie = px.pie(status_counts_df, values="Count", names="Status")
    
    # Customer Health Distribution (Right)  
    with viz_status_health_col2:
        fig_health_donut = px.pie(health_counts, values="Count", names="Health", hole=0.4)
```
**Technical Implementation:**
- Two-column layout using `st.columns(2)`
- Project status as pie chart with consistent color mapping
- Customer health as donut chart with hover data
- Dynamic data validation and error handling

#### `display_world_map()`
**Geographic Visualization**
```python
location_coords = {
    'USA': {'lat': 39.8283, 'lon': -98.5795, 'country': 'United States'},
    'Mumbai, India': {'lat': 19.0760, 'lon': 72.8777, 'country': 'India'},
    # ... comprehensive location mapping
}
```
**Advanced Features:**
- Hardcoded coordinate mapping for accurate positioning
- Location name normalization and alias handling
- Plotly Scattergeo for interactive world map
- Project count aggregation by location
- Custom hover templates with project details

#### `display_key_metrics()`
**KPI Dashboard**
```python
total_projects_sum = current_display_df.shape[0]
total_churned_sum = int(pd.to_numeric(current_display_df['Churn'], errors='coerce').fillna(0).sum())
churn_rate = (total_churned_sum / total_projects_sum) * 100
```
**Metrics Calculated:**
- Total projects count
- Unique customers analysis
- Churn rate calculation with error handling
- Average projects per customer
- Use cases/modules aggregation

### Data Requirements
- **Core Columns**: `Exective`, `Project Status (R/G/Y)`
- **Optional**: `Customer Name`, `Geography`, `Customer Health`, `Contract End Date`
- **Calculated Fields**: Churn rate, geographic aggregations

---

## 2. Support Tickets (`support_tickets.py`)

### Purpose
Ticket management and analysis dashboard with external system integrations and comprehensive ticket analytics.

### Key Functions & Code Analysis

#### `display_integration_links()`
**External System Integration**
```python
def display_integration_links():
    tickets_col1, tickets_col2, tickets_col3 = st.columns(3)
    
    # HubSpot Integration
    with tickets_col1:
        st.components.v1.html("""
            <a href="https://app.hubspot.com/contacts/20074161/objects/0-5/views/all/list" 
               target="_blank" style="...">Open Hubspot Tickets</a>
        """)
    
    # APM Tickets Integration
    with tickets_col3:
        st.components.v1.html("""
            <a href="https://sparkcognition.atlassian.net/jira/servicedesk/projects/RBS/queues/custom/567"
               target="_blank" style="...">Open APM Tickets</a>
        """)
```
**Integration Features:**
- Three-column layout for system links
- Custom HTML buttons with brand colors
- Direct links to HubSpot, Jira, and APM service desk
- Opens in new tabs for workflow continuity

#### `display_ticket_metrics()`
**Ticket KPI Analysis**
```python
open_statuses = ["Open", "New", "In Progress", "Waiting", "new", "open", "in progress"]
closed_statuses = ["Closed", "Resolved", "Solved", "closed", "resolved", "solved"]

open_tickets = current_display_df[current_display_df[status_col].isin(open_statuses)].shape[0]
```
**Smart Status Handling:**
- Case-insensitive status matching
- Flexible status categorization
- Priority-based high-importance ticket identification
- Recent tickets analysis (last 7 days)

#### `display_google_sheets_iframe()`
**Live Data Integration**
```python
google_sheets_url = "https://docs.google.com/spreadsheets/d/1Nxvj1LRWYIw3cQcX2Qz9RJmvv17JlCe-V8G2tmvqHfE/edit#gid=1"

st.components.v1.iframe(src=google_sheets_url, width=None, height=600, scrolling=True)
```
**Technical Details:**
- Uses specific GID=1 to target Tickets tab
- Full-width responsive iframe
- Scrolling enabled for large datasets
- Real-time data viewing without refresh

### Chart Functions
- **Status Distribution**: Pie chart with color mapping
- **Priority Analysis**: Donut chart for priority levels  
- **Timeline Trends**: Line chart for ticket creation over time
- **Category Breakdown**: Bar charts for categories and applications

---

## 3. Revenue Analysis (`revenue.py`)

### Purpose
Comprehensive financial performance analytics with multiple revenue metrics and geographic/customer analysis.

### Key Functions & Code Analysis

#### `show_page()` with Enhanced Validation
```python
# Debug section for troubleshooting
if not current_display_df.empty:
    with st.expander("🔍 Debug: Available Columns", expanded=False):
        st.write("**Available columns in the data:**", list(current_display_df.columns))
        st.write("**Data shape:**", current_display_df.shape)

# Smart validation
revenue_columns = ["Current ARR", "Contracted ARR", "Recognized ARR", "Services Revenue"]
found_columns = [col for col in revenue_columns if col in current_display_df.columns]

if found_columns:
    st.success(f"✅ Using standard Revenue data structure (Found: {', '.join(found_columns)})")
```
**Advanced Features:**
- Debug mode for data structure inspection
- Dynamic column detection and validation
- User-friendly feedback on data compatibility
- Comprehensive error messaging

#### `clean_revenue_data()`
**Data Preprocessing Pipeline**
```python
def clean_revenue_data(df):
    df = df.copy()
    numeric_columns_to_clean = ["Current ARR", "Contracted ARR", "Recognized ARR", "Services Revenue"]
    
    for col in numeric_columns_to_clean:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(r'[\$,]', '', regex=True), 
                errors='coerce'
            ).fillna(0)
    return df
```
**Data Cleaning Features:**
- Currency symbol removal ($, commas)
- String to numeric conversion with error handling
- Missing value imputation with zeros
- Data type consistency enforcement

#### `display_revenue_metrics()`
**Financial KPI Dashboard**
```python
# Dynamic column selection
arr_column = "Current ARR" if "Current ARR" in current_display_df.columns else "Contracted ARR"

# Advanced calculations
arr_recognition_rate = (total_recognized_arr / total_arr * 100) if total_arr > 0 else 0
avg_contract_value = total_arr / total_customers if total_customers > 0 else 0
```
**Metrics Calculated:**
- Total ARR (Current or Contracted)
- Recognized ARR and recognition rate
- Services revenue totals
- Customer metrics (count, average contract value)
- Contract count and distribution

### Visualization Functions

#### Geographic Revenue Analysis
```python
def display_revenue_by_geography(current_display_df, arr_column):
    geo_revenue = current_display_df.groupby("Geography", observed=True)[arr_column].sum().reset_index()
    
    fig_geo_revenue = px.bar(geo_revenue, x="Geography", y=arr_column,
                            color=arr_column, color_continuous_scale="Viridis")
    fig_geo_revenue.update_traces(text=geo_revenue[arr_column].apply(lambda x: f"${x:,.0f}"))
```

#### Customer Revenue Ranking
```python
def display_top_customers_revenue(current_display_df, arr_column):
    revenue_by_customer = current_display_df.groupby("Customer Name")[arr_column].sum().reset_index()
    revenue_by_customer = revenue_by_customer.sort_values(arr_column, ascending=False).head(10)
```

---

## 4. Chat Analytics (`chat_analytics.py`)

### Purpose
AI-powered conversational analytics with multiple AI provider integration and smart data analysis capabilities.

### Key Functions & Code Analysis

#### AI Provider Integration Architecture

##### OpenAI Integration
```python
def analyze_with_openai(prompt, df_info, api_key):
    client = OpenAI(api_key=api_key)
    
    system_prompt = """You are a data analyst AI assistant. Analyze the provided dataset information and answer questions about it.
    When possible, suggest specific insights, trends, or areas for investigation."""
    
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": full_prompt}
        ],
        max_tokens=500,
        temperature=0.7
    )
```

##### Anthropic Claude Integration
```python
def analyze_with_claude(prompt, df_info, api_key):
    client = anthropic.Anthropic(api_key=api_key)
    
    response = client.messages.create(
        model="claude-3-sonnet-20240229",
        max_tokens=500,
        messages=[{"role": "user", "content": full_prompt}]
    )
```

##### Free LLM Integration (Hugging Face)
```python
def analyze_with_free_llm(prompt, df_info, hf_token=None):
    models = [
        "google/flan-t5-large",
        "microsoft/DialoGPT-medium", 
        "google/flan-t5-xl"
    ]
    
    for model_name in models:
        try:
            response = requests.post(api_url, headers=headers, json={"inputs": prompt}, timeout=30)
            if response.status_code == 503:
                time.sleep(5)  # Model loading wait
                continue
```
**Advanced Features:**
- Multiple model fallback system
- Model warm-up handling for 503 errors
- Token-based authentication
- Timeout and retry logic

#### `analyze_data_locally()`
**Fallback Analysis Engine**
```python
def analyze_data_locally(prompt, df):
    analysis = {
        "shape": f"Dataset has {df.shape[0]} rows and {df.shape[1]} columns",
        "columns": list(df.columns),
        "missing_data": df.isnull().sum().to_dict(),
        "data_types": df.dtypes.astype(str).to_dict(),
        "numeric_summary": df.describe().to_dict() if not df.select_dtypes(include=[np.number]).empty else {},
        "sample_data": df.head(3).to_dict() if not df.empty else {}
    }
```
**Local Analysis Features:**
- Dataset profiling and statistics
- Missing data identification
- Data type analysis
- Sample data preview
- Numeric summary statistics

#### Smart Suggestions System
```python
suggestions = [
    "🆓 Try the Free AI option - minimal setup required!",
    "📊 Analyze customer distribution by geography",
    "💰 Show revenue trends over time",
    "🎯 Identify top performing projects",
    "⚠️ Analyze projects with red status",
    "👥 Compare executive performance",
    "📈 Calculate customer health metrics",
    "🌍 Show global project distribution"
]
```

---

## 5. Dinh and Kyle Sheet (`dinh_kyle_sheet.py`)

### Purpose
Direct Google Sheets integration for collaborative data management and real-time editing.

```python
def show_page():
    st.title("📊 Dinh and Kyle Sheet")
    st.markdown("Direct access to the collaborative Google Sheets for Dinh and Kyle.")
    
    google_sheets_url = "https://docs.google.com/spreadsheets/d/1Nxvj1LRWYIw3cQcX2Qz9RJmvv17JlCe-V8G2tmvqHfE/edit#gid=0"
    
    st.components.v1.iframe(
        src=google_sheets_url,
        width=None,
        height=800,
        scrolling=True
    )
```
**Features:**
- Full-screen Google Sheets embedding
- Real-time collaborative editing
- Direct data manipulation capabilities
- Seamless integration within dashboard

---

## Utility Modules

## Data Loader (`utils/data_loader.py`)

### Configuration System
```python
DATA_SOURCES = {
    "ops_review": {"url": f"{BASE_GOOGLE_SHEETS_URL}&sheet=Master", "sheet": "Master"},
    "revenue": {"url": f"{BASE_GOOGLE_SHEETS_URL}&sheet=Revenue", "sheet": "Revenue"}, 
    "tickets": {"url": f"{BASE_GOOGLE_SHEETS_URL}&sheet=Tickets", "sheet": "Tickets"}
}
```

### Advanced Filtering System
```python
def apply_filters(df):
    # Multi-dimensional filtering
    if "Customer Name" in df_filtered.columns:
        cust_filter = st.sidebar.multiselect("Filter by Customer Name", options=customers)
        
    # Date range filtering
    if "Project Start Date" in df_filtered.columns:
        proj_start_date = st.sidebar.date_input("Project Start From", min_value=min_date)
```

## Authentication Handler (`utils/auth_handler.py`)

### Secure API Key Management
```python
def setup_authentication_ui():
    with st.sidebar.expander("OpenAI Configuration"):
        openai_key = st.text_input("OpenAI API Key", type="password")
        if openai_key:
            st.session_state.openai_api_key = openai_key
```

---

## Data Flow & Integration

### 1. Application Flow
```
main.py → Page Selection → data_loader.load_data() → Page Module → Visualization
```

### 2. Data Sources
- **Google Sheets**: Live data via CSV export URLs
- **HubSpot API**: Direct CRM integration  
- **File Upload**: CSV/Excel file processing
- **Local Files**: Fallback data sources

### 3. AI Integration Flow
```
User Query → Provider Selection → API Call → Response Processing → Display + History
```

---

## Performance & Security

### Performance Optimizations
- Cached data loading where possible
- Efficient data aggregation for visualizations
- Smart sampling for large datasets
- Progressive loading for better UX

### Security Measures
- Client-side API key storage only
- Secure input fields (password type)
- No server-side data persistence
- HTTPS API communications

---

This technical documentation provides comprehensive coverage of the entire Avathon Analytics Dashboard, including architecture, implementation details, and operational considerations. 