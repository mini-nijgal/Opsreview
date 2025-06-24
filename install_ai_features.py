#!/usr/bin/env python3
"""
AI Features Installation Script for Avathon Analytics Dashboard

This script helps install optional AI/LLM dependencies for enhanced chat analytics.
"""

import subprocess
import sys
import importlib

def check_package(package_name):
    """Check if a package is installed"""
    try:
        importlib.import_module(package_name)
        return True
    except ImportError:
        return False

def install_package(package_name):
    """Install a package using pip"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
        return True
    except subprocess.CalledProcessError:
        return False

def main():
    print("🤖 Avathon Analytics - AI Features Installation")
    print("=" * 50)
    
    packages = {
        "openai": "openai>=1.0.0",
        "anthropic": "anthropic>=0.18.0"
    }
    
    installed_packages = []
    failed_packages = []
    
    for package_name, package_spec in packages.items():
        print(f"\nChecking {package_name}...")
        
        if check_package(package_name):
            print(f"✅ {package_name} is already installed")
            installed_packages.append(package_name)
        else:
            print(f"📦 Installing {package_name}...")
            if install_package(package_spec):
                print(f"✅ {package_name} installed successfully")
                installed_packages.append(package_name)
            else:
                print(f"❌ Failed to install {package_name}")
                failed_packages.append(package_name)
    
    print("\n" + "=" * 50)
    print("Installation Summary:")
    print(f"✅ Successfully installed/verified: {len(installed_packages)} packages")
    
    if installed_packages:
        print("   - " + "\n   - ".join(installed_packages))
    
    if failed_packages:
        print(f"❌ Failed to install: {len(failed_packages)} packages")
        print("   - " + "\n   - ".join(failed_packages))
        print("\nTry installing manually:")
        for package in failed_packages:
            print(f"   pip install {packages[package]}")
    
    print("\n🚀 Next Steps:")
    print("1. Run your Streamlit dashboard: streamlit run main.py")
    print("2. Navigate to Chat Analytics page")
    print("3. Configure your AI provider in the sidebar")
    print("4. Add your API key (OpenAI or Anthropic)")
    print("5. Enjoy AI-powered data analytics!")
    
    if "openai" in installed_packages:
        print("\n🔑 OpenAI Setup:")
        print("   - Get API key: https://platform.openai.com/api-keys")
        print("   - Models available: GPT-3.5-turbo, GPT-4, GPT-4-turbo")
    
    if "anthropic" in installed_packages:
        print("\n🔑 Anthropic Setup:")
        print("   - Get API key: https://console.anthropic.com/")
        print("   - Models available: Claude-3 Sonnet, Haiku, Opus")

if __name__ == "__main__":
    main() 