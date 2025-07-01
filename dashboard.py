# Compatibility redirect for existing Streamlit Cloud deployments
# This file runs the new main.py structure directly

import streamlit as st
import sys
import os

# Add current directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Run the main application by executing main.py content
try:
    # Read and execute main.py content directly
    main_file_path = os.path.join(current_dir, 'main.py')
    
    if os.path.exists(main_file_path):
        with open(main_file_path, 'r', encoding='utf-8') as f:
            main_content = f.read()
        
        # Execute the main.py content
        exec(main_content)
    else:
        st.error("❌ main.py file not found")
        st.info("Please ensure main.py is present in the repository.")
        
except Exception as e:
    st.error(f"❌ Error running application: {e}")
    st.info("📋 Error details for debugging:")
    st.code(f"Exception: {str(e)}\nType: {type(e).__name__}")
    
    # Show available files for debugging
    try:
        files = os.listdir(current_dir)
        st.info(f"📁 Available files: {files}")
    except:
        pass