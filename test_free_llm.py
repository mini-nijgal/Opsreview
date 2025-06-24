#!/usr/bin/env python3
"""
Test script for Free LLM integration
Tests the Hugging Face Inference API functionality
"""

import requests
import pandas as pd
import time

def test_free_llm():
    """Test the free LLM functionality"""
    print("🆓 Testing Free LLM Integration...")
    print("=" * 50)
    
    # Test models
    models_to_test = [
        "google/flan-t5-large",
        "microsoft/DialoGPT-medium"
    ]
    
    # Create sample data
    sample_data = {
        'Customer': ['Company A', 'Company B', 'Company C'],
        'Revenue': [100000, 150000, 200000],
        'Status': ['Green', 'Yellow', 'Red']
    }
    df = pd.DataFrame(sample_data)
    
    print("Sample Data:")
    print(df)
    print("\n" + "=" * 50)
    
    for model in models_to_test:
        print(f"\n🤖 Testing model: {model}")
        print("-" * 30)
        
        try:
            # Test API endpoint
            api_url = f"https://api-inference.huggingface.co/models/{model}"
            
            # Simple test prompt
            prompt = "Analyze this data: Company A has $100,000 revenue with Green status. What insights can you provide?"
            
            payload = {
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": 100,
                    "temperature": 0.7,
                    "do_sample": True,
                    "return_full_text": False
                }
            }
            
            headers = {"Content-Type": "application/json"}
            # Note: In actual usage, user would provide their free HF token
            
            print(f"Making request to: {api_url}")
            start_time = time.time()
            
            response = requests.post(api_url, headers=headers, json=payload, timeout=30)
            
            end_time = time.time()
            response_time = round(end_time - start_time, 2)
            
            print(f"Response time: {response_time} seconds")
            print(f"Status code: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print("✅ Success!")
                print("Response:", str(result)[:200] + "..." if len(str(result)) > 200 else str(result))
                
            elif response.status_code == 503:
                print("⏳ Model is loading (503) - this is normal for free models")
                print("In the dashboard, users can try again in a few moments")
                
            else:
                print(f"❌ Error: Status {response.status_code}")
                print("Response:", response.text[:200])
                
        except requests.exceptions.Timeout:
            print("⏰ Request timed out - free models can be slow")
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
    
    print("\n" + "=" * 50)
    print("🎯 Test Summary:")
    print("- Free LLM uses Hugging Face Inference API")
    print("- Requires FREE Hugging Face token (no payment needed)")
    print("- Models may take time to 'warm up' (503 errors)")
    print("- Response times vary (can be 10-30 seconds)")
    print("- Perfect for free AI-powered analytics!")
    print("\n✨ Users need to get a free HF token, then can use AI immediately!")
    print("\n🔑 Get token at: https://huggingface.co/settings/tokens")

if __name__ == "__main__":
    test_free_llm() 