# Compatibility redirect for existing Streamlit Cloud deployments
# This file imports and runs the new main.py structure

import streamlit as st
import sys
import os

# Add current directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Import and run the main application
try:
    import main
except ImportError as e:
    st.error(f"Error importing main module: {e}")
    st.info("Please ensure all required files are present in the repository.")
except Exception as e:
    st.error(f"Error running application: {e}")
    st.info("Please check the application logs for more details.")