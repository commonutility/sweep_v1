#!/usr/bin/env python
"""
Trading-Copilot Runner Script
Starts the Gateway API service
"""

import os
import sys
import logging
import uvicorn
import subprocess
from dotenv import load_dotenv

# Add the parent directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Verify required packages are installed
def check_dependencies():
    required_packages = [
        "fastapi", "uvicorn", "pydantic", 
        "langchain_core", "langchain_openai", "langchain_anthropic",
        "openai", "anthropic", "redis", "jose", 
        "dotenv", "multipart"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"Missing dependencies: {', '.join(missing_packages)}")
        print("Please install them with: conda install [package-names] -c conda-forge")
        sys.exit(1)
    else:
        print("All required dependencies are installed!")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("trading_copilot")

def main():
    """Main entry point for Trading-Copilot"""
    
    # Check all required dependencies are installed
    check_dependencies()
    
    # Load environment variables from .env file
    dotenv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    load_dotenv(dotenv_path)
    
    logger.info("Starting Trading-Copilot Gateway API")
    logger.info(f"LLM Provider: {os.getenv('LLM_PROVIDER', 'openai')}")
    logger.info(f"LLM Model: {os.getenv('LLM_MODEL', 'gpt-4o')}")
    
    # Check for API keys
    if os.getenv('LLM_PROVIDER') == 'openai' and not os.getenv('OPENAI_API_KEY'):
        logger.warning("OPENAI_API_KEY not set. You need to configure this in the .env file.")
    
    if os.getenv('LLM_PROVIDER') == 'anthropic' and not os.getenv('ANTHROPIC_API_KEY'):
        logger.warning("ANTHROPIC_API_KEY not set. You need to configure this in the .env file.")
    
    # Start the FastAPI gateway
    try:
        # Import here to ensure environment variables are loaded first
        from api.gateway import app
        
        # Run the server
        uvicorn.run(
            "api.gateway:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except Exception as e:
        logger.error(f"Error starting Trading-Copilot: {str(e)}", exc_info=True)
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
