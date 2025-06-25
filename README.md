# Avathon Analytics Dashboard

A modular Streamlit dashboard for analytics across multiple business areas including Projects & Customer Health, Support Tickets, Revenue Analysis, and more.

## 📁 Project Structure

```
├── main.py                     # Main dashboard entry point
├── dashboard.py               # Legacy monolithic dashboard (backup)
├── pages/                     # Page modules
│   ├── __init__.py
│   ├── projects_health.py     # Projects & Customer Health page
│   ├── support_tickets.py     # Support Tickets page  
│   ├── dinh_kyle_sheet.py     # Dinh and Kyle Sheet page
│   ├── revenue.py             # Revenue Analysis page
│   └── chat_analytics.py      # Chat Analytics page
├── utils/                     # Utility modules
│   ├── __init__.py
│   ├── data_loader.py         # Data loading and filtering functions
│   └── auth_handler.py        # Authentication setup functions
├── Data1.csv                  # Sample projects data
├── Revenue.csv                # Sample revenue data
├── Tickets.csv                # Sample tickets data (optional)
├── May'25 Revenue.xlsx        # Excel revenue data (optional)
└── Untitled design.gif       # Animated logo (optional)
```

## 🚀 Getting Started

### Prerequisites

```bash
pip install streamlit pandas plotly requests openpyxl
```

### AI Features Setup (Optional)

For enhanced AI-powered chat analytics, install additional dependencies:

```bash
# Quick setup using the installation script
python install_ai_features.py

# Or install manually
pip install openai>=1.0.0 anthropic>=0.18.0
```

