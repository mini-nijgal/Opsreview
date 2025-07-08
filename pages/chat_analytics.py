import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re
import random
import string
import json
from typing import Tuple, Optional, Any

# LLM Integration
try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

try:
    from anthropic import Anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

def show_page(df):
    """Display the Chat Analytics page"""
    
    st.title("💬 AI-Powered Chat Analytics")
    st.markdown("Ask questions about your data using natural language. Powered by AI for intelligent analysis and insights.")

    # LLM Configuration
    setup_llm_configuration()
    
    # Use the original, unfiltered df for chat Q&A to provide broader answers
    chat_data_context = df.copy() if not df.empty else pd.DataFrame()

    display_faq(chat_data_context)
    st.markdown("---")
    
    # Enhanced chat interface
    display_chat_interface(chat_data_context)

def setup_llm_configuration():
    """Setup LLM configuration in sidebar"""
    with st.sidebar.expander("🤖 AI Configuration", expanded=False):
        st.markdown("### AI-Powered Analytics")
        
        # LLM Provider Selection
        providers = ["Local Analysis (Fallback)"]
        if HAS_REQUESTS:
            providers.insert(0, "Free LLM (Hugging Face)")
        if HAS_OPENAI:
            providers.insert(-1, "OpenAI GPT")
        if HAS_ANTHROPIC:
            providers.insert(-1, "Anthropic Claude")
            
        llm_provider = st.selectbox(
            "Choose AI Provider:",
            providers,
            help="Select your preferred AI provider for enhanced analytics"
        )
        
        if llm_provider == "Free LLM (Hugging Face)":
            if HAS_REQUESTS:
                st.markdown("### 🆓 Free AI with Hugging Face")
                st.info("✅ **No API key required!** Using free Hugging Face models.")
                
                # Model selection
                free_models = {
                    "microsoft/DialoGPT-medium": "DialoGPT Medium (Conversational)",
                    "google/flan-t5-large": "FLAN-T5 Large (Instruction following)",
                    "microsoft/DialoGPT-large": "DialoGPT Large (Advanced conversational)",
                    "google/flan-t5-xl": "FLAN-T5 XL (Most capable, slower)"
                }
                
                selected_model = st.selectbox(
                    "Choose Free Model:",
                    list(free_models.keys()),
                    format_func=lambda x: free_models[x],
                    index=1,  # Default to FLAN-T5 Large
                    help="Free models from Hugging Face - no API key needed!"
                )
                st.session_state.selected_free_model = selected_model
                
                # Hugging Face configuration
                hf_token = None
                try:
                    # Try secrets first
                    hf_token = st.secrets["huggingface"]["token"]
                    st.success("✅ Hugging Face token configured from secrets!")
                except:
                    # Fallback to environment variable
                    import os
                    hf_token = os.getenv("HF_TOKEN")
                    if hf_token:
                        st.success("✅ Hugging Face token configured from environment!")
                    else:
                        st.error("❌ Hugging Face token not found")
                        st.info("🔧 **Admin Note**: Configure HF token in Streamlit Cloud Secrets or environment variable")
                
                if hf_token:
                    st.session_state.hf_token = hf_token
                    st.info("🤖 **Free AI Ready**: Your Hugging Face token is configured and ready to use!")
                
                st.markdown("### 💡 Free AI Benefits:")
                st.markdown("""
                - **Completely Free**: No API costs or payment required
                - **Free Account**: Just need a free Hugging Face account (like GitHub)
                - **Good Performance**: Capable models for analysis
                - **Privacy**: Your data stays secure
                - **Reliable**: Backed by Hugging Face infrastructure
                """)
                
                st.markdown("### 🚀 Get Started:")
                st.markdown("Just start asking questions - no setup needed!")
                
            else:
                st.warning("⚠️ Requests package required for free LLM")
                st.code("pip install requests", language="bash")
        
        elif llm_provider == "OpenAI GPT":
            if HAS_OPENAI:
                api_key = st.text_input(
                    "OpenAI API Key",
                    type="password",
                    value=st.session_state.get('openai_api_key', ''),
                    help="Enter your OpenAI API key for enhanced AI responses"
                )
                
                if st.button("Save API Key"):
                    st.session_state.openai_api_key = api_key
                    if api_key:
                        st.success("✅ OpenAI API key saved!")
                    else:
                        st.warning("Please enter a valid API key")
                
                # Model selection
                model = st.selectbox(
                    "GPT Model:",
                    ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo-preview"],
                    index=0,
                    help="Choose the GPT model for analysis"
                )
                st.session_state.selected_model = model
                
                st.markdown("### 💡 Tips for AI Chat:")
                st.markdown("""
                - Ask complex analytical questions
                - Request insights and trends
                - Ask for recommendations
                - Use natural language freely
                """)
            else:
                st.warning("⚠️ OpenAI package not installed")
                st.code("pip install openai", language="bash")
        
        elif llm_provider == "Anthropic Claude":
            if HAS_ANTHROPIC:
                api_key = st.text_input(
                    "Anthropic API Key",
                    type="password",
                    value=st.session_state.get('anthropic_api_key', ''),
                    help="Enter your Anthropic API key for Claude AI responses"
                )
                
                if st.button("Save Anthropic Key"):
                    st.session_state.anthropic_api_key = api_key
                    if api_key:
                        st.success("✅ Anthropic API key saved!")
                    else:
                        st.warning("Please enter a valid API key")
                
                # Model selection
                model = st.selectbox(
                    "Claude Model:",
                    ["claude-3-sonnet-20240229", "claude-3-haiku-20240307", "claude-3-opus-20240229"],
                    index=0,
                    help="Choose the Claude model for analysis"
                )
                st.session_state.selected_claude_model = model
                
                st.markdown("### 💡 Tips for Claude AI:")
                st.markdown("""
                - Claude excels at detailed analysis
                - Great for complex reasoning
                - Excellent at recommendations
                - Strong analytical capabilities
                """)
            else:
                st.warning("⚠️ Anthropic package not installed")
                st.code("pip install anthropic", language="bash")
        
        st.session_state.llm_provider = llm_provider

