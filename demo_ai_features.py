#!/usr/bin/env python3
"""
AI Features Demo for Avathon Analytics Dashboard

This script demonstrates the AI-powered analytics capabilities.
Run this after setting up the dashboard to test AI features.
"""

import pandas as pd
import sys
import os

# Add the current directory to path to import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from pages.chat_analytics import analyze_data_locally, get_smart_suggestions
    print("✅ Successfully imported chat analytics modules")
except ImportError as e:
    print(f"❌ Failed to import modules: {e}")
    sys.exit(1)

def create_sample_data():
    """Create sample data for demonstration"""
    data = {
        'Customer Name': ['Aramco', 'Shell', 'BP', 'ExxonMobil', 'Chevron'] * 4,
        'Project Status (R/G/Y)': ['Red', 'Green', 'Yellow', 'Green', 'Red'] * 4,
        'Exective': ['Alice', 'Bob', 'Charlie', 'Diana', 'Eve'] * 4,
        'Revenue': [100000, 250000, 150000, 300000, 80000] * 4,
        'Geography': ['USA', 'Europe', 'Asia', 'USA', 'Europe'] * 4,
        'Customer Health': ['Good', 'Excellent', 'Fair', 'Good', 'Poor'] * 4
    }
    return pd.DataFrame(data)

def demo_smart_suggestions(df):
    """Demonstrate smart suggestions feature"""
    print("\n🔍 Smart Suggestions Demo")
    print("=" * 40)
    
    suggestions = get_smart_suggestions(df)
    print("Generated suggestions based on your data:")
    for i, suggestion in enumerate(suggestions, 1):
        print(f"{i}. {suggestion}")

def demo_local_analysis(df):
    """Demonstrate local analysis capabilities"""
    print("\n🧠 Local Analysis Demo")
    print("=" * 40)
    
    # Test queries
    test_queries = [
        "What is the total revenue?",
        "How many projects have red status?",
        "Give me a comprehensive analysis of this dataset",
        "What are the biggest risks I should be aware of?",
        "What recommendations do you have?",
        "How are different executives performing?"
    ]
    
    for query in test_queries:
        print(f"\n🤔 Question: {query}")
        print("-" * 50)
        try:
            response, fig = analyze_data_locally(query, df)
            print("📊 Response:")
            print(response[:300] + "..." if len(response) > 300 else response)
            if fig:
                print("📈 Visualization: Chart generated successfully")
            else:
                print("📈 Visualization: No chart generated")
        except Exception as e:
            print(f"❌ Error: {e}")

def demo_ai_capabilities():
    """Demonstrate AI integration capabilities"""
    print("\n🤖 AI Integration Demo")
    print("=" * 40)
    
    try:
        import openai
        print("✅ OpenAI package available")
        print("   - Supports GPT-3.5-turbo, GPT-4, GPT-4-turbo")
        print("   - Requires API key configuration")
    except ImportError:
        print("❌ OpenAI package not installed")
        print("   - Run: pip install openai>=1.0.0")
    
    try:
        from anthropic import Anthropic
        print("✅ Anthropic package available")
        print("   - Supports Claude-3 Sonnet, Haiku, Opus")
        print("   - Requires API key configuration")
    except ImportError:
        print("❌ Anthropic package not installed")
        print("   - Run: pip install anthropic>=0.18.0")

def main():
    print("🤖 Avathon Analytics - AI Features Demo")
    print("=" * 50)
    
    # Create sample data
    print("📊 Creating sample data...")
    df = create_sample_data()
    print(f"   - Created dataset with {len(df)} rows and {len(df.columns)} columns")
    print(f"   - Columns: {', '.join(df.columns)}")
    
    # Demo features
    demo_smart_suggestions(df)
    demo_local_analysis(df)
    demo_ai_capabilities()
    
    print("\n🚀 Next Steps:")
    print("1. Run the dashboard: streamlit run main.py")
    print("2. Navigate to Chat Analytics page")
    print("3. Try the AI features with your own data")
    print("4. Configure OpenAI or Anthropic API keys for enhanced AI")
    
    print("\n💡 Example AI Questions to Try:")
    print("- 'Analyze our customer performance and identify risks'")
    print("- 'What trends do you see in our project data?'")
    print("- 'Which executives need support and why?'")
    print("- 'Give me actionable recommendations for improvement'")
    print("- 'Create a comprehensive executive summary'")

if __name__ == "__main__":
    main() 