**AI Providers:**
- **🆓 Free LLM (Hugging Face)**: No setup required, works immediately!
- **OpenAI GPT**: Requires API key from [OpenAI Platform](https://platform.openai.com/api-keys)
- **Anthropic Claude**: Requires API key from [Anthropic Console](https://console.anthropic.com/)

### Running the Dashboard

**Option 1: New Modular Version (Recommended)**
```bash
streamlit run main.py
```

**Option 2: Legacy Monolithic Version**
```bash
streamlit run dashboard.py
```

### 🆓 Getting Started with Free AI (Minimal Setup!)

1. **Get a free Hugging Face token:**
   - Go to [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
   - Create free account (no payment required)
   - Create a "Read" token
2. **Run the dashboard** (either version above)
3. **Go to Chat Analytics page**
4. **In the sidebar**, select "Free LLM (Hugging Face)"
5. **Enter your free token and start asking questions!**
   - "What insights can you provide from this data?"
   - "Show me revenue by customer"  
   - "What are the biggest risks?"
   - "Analyze project status distribution"

**No payment required, no usage limits, completely free AI analysis!**

## 📊 Dashboard Pages

### 1. Projects & Customer Health
- **File**: `pages/projects_health.py`
- **Data Source**: Google Sheets Master tab or Data1.csv
- **Features**:
  - Interactive world map showing global project distribution
  - Project status distribution with color coding
  - Executive performance analysis
  - Customer health metrics
  - Contract timeline analysis
  - PDF document embedding

### 2. Support Tickets
- **File**: `pages/support_tickets.py`
- **Data Sources**: HubSpot API or Google Sheets Tickets tab
- **Features**:
  - HubSpot and Jira integration links
  - Ticket metrics (total, open, closed, high priority)
  - Status and priority distribution charts
  - Timeline analysis
  - Category breakdown
  - Live Google Sheets iframe

### 3. Dinh and Kyle Sheet
- **File**: `pages/dinh_kyle_sheet.py`
- **Data Source**: May'25 Revenue.xlsx
- **Features**:
  - Excel-like HTML table rendering
  - Multi-sheet support
  - Professional styling with hover effects
  - Sheet selector

### 4. Revenue Analysis
- **File**: `pages/revenue.py`
- **Data Source**: Revenue.csv
- **Features**:
  - Key revenue KPIs (ARR, recognition rates, etc.)
  - Revenue by geography and customer
  - Industry/application breakdown
  - Revenue trends over time
  - ARR vs Recognized ARR analysis

### 5. Chat Analytics (🤖 AI-Powered)
- **File**: `pages/chat_analytics.py`
- **Data Source**: Any loaded dataset
- **AI Providers**: 🆓 Free LLM (Hugging Face), OpenAI GPT, Anthropic Claude
- **Features**:
  - **AI-Powered Analysis**: Use GPT or Claude for intelligent insights
  - **Natural Language Queries**: Ask complex questions in plain English
  - **Smart Suggestions**: AI-generated question recommendations
  - **Comprehensive Analysis**: Risk assessment, performance analysis, recommendations
  - **Auto-Visualization**: AI suggests and creates relevant charts
  - **Local Fallback**: Works without AI for basic queries
  - **FAQ Section**: Quick access to common questions

## 🔧 Data Sources

### Google Sheets Integration
- **Sheet ID**: `1Nxvj1LRWYIw3cQcX2Qz9RJmvv17JlCe-V8G2tmvqHfE`
- **Tabs**: Master, Finance, Tickets
- **Auto-refresh**: Data loads fresh each time

### HubSpot Integration
- **API**: HubSpot CRM API v3
- **Authentication**: API key required
- **Data**: Tickets with properties (subject, priority, status, etc.)

### Local Files
- **CSV Files**: Data1.csv, Revenue.csv, Tickets.csv
- **Excel Files**: May'25 Revenue.xlsx
- **PDFs**: Weekly status reports

### File Upload
- **Supported**: CSV, Excel (.xlsx)
- **Encoding**: UTF-8 with latin1 fallback
- **Processing**: Automatic date column detection

## 🛠 Utility Modules

### data_loader.py
- **Purpose**: Centralized data loading and filtering
- **Functions**:
  - `load_data(data_source, page)`: Main data loading function
  - `apply_filters(df)`: Apply sidebar filters
  - `fetch_hubspot_tickets(api_key)`: HubSpot API integration
  - `load_may_revenue_excel()`: Excel file handling

### auth_handler.py
- **Purpose**: Authentication setup and management
- **Functions**:
  - `setup_authentication_ui()`: Main auth UI setup
  - `setup_sharepoint_auth()`: SharePoint credentials
  - `setup_hubspot_auth()`: HubSpot API key management

## 🎨 Features

### Interactive Visualizations
- **World Map**: Global project distribution with hover details
- **Status Charts**: Color-coded project status (Red/Yellow/Green)
- **Revenue Charts**: Bar charts, pie charts, trend lines
- **Timeline Charts**: Contract and project date analysis

### Smart Filtering
- **Customer**: Multi-select customer filter
- **Executive**: Filter by project owner/executive
- **Status**: Project status filtering
- **Health**: Customer health status
- **Dates**: Project start and contract end date ranges

### Chat Analytics
- **Natural Language**: Ask questions in plain English
- **Auto-Visualization**: Generates charts based on queries
- **Context Aware**: Understands column names and data types
- **Examples**: "How many red status projects?", "Show revenue by customer"

### 🤖 AI-Powered Features

#### Smart Analysis
- **Comprehensive Insights**: AI provides detailed dataset analysis
- **Risk Assessment**: Automatically identifies potential issues
- **Performance Analysis**: Evaluates executive and customer performance
- **Recommendations**: Actionable suggestions based on data patterns

#### Natural Language Interface
- **Complex Queries**: "What are the biggest risks I should be aware of?"
- **Trend Analysis**: "Analyze revenue performance and identify key trends"
- **Comparative Analysis**: "How are different executives performing?"
- **Predictive Insights**: AI suggests future actions and improvements

#### Intelligent Visualizations
- **Auto-Generation**: AI creates relevant charts based on questions
- **Context-Aware**: Chooses appropriate chart types for data
- **Interactive**: Hover details and drill-down capabilities
- **Professional**: Publication-ready visualizations

#### Fallback System
- **Graceful Degradation**: Works without AI for basic queries
- **Error Handling**: Automatic fallback to local analysis
- **Hybrid Approach**: Combines AI insights with local processing

## 🔐 Authentication

### SharePoint (Optional)
- **Use Case**: If switching back to SharePoint data sources
- **Credentials**: Username/password stored in session
- **Status**: Currently optional as dashboard uses Google Sheets

### HubSpot (For Tickets)
- **Required**: For live ticket data from HubSpot
- **Setup**: Get API key from HubSpot Settings > Integrations
- **Fallback**: Uses Google Sheets if API key not provided

### AI Providers (For Enhanced Chat)
- **🆓 Free LLM (Hugging Face)**: Completely free, minimal setup
  - Models: FLAN-T5, DialoGPT variants
  - Setup: Free Hugging Face account + token (like GitHub)
  - Cost: Completely free
- **OpenAI GPT**: Optional, for AI-powered analytics
  - Get API key: [OpenAI Platform](https://platform.openai.com/api-keys)
  - Models: GPT-3.5-turbo, GPT-4, GPT-4-turbo
  - Cost: Pay per token usage
- **Anthropic Claude**: Optional, alternative AI provider
  - Get API key: [Anthropic Console](https://console.anthropic.com/)
  - Models: Claude-3 Sonnet, Haiku, Opus
  - Cost: Pay per token usage

## 📱 Responsive Design

- **Layout**: Wide layout optimized for dashboards
- **Columns**: Dynamic column layouts for different screen sizes
- **Mobile**: Basic mobile compatibility
- **Sidebar**: Collapsible navigation and filters

## 🚀 Deployment

### Local Development
```bash
streamlit run main.py
```

### Streamlit Cloud
1. Push code to GitHub repository
2. Connect to Streamlit Cloud
3. Set main.py as entry point
4. Add secrets for API keys if needed

### Docker (Optional)
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "main.py"]
```

## 🔄 Migration from Legacy

The original `dashboard.py` has been split into modular components:

1. **Main App Logic** → `main.py`
2. **Page Content** → `pages/*.py`
3. **Data Functions** → `utils/data_loader.py`
4. **Auth Functions** → `utils/auth_handler.py`

**Benefits**:
- Better code organization
- Easier maintenance
- Independent page development
- Reusable utility functions
- Cleaner separation of concerns

## 🐛 Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all files are in correct directories
2. **Data Loading**: Check file paths and Google Sheets permissions
3. **HubSpot API**: Verify API key and permissions
4. **Date Filtering**: Ensure date columns are properly formatted
5. **AI Features**: 
   - Install dependencies: `python install_ai_features.py`
   - Check API keys in sidebar configuration
   - Verify internet connection for AI providers
   - Check API rate limits and usage quotas

### Debug Mode
Add this to main.py for debugging:
```python
import streamlit as st
st.write("Debug info:", st.session_state)
```

## 📈 Future Enhancements

- [ ] Add more data source integrations
- [ ] Implement user authentication
- [ ] Add data export functionality
- [ ] Create automated reporting
- [ ] Add real-time data refresh
- [ ] Implement caching for better performance

## 📄 License

Internal use only - Avathon Analytics Dashboard © 2025 # Force deployment refresh Wed Jun 25 14:12:06 IST 2025