def display_chat_interface(chat_data_context):
    """Display enhanced chat interface with AI capabilities"""
    
    # Chat suggestions
    if not st.session_state.messages:
        st.subheader("💡 Try asking:")
        suggestions = get_smart_suggestions(chat_data_context)
        
        cols = st.columns(2)
        for i, suggestion in enumerate(suggestions):
            with cols[i % 2]:
                if st.button(suggestion, key=f"suggestion_{i}", use_container_width=True):
                    # Add suggestion as user message and process it
                    st.session_state.messages.append({"role": "user", "content": suggestion})
                    with st.spinner("🤖 AI is analyzing your data..."):
                        response, fig = analyze_with_ai(suggestion, chat_data_context)
                        st.session_state.messages.append({"role": "assistant", "content": (response, fig)})
                    st.rerun()
    
    st.subheader("💬 Chat with Your Data")
    
    # Display existing messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if isinstance(message["content"], tuple):
                st.markdown(message["content"][0])
                if message["content"][1] is not None:
                    st.plotly_chart(message["content"][1], use_container_width=True)
            else:
                st.markdown(message["content"])

    # Chat input with enhanced processing
    if prompt := st.chat_input("Ask anything about your data... 🤖"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("🤖 AI is analyzing your data..."):
                response, fig = analyze_with_ai(prompt, chat_data_context)
                st.markdown(response)
                if fig is not None:
                    st.plotly_chart(fig, use_container_width=True)
                st.session_state.messages.append({"role": "assistant", "content": (response, fig)})

def get_smart_suggestions(data):
    """Generate smart suggestions based on available data"""
    suggestions = []
    
    if not data.empty:
        columns = data.columns.tolist()
        
        # Dynamic suggestions based on available columns
        if any("status" in col.lower() for col in columns):
            suggestions.append("📊 What's the distribution of project statuses and what insights can you provide?")
        
        if any("revenue" in col.lower() for col in columns):
            suggestions.append("💰 Analyze our revenue performance and identify key trends")
        
        if any("customer" in col.lower() for col in columns):
            suggestions.append("👥 Which customers need attention and why?")
        
        if any("executive" in col.lower() or "owner" in col.lower() for col in columns):
            suggestions.append("🎯 How are different executives performing and what recommendations do you have?")
        
        # Add general suggestions
        suggestions.extend([
            "🔍 Give me a comprehensive analysis of this dataset",
            "⚠️ What are the biggest risks or issues I should be aware of?",
            "📈 What opportunities for improvement do you see?",
            "🎯 What actions should I take based on this data?"
        ])
    else:
        suggestions = [
            "📊 What kind of data analysis can you help me with?",
            "🤖 How can AI enhance my data analytics?",
            "💡 What insights can you provide once I load data?",
            "🆓 Try the Free AI option - no setup required!",
            "🔧 What features are available in this analytics platform?"
        ]
    
    return suggestions[:6]  # Return top 6 suggestions

def analyze_with_ai(question: str, data: pd.DataFrame) -> Tuple[str, Optional[Any]]:
    """Enhanced analysis using AI when available, with intelligent fallback"""
    
    llm_provider = st.session_state.get('llm_provider')
    
    # Check if we should use Free LLM
    hf_token_available = False
    try:
        hf_token_available = bool(st.secrets["huggingface"]["token"])
    except:
        import os
        hf_token_available = bool(st.session_state.get('hf_token')) or bool(os.getenv("HF_TOKEN"))
    
    use_free_llm = (
        llm_provider == "Free LLM (Hugging Face)" and
        HAS_REQUESTS and
        hf_token_available and
        not data.empty
    )
    
    # Check if we should use OpenAI
    use_openai = (
        llm_provider == "OpenAI GPT" and
        st.session_state.get('openai_api_key') and
        HAS_OPENAI and
        not data.empty
    )
    
    # Check if we should use Anthropic
    use_anthropic = (
        llm_provider == "Anthropic Claude" and
        st.session_state.get('anthropic_api_key') and
        HAS_ANTHROPIC and
        not data.empty
    )
    
    if use_free_llm:
        try:
            return analyze_with_free_llm(question, data)
        except Exception as e:
            st.warning(f"⚠️ Free LLM analysis failed: {str(e)[:100]}... Falling back to local analysis.")
            return analyze_data_locally(question, data)
    elif llm_provider == "Free LLM (Hugging Face)" and not hf_token_available:
        # Free LLM selected but no token provided
        fallback_response, fallback_fig = analyze_data_locally(question, data)
        token_message = """
🔑 **Hugging Face Token Required**

The HF token is not configured in secrets. Please contact your administrator to configure the token.

For now, here's local analysis:

---
"""
        return token_message + fallback_response, fallback_fig
    elif use_openai:
        try:
            return analyze_with_openai(question, data)
        except Exception as e:
            st.warning(f"⚠️ OpenAI analysis failed: {str(e)[:100]}... Falling back to local analysis.")
            return analyze_data_locally(question, data)
    elif use_anthropic:
        try:
            return analyze_with_anthropic(question, data)
        except Exception as e:
            st.warning(f"⚠️ Anthropic analysis failed: {str(e)[:100]}... Falling back to local analysis.")
            return analyze_data_locally(question, data)
    else:
        return analyze_data_locally(question, data)

def analyze_with_openai(question: str, data: pd.DataFrame) -> Tuple[str, Optional[Any]]:
    """Analyze data using OpenAI GPT with structured prompts"""
    
    # Prepare data context
    data_summary = prepare_data_context(data)
    
    # Create system prompt
    system_prompt = f"""
    You are an expert data analyst helping analyze business data. You have access to a dataset with the following structure:

    {data_summary}

    Your role is to:
    1. Provide insightful analysis based on the data
    2. Identify trends, patterns, and anomalies
    3. Give actionable recommendations
    4. Suggest specific visualizations when relevant
    5. Be concise but comprehensive

    When suggesting visualizations, use this format:
    VISUALIZATION: [chart_type]|[x_column]|[y_column]|[color_column]|[title]

    Available chart types: bar, pie, line, scatter, box, histogram
    """
    
    # Create user prompt
    user_prompt = f"""
    Question: {question}
    
    Please analyze this question in the context of the provided dataset and give me:
    1. Direct answer to the question
    2. Key insights and patterns
    3. Actionable recommendations
    4. Suggested visualization if relevant
    
    Be specific and reference actual data points when possible.
    """
    
    try:
        # Set up OpenAI client
        client = openai.OpenAI(api_key=st.session_state.openai_api_key)
        model = st.session_state.get('selected_model', 'gpt-3.5-turbo')
        
        # Make API call using new client format
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=1000,
            temperature=0.7
        )
        
        ai_response = response.choices[0].message.content
        
        # Extract visualization suggestion and create chart
        fig = extract_and_create_visualization(ai_response, data)
        
        # Clean up response (remove visualization instruction from display)
        clean_response = re.sub(r'VISUALIZATION:.*?\n', '', ai_response, flags=re.IGNORECASE)
        
        # Add AI attribution
        final_response = f"🤖 **AI Analysis:**\n\n{clean_response}"
        
        return final_response, fig
        
    except Exception as e:
        raise Exception(f"OpenAI API error: {str(e)}")

def analyze_with_free_llm(question: str, data: pd.DataFrame) -> Tuple[str, Optional[Any]]:
    """Analyze data using free Hugging Face models"""
    
    # Prepare data context
    data_summary = prepare_data_context(data)
    
    # Create a comprehensive prompt
    prompt = f"""You are a data analyst. Analyze this dataset and answer the question.

Dataset Information:
{data_summary}

Question: {question}

Please provide:
1. Direct answer to the question
2. Key insights from the data
3. Actionable recommendations
4. If relevant, suggest a visualization format: VISUALIZATION: [chart_type]|[x_column]|[y_column]|[color_column]|[title]

Available chart types: bar, pie, line, scatter, box, histogram

Answer:"""
    
    try:
        # Get model from session state
        model = st.session_state.get('selected_free_model', 'google/flan-t5-large')
        
        # Get HF token from secrets first, then session state, then environment
        try:
            hf_token = st.secrets["huggingface"]["token"]
        except:
            import os
            hf_token = st.session_state.get('hf_token', '') or os.getenv("HF_TOKEN", '')
        
        # Hugging Face Inference API endpoint
        api_url = f"https://api-inference.huggingface.co/models/{model}"
        
        # Prepare headers
        headers = {"Content-Type": "application/json"}
        if hf_token:
            headers["Authorization"] = f"Bearer {hf_token}"
        else:
            raise Exception("Hugging Face token is required. Please configure it in secrets or contact admin.")
        
        # Prepare payload
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 500,
                "temperature": 0.7,
                "do_sample": True,
                "return_full_text": False
            }
        }
        
        # Make API call
        response = requests.post(api_url, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            
            # Handle different response formats
            if isinstance(result, list) and len(result) > 0:
                if 'generated_text' in result[0]:
                    ai_response = result[0]['generated_text']
                elif 'text' in result[0]:
                    ai_response = result[0]['text']
                else:
                    ai_response = str(result[0])
            elif isinstance(result, dict):
                if 'generated_text' in result:
                    ai_response = result['generated_text']
                elif 'text' in result:
                    ai_response = result['text']
                else:
                    ai_response = str(result)
            else:
                ai_response = str(result)
            
            # Clean up response
            ai_response = ai_response.strip()
            
            # If response is too short, enhance it with local analysis
            if len(ai_response) < 50:
                local_response, local_fig = analyze_data_locally(question, data)
                ai_response = f"{ai_response}\n\nEnhanced Analysis:\n{local_response}"
                fig = local_fig
            else:
                # Extract visualization suggestion and create chart
                fig = extract_and_create_visualization(ai_response, data)
            
            # Clean up response (remove visualization instruction from display)
            clean_response = re.sub(r'VISUALIZATION:.*?\n', '', ai_response, flags=re.IGNORECASE)
            
            # Add AI attribution
            final_response = f"🤖 **Free AI Analysis** (Model: {model.split('/')[-1]}):\n\n{clean_response}"
            
            return final_response, fig
            
        elif response.status_code == 503:
            # Model is loading, try again with simpler prompt
            simple_payload = {
                "inputs": f"Analyze this data question: {question}",
                "parameters": {"max_new_tokens": 200, "temperature": 0.5}
            }
            
            retry_response = requests.post(api_url, headers=headers, json=simple_payload, timeout=15)
            if retry_response.status_code == 200:
                result = retry_response.json()
                ai_response = str(result[0].get('generated_text', result))
                return f"🤖 **Free AI Analysis** (Simple):\n\n{ai_response}", None
            else:
                raise Exception(f"Model loading (503). Please try again in a moment.")
        else:
            raise Exception(f"API error: {response.status_code}")
            
    except requests.exceptions.Timeout:
        raise Exception("Request timeout. Free models can be slow - please try again.")
    except requests.exceptions.RequestException as e:
        raise Exception(f"Network error: {str(e)}")
    except Exception as e:
        raise Exception(f"Free LLM error: {str(e)}")

def analyze_with_anthropic(question: str, data: pd.DataFrame) -> Tuple[str, Optional[Any]]:
    """Analyze data using Anthropic Claude with structured prompts"""
    
    # Prepare data context
    data_summary = prepare_data_context(data)
    
    # Create system prompt
    system_prompt = f"""You are an expert data analyst helping analyze business data. You have access to a dataset with the following structure:

{data_summary}

Your role is to:
1. Provide insightful analysis based on the data
2. Identify trends, patterns, and anomalies
3. Give actionable recommendations
4. Suggest specific visualizations when relevant
5. Be concise but comprehensive

When suggesting visualizations, use this format:
VISUALIZATION: [chart_type]|[x_column]|[y_column]|[color_column]|[title]

Available chart types: bar, pie, line, scatter, box, histogram"""
    
    # Create user prompt
    user_prompt = f"""Question: {question}

Please analyze this question in the context of the provided dataset and give me:
1. Direct answer to the question
2. Key insights and patterns
3. Actionable recommendations
4. Suggested visualization if relevant

Be specific and reference actual data points when possible."""
    
    try:
        # Set up Anthropic client
        client = Anthropic(api_key=st.session_state.anthropic_api_key)
        model = st.session_state.get('selected_claude_model', 'claude-3-sonnet-20240229')
        
        # Make API call
        response = client.messages.create(
            model=model,
            max_tokens=1000,
            temperature=0.7,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )
        
        ai_response = response.content[0].text
        
        # Extract visualization suggestion and create chart
        fig = extract_and_create_visualization(ai_response, data)
        
        # Clean up response (remove visualization instruction from display)
        clean_response = re.sub(r'VISUALIZATION:.*?\n', '', ai_response, flags=re.IGNORECASE)
        
        # Add AI attribution
        final_response = f"🤖 **Claude AI Analysis:**\n\n{clean_response}"
        
        return final_response, fig
        
    except Exception as e:
        raise Exception(f"Anthropic API error: {str(e)}")

def prepare_data_context(data: pd.DataFrame) -> str:
    """Prepare a concise summary of the dataset for the AI"""
    
    if data.empty:
        return "No data available"
    
    context = f"""
    Dataset Overview:
    - Rows: {len(data)}
    - Columns: {len(data.columns)}
    
    Column Information:
    """
    
    for col in data.columns:
        dtype = str(data[col].dtype)
        non_null = data[col].count()
        unique_vals = data[col].nunique()
        
        if data[col].dtype in ['object', 'category']:
            sample_values = data[col].dropna().unique()[:3]
            context += f"- {col} ({dtype}): {non_null} non-null, {unique_vals} unique. Sample: {list(sample_values)}\n"
        else:
            context += f"- {col} ({dtype}): {non_null} non-null, range: {data[col].min():.2f} to {data[col].max():.2f}\n"
    
    # Add key statistics
    if len(data) > 0:
        context += f"\nKey Insights:\n"
        
        # Status distribution if available
        status_cols = [col for col in data.columns if 'status' in col.lower()]
        if status_cols:
            status_dist = data[status_cols[0]].value_counts().head(3)
            context += f"- Status distribution: {dict(status_dist)}\n"
        
        # Revenue info if available
        revenue_cols = [col for col in data.columns if 'revenue' in col.lower()]
        if revenue_cols:
            total_revenue = data[revenue_cols[0]].sum()
            context += f"- Total revenue: ${total_revenue:,.0f}\n"
    
    return context

def extract_and_create_visualization(ai_response: str, data: pd.DataFrame) -> Optional[Any]:
    """Extract visualization instructions from AI response and create the chart"""
    
    viz_match = re.search(r'VISUALIZATION:\s*([^|]+)\|([^|]+)\|([^|]+)\|([^|]*)\|([^|\n]+)', ai_response, re.IGNORECASE)
    
    if not viz_match or data.empty:
        return None
    
    try:
        chart_type = viz_match.group(1).strip().lower()
        x_col = viz_match.group(2).strip()
        y_col = viz_match.group(3).strip()
        color_col = viz_match.group(4).strip() or None
        title = viz_match.group(5).strip()
        
        # Validate columns exist
        if x_col not in data.columns or y_col not in data.columns:
            return None
        
        if color_col and color_col not in data.columns:
            color_col = None
        
        # Create visualization based on type
        if chart_type == 'bar':
            if data[x_col].dtype in ['object', 'category']:
                grouped_data = data.groupby(x_col)[y_col].sum().reset_index()
                fig = px.bar(grouped_data, x=x_col, y=y_col, color=color_col, title=title)
            else:
                fig = px.bar(data, x=x_col, y=y_col, color=color_col, title=title)
        elif chart_type == 'pie':
            if data[x_col].dtype in ['object', 'category']:
                pie_data = data[x_col].value_counts().reset_index()
                fig = px.pie(pie_data, names='index', values=x_col, title=title)
            else:
                return None
        elif chart_type == 'line':
            fig = px.line(data, x=x_col, y=y_col, color=color_col, title=title)
        elif chart_type == 'scatter':
            fig = px.scatter(data, x=x_col, y=y_col, color=color_col, title=title)
        elif chart_type == 'box':
            fig = px.box(data, x=x_col, y=y_col, color=color_col, title=title)
        elif chart_type == 'histogram':
            fig = px.histogram(data, x=x_col, color=color_col, title=title)
        else:
            return None
        
        fig.update_layout(height=400)
        return fig
        
    except Exception as e:
        st.warning(f"Could not create suggested visualization: {str(e)}")
        return None

def analyze_data_locally(question: str, data: pd.DataFrame) -> Tuple[str, Optional[Any]]:
    """Enhanced local analysis with better pattern matching and insights"""
    
    question_lower = question.lower().strip()
    
    try:
        # Handle empty data
        if data.empty:
            if "free ai" in question_lower or "no setup" in question_lower:
                return "🆓 **Free AI Available!** Go to the sidebar and select 'Free LLM (Hugging Face)' for AI-powered analysis with no setup required. It works immediately!", None
            return "I need data to answer questions. Please load or adjust filters on other pages.", None
            
        # Get available columns and their data types
        available_columns = list(data.columns)
        numeric_columns = data.select_dtypes(include=['int64', 'float64']).columns.tolist()
        categorical_columns = data.select_dtypes(include=['object', 'category']).columns.tolist()
        date_columns = data.select_dtypes(include=['datetime64']).columns.tolist()
        
        # Enhanced pattern matching with more intelligence
        
        # Handle AI-related questions
        if any(term in question_lower for term in ["ai", "llm", "free ai", "artificial intelligence", "machine learning"]):
            return "🤖 **AI Features Available!**\n\n" + \
                   "Choose from these AI options in the sidebar:\n" + \
                   "- 🆓 **Free LLM (Hugging Face)**: No setup required, works immediately!\n" + \
                   "- 💰 **OpenAI GPT**: Requires API key, very powerful\n" + \
                   "- 🧠 **Anthropic Claude**: Requires API key, excellent reasoning\n\n" + \
                   "The Free LLM option is perfect to start with - just select it and start asking questions!", None
        
        # Comprehensive analysis requests
        if any(term in question_lower for term in ["comprehensive", "full analysis", "overview", "summary", "insights"]):
            return generate_comprehensive_analysis(data, available_columns, numeric_columns, categorical_columns)
        
        # Risk and issue identification
        if any(term in question_lower for term in ["risk", "issue", "problem", "concern", "alert"]):
            return identify_risks_and_issues(data, available_columns)
        
        # Recommendations and actions
        if any(term in question_lower for term in ["recommend", "action", "should do", "next steps", "improve"]):
            return generate_recommendations(data, available_columns)
        
        # Performance analysis
        if any(term in question_lower for term in ["performance", "performing", "best", "worst", "top", "bottom"]):
            return analyze_performance(data, available_columns, question_lower)
        
        # Trend analysis
        if any(term in question_lower for term in ["trend", "pattern", "over time", "timeline", "historical"]):
            return analyze_trends(data, date_columns, numeric_columns, question_lower)
        
        # Fall back to original analysis for specific queries
        return analyze_data_for_chat_original(question, data)
        
    except Exception as e:
        return f"I encountered an error analyzing the data: {str(e)}\n\nTry asking a different question or check if the columns you're asking about exist in the data.", None

def generate_comprehensive_analysis(data, available_columns, numeric_columns, categorical_columns):
    """Generate a comprehensive analysis of the dataset"""
    
    analysis = "## 📊 Comprehensive Data Analysis\n\n"
    
    # Basic stats
    analysis += f"**Dataset Overview:**\n"
    analysis += f"- Total records: {len(data):,}\n"
    analysis += f"- Total columns: {len(available_columns)}\n"
    analysis += f"- Numeric columns: {len(numeric_columns)}\n"
    analysis += f"- Categorical columns: {len(categorical_columns)}\n\n"
    
    # Key insights by column type
    if categorical_columns:
        analysis += "**Key Categorical Insights:**\n"
        for col in categorical_columns[:3]:  # Top 3 categorical columns
            if not data[col].empty:
                top_value = data[col].mode()[0] if len(data[col].mode()) > 0 else "N/A"
                unique_count = data[col].nunique()
                analysis += f"- {col}: {unique_count} unique values, most common: '{top_value}'\n"
        analysis += "\n"
    
    if numeric_columns:
        analysis += "**Key Numeric Insights:**\n"
        for col in numeric_columns[:3]:  # Top 3 numeric columns
            mean_val = data[col].mean()
            max_val = data[col].max()
            min_val = data[col].min()
            analysis += f"- {col}: Range {min_val:.2f} to {max_val:.2f}, Average: {mean_val:.2f}\n"
        analysis += "\n"
    
    # Status analysis if available
    status_cols = [col for col in categorical_columns if 'status' in col.lower()]
    if status_cols:
        status_col = status_cols[0]
        status_dist = data[status_col].value_counts()
        analysis += f"**Status Analysis ({status_col}):**\n"
        for status, count in status_dist.head(5).items():
            pct = (count / len(data)) * 100
            analysis += f"- {status}: {count} ({pct:.1f}%)\n"
        analysis += "\n"
    
    # Create a summary visualization
    fig = None
    if status_cols:
        status_counts = data[status_cols[0]].value_counts()
        fig = px.pie(values=status_counts.values, names=status_counts.index, 
                    title=f"Distribution of {status_cols[0]}")
    elif len(numeric_columns) > 0:
        fig = px.histogram(data, x=numeric_columns[0], title=f"Distribution of {numeric_columns[0]}")
    
    return analysis, fig

def identify_risks_and_issues(data, available_columns):
    """Identify potential risks and issues in the data"""
    
    risks = "## ⚠️ Risk Analysis\n\n"
    risk_count = 0
    fig = None
    
    # Check for status-related risks
    status_cols = [col for col in available_columns if 'status' in col.lower()]
    if status_cols:
        status_col = status_cols[0]
        red_statuses = data[data[status_col].isin(['Red', 'R'])].shape[0]
        total = len(data)
        
        if red_statuses > 0:
            risk_count += 1
            pct = (red_statuses / total) * 100
            risks += f"🔴 **Critical Status Alert**: {red_statuses} projects ({pct:.1f}%) in Red status\n\n"
            
            # Create visualization for status risks
            status_counts = data[status_col].value_counts()
            colors = ['#d62728' if 'Red' in str(x) or 'R' == str(x) else '#ff7f0e' if 'Yellow' in str(x) or 'Y' == str(x) else '#2ca02c' for x in status_counts.index]
            fig = px.bar(x=status_counts.index, y=status_counts.values, 
                        title="Project Status Distribution - Risk Analysis",
                        color=status_counts.index,
                        color_discrete_sequence=colors)
    
    # Check for customer concentration risk
    customer_cols = [col for col in available_columns if 'customer' in col.lower()]
    if customer_cols:
        customer_col = customer_cols[0]
        top_customer_pct = (data[customer_col].value_counts().iloc[0] / len(data)) * 100
        
        if top_customer_pct > 30:
            risk_count += 1
            top_customer = data[customer_col].value_counts().index[0]
            risks += f"⚠️ **Customer Concentration Risk**: {top_customer} represents {top_customer_pct:.1f}% of projects\n\n"
    
    # Check for date-related risks
    date_cols = [col for col in available_columns if 'date' in col.lower() and 'end' in col.lower()]
    if date_cols:
        date_col = date_cols[0]
        overdue = data[data[date_col] < pd.Timestamp.now()].shape[0]
        
        if overdue > 0:
            risk_count += 1
            risks += f"📅 **Overdue Items**: {overdue} items past their end date\n\n"
    
    if risk_count == 0:
        risks += "✅ **No major risks identified** in the current dataset.\n\n"
        risks += "The data appears to be in good shape with no immediate red flags."
    
    return risks, fig

def generate_recommendations(data, available_columns):
    """Generate actionable recommendations based on data analysis"""
    
    recommendations = "## 🎯 Actionable Recommendations\n\n"
    rec_count = 0
    fig = None
    
    # Status-based recommendations
    status_cols = [col for col in available_columns if 'status' in col.lower()]
    if status_cols:
        status_col = status_cols[0]
        status_counts = data[status_col].value_counts()
        
        red_count = sum(data[status_col].isin(['Red', 'R']))
        yellow_count = sum(data[status_col].isin(['Yellow', 'Y', 'Amber', 'A']))
        
        if red_count > 0:
            rec_count += 1
            recommendations += f"🔴 **Immediate Action Required**: Focus on {red_count} Red status projects\n"
            recommendations += "   - Conduct emergency review meetings\n"
            recommendations += "   - Allocate additional resources\n"
            recommendations += "   - Identify root causes\n\n"
        
        if yellow_count > 0:
            rec_count += 1
            recommendations += f"🟡 **Monitor Closely**: {yellow_count} projects at risk\n"
            recommendations += "   - Increase check-in frequency\n"
            recommendations += "   - Proactive risk mitigation\n"
            recommendations += "   - Resource reallocation if needed\n\n"
    
    # Executive/Owner workload recommendations
    exec_cols = [col for col in available_columns if any(term in col.lower() for term in ['executive', 'exective', 'owner'])]
    if exec_cols:
        exec_col = exec_cols[0]
        exec_workload = data[exec_col].value_counts()
        
        if len(exec_workload) > 1:
            max_load = exec_workload.max()
            min_load = exec_workload.min()
            
            if max_load > min_load * 2:  # Significant imbalance
                rec_count += 1
                overloaded_exec = exec_workload.idxmax()
                underloaded_exec = exec_workload.idxmin()
                
                recommendations += f"⚖️ **Workload Rebalancing**: Consider redistributing projects\n"
                recommendations += f"   - {overloaded_exec} has {max_load} projects (heaviest load)\n"
                recommendations += f"   - {underloaded_exec} has {min_load} projects (lightest load)\n"
                recommendations += f"   - Consider transferring 1-2 projects for better balance\n\n"
                
                # Create workload visualization
                fig = px.bar(x=exec_workload.index, y=exec_workload.values,
                           title="Executive Workload Distribution",
                           labels={'x': exec_col, 'y': 'Number of Projects'})
    
    # Customer health recommendations
    health_cols = [col for col in available_columns if 'health' in col.lower()]
    if health_cols:
        health_col = health_cols[0]
        poor_health = sum(data[health_col].isin(['Red', 'Poor', 'At Risk']))
        
        if poor_health > 0:
            rec_count += 1
            recommendations += f"❤️ **Customer Health Alert**: {poor_health} customers need attention\n"
            recommendations += "   - Schedule customer success calls\n"
            recommendations += "   - Review service delivery\n"
            recommendations += "   - Implement retention strategies\n\n"
    
    if rec_count == 0:
        recommendations += "✅ **Maintain Current Course**: Data shows healthy performance\n\n"
        recommendations += "**Suggested Actions:**\n"
        recommendations += "- Continue monitoring key metrics\n"
        recommendations += "- Maintain regular review cycles\n"
        recommendations += "- Focus on continuous improvement\n"
    
    return recommendations, fig

def analyze_performance(data, available_columns, question):
    """Analyze performance metrics and identify top/bottom performers"""
    
    performance = "## 📈 Performance Analysis\n\n"
    fig = None
    
    # Executive performance
    if any(term in question for term in ['executive', 'exec', 'owner']):
        exec_cols = [col for col in available_columns if any(term in col.lower() for term in ['executive', 'exective', 'owner'])]
        if exec_cols:
            exec_col = exec_cols[0]
            exec_counts = data[exec_col].value_counts()
            
            performance += f"**Executive Performance ({exec_col}):**\n"
            performance += f"- Most active: {exec_counts.index[0]} ({exec_counts.iloc[0]} projects)\n"
            performance += f"- Least active: {exec_counts.index[-1]} ({exec_counts.iloc[-1]} projects)\n\n"
            
            # Success rate by executive if status available
            status_cols = [col for col in available_columns if 'status' in col.lower()]
            if status_cols:
                status_col = status_cols[0]
                exec_performance = []
                
                for exec_name in exec_counts.index[:5]:  # Top 5 executives
                    exec_data = data[data[exec_col] == exec_name]
                    green_count = sum(exec_data[status_col].isin(['Green', 'G']))
                    total_count = len(exec_data)
                    success_rate = (green_count / total_count) * 100 if total_count > 0 else 0
                    exec_performance.append({'Executive': exec_name, 'Success Rate': success_rate, 'Total Projects': total_count})
                
                perf_df = pd.DataFrame(exec_performance)
                if not perf_df.empty:
                    fig = px.bar(perf_df, x='Executive', y='Success Rate', 
                               title="Executive Success Rate (% Green Status)",
                               hover_data=['Total Projects'])
    
    # Customer performance
    elif any(term in question for term in ['customer', 'client']):
        customer_cols = [col for col in available_columns if 'customer' in col.lower()]
        if customer_cols:
            customer_col = customer_cols[0]
            customer_counts = data[customer_col].value_counts().head(10)
            
            performance += f"**Top Customers by Project Volume:**\n"
            for i, (customer, count) in enumerate(customer_counts.items(), 1):
                performance += f"{i}. {customer}: {count} projects\n"
            
            fig = px.bar(x=customer_counts.values, y=customer_counts.index, 
                       orientation='h', title="Top 10 Customers by Project Count")
    
    return performance, fig

def analyze_trends(data, date_columns, numeric_columns, question):
    """Analyze trends over time"""
    
    trends = "## 📊 Trend Analysis\n\n"
    fig = None
    
    if not date_columns:
        return "No date columns found for trend analysis.", None
    
    date_col = date_columns[0]
    
    # Revenue trends
    if any(term in question for term in ['revenue', 'financial', 'money']):
        revenue_cols = [col for col in numeric_columns if 'revenue' in col.lower()]
        if revenue_cols:
            revenue_col = revenue_cols[0]
            monthly_revenue = data.groupby(data[date_col].dt.to_period('M'))[revenue_col].sum().reset_index()
            monthly_revenue[date_col] = monthly_revenue[date_col].dt.to_timestamp()
            
            fig = px.line(monthly_revenue, x=date_col, y=revenue_col, 
                         title="Revenue Trend Over Time", markers=True)
            
            trends += f"**Revenue Trends:**\n"
            if len(monthly_revenue) > 1:
                latest_revenue = monthly_revenue[revenue_col].iloc[-1]
                previous_revenue = monthly_revenue[revenue_col].iloc[-2]
                change = ((latest_revenue - previous_revenue) / previous_revenue) * 100
                trends += f"- Latest month: ${latest_revenue:,.0f}\n"
                trends += f"- Month-over-month change: {change:+.1f}%\n"
    
    # Project trends
    else:
        monthly_projects = data.groupby(data[date_col].dt.to_period('M')).size().reset_index(name='Project Count')
        monthly_projects[date_col] = monthly_projects[date_col].dt.to_timestamp()
        
        fig = px.line(monthly_projects, x=date_col, y='Project Count', 
                     title="Project Volume Trend Over Time", markers=True)
        
        trends += f"**Project Volume Trends:**\n"
        if len(monthly_projects) > 1:
            latest_count = monthly_projects['Project Count'].iloc[-1]
            previous_count = monthly_projects['Project Count'].iloc[-2]
            change = latest_count - previous_count
            trends += f"- Latest month: {latest_count} projects\n"
            trends += f"- Month-over-month change: {change:+d} projects\n"
    
    return trends, fig

def analyze_data_for_chat_original(question, data):
    """Original analyze function for backward compatibility"""
    question_lower = question.lower().strip()
    
    try:
        # Handle empty or invalid data
        if data.empty:
            return "I need data to answer questions. Please load or adjust filters on other pages.", None
            
        # Get available columns and their data types for dynamic analysis
        available_columns = list(data.columns)
        numeric_columns = data.select_dtypes(include=['int64', 'float64']).columns.tolist()
        categorical_columns = data.select_dtypes(include=['object', 'category']).columns.tolist()
        date_columns = data.select_dtypes(include=['datetime64']).columns.tolist()
        
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
        
        # Handle summary statistics request
        if "summary" in question_lower or "statistics" in question_lower or "describe" in question_lower:
            # Find specific column matches
            col_match = None
            for col in available_columns:
                if col.lower() in question_lower:
                    col_match = col
                    break
            
            if col_match:
                if col_match in numeric_columns:
                    stats = data[col_match].describe().to_dict()
                    fig = px.box(data, y=col_match, title=f"Distribution of {col_match}")
                    return f"**Summary statistics for {col_match}:**\n" + \
                           f"Count: {stats['count']:.0f}\n" + \
                           f"Mean: {stats['mean']:.2f}\n" + \
                           f"Std Dev: {stats['std']:.2f}\n" + \
                           f"Min: {stats['min']:.2f}\n" + \
                           f"25%: {stats['25%']:.2f}\n" + \
                           f"Median: {stats['50%']:.2f}\n" + \
                           f"75%: {stats['75%']:.2f}\n" + \
                           f"Max: {stats['max']:.2f}", fig
                elif col_match in categorical_columns:
                    value_counts = data[col_match].value_counts()
                    fig = px.pie(values=value_counts.values, names=value_counts.index, 
                               title=f"Distribution of {col_match}")
                    value_summary = "\n".join([f"- {val}: {count}" for val, count in value_counts.items()])
                    return f"**Value counts for {col_match}:**\n\n{value_summary}", fig
            else:
                # General summary
                numeric_summary = data[numeric_columns].describe().transpose()
                return f"**Dataset Summary:**\nTotal rows: {len(data)}\nTotal columns: {len(available_columns)}\n\n{numeric_summary.to_string()}", None
        
        # Count queries for projects by status
        if re.search(r"how many projects (?:have|are)(?: project)? status(?: as| is| =)? (red|green|yellow|amber|r\b|g\b|y\b|a\b)", question_lower):
            color_match = re.search(r"status(?:.*?)(red|green|yellow|amber|r\b|g\b|y\b|a\b)", question_lower)
            if color_match:
                status_color = color_match.group(1).lower().strip()
                
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
                
                # Count matches
                count = 0
                matched_values = []
                for val in possible_values:
                    val_count = data[data[status_col] == val].shape[0]
                    if val_count > 0:
                        count += val_count
                        matched_values.append(f"{val}: {val_count}")
                
                response = f"**There are {count} projects with {display_color} status.**"
                if len(matched_values) > 0:
                    response += f"\n\nBreakdown: {', '.join(matched_values)}"
                
                return response, None
        
        # If we've reached this point, provide a helpful response
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

def display_faq(current_data):
    """Display frequently asked questions"""
    faq_items = {}
    if not current_data.empty:
        faq_items = {
            "What is the total revenue?": f"The total revenue in the current filtered data is ${current_data['Revenue'].sum():,.0f}." if 'Revenue' in current_data else "Revenue data not available.",
            "How many projects are there in total?": f"There are {current_data.shape[0]} projects in the current filtered data.",
            "Which executive has the most projects?": (f"The executive with the most projects is {current_data['Exective'].mode()[0]} with {current_data['Exective'].value_counts().max()} projects." if 'Exective' in current_data and not current_data['Exective'].dropna().empty and len(current_data['Exective'].mode()) > 0 else "Executive data not available or insufficient."),
            "What are the different project statuses?": (f"The project statuses are: {', '.join([str(x) for x in current_data['Project Status (R/G/Y)'].unique() if pd.notna(x)])}." if 'Project Status (R/G/Y)' in current_data else "Project status data not available.")
        }
    else:
        faq_items["No data loaded"] = "Please load data to see relevant FAQs."

    st.subheader("❓ Frequently Asked Questions")
    if not faq_items:
        st.write("Load data to see FAQs.")
        return
        
    for question, answer in faq_items.items():
        with st.expander(question):
            st.write(answer) 