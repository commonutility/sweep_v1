#!/usr/bin/env python3
"""
Freqtrade Copilot V2 - Main script
LLM interface for making calls to the Freqtrade API

Usage:
    python user_data/copilot_v2/run.py
    python -m user_data.copilot_v2.run

Requirements:
    - OpenAI API key set as OPENAI_API_TOKEN environment variable
    - Running Freqtrade instance with API enabled
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add the freqtrade directory to sys.path for proper module imports
freqtrade_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(freqtrade_dir))

# pylint: disable=wrong-import-position
# isort: skip
from user_data.copilot_v2.api.gateway import FreqtradeGateway

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file if it exists
load_dotenv()

def parse_arguments():
    """
    Parse command line arguments
    """
    parser = argparse.ArgumentParser(
        description="Freqtrade Copilot V2 - LLM interface for Freqtrade API"
    )
    parser.add_argument(
        "--model", 
        type=str, 
        default=None,
        help="OpenAI model to use (default: o3)"
    )
    parser.add_argument(
        "--api-url", 
        type=str, 
        default=None,
        help="Freqtrade API URL (default: from environment or http://127.0.0.1:8080)"
    )
    parser.add_argument(
        "--username", 
        type=str, 
        default=None,
        help="Freqtrade API username (default: from environment or 'a')"
    )
    parser.add_argument(
        "--password", 
        type=str, 
        default=None,
        help="Freqtrade API password (default: from environment or 'a')"
    )
    
    return parser.parse_args()

async def main():
    """
    Main entry point for the Freqtrade Copilot V2
    """
    args = parse_arguments()
    # Set environment variables if provided via command line
    if args.api_url:
        os.environ["FREQTRADE_API_URL"] = args.api_url
    if args.username:
        os.environ["FREQTRADE_API_USERNAME"] = args.username
    if args.password:
        os.environ["FREQTRADE_API_PASSWORD"] = args.password
    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_TOKEN"):
        logger.error("OPENAI_API_TOKEN environment variable is not set. Please set it and try again.")
        return
    print("""
    ╔═══════════════════════════════════════════╗
    ║                                           ║
    ║         Freqtrade Copilot V2              ║
    ║    LLM Interface for Freqtrade API        ║
    ║                                           ║
    ╚═══════════════════════════════════════════╝

    Type 'exit' or 'quit' to end the session.
    Type 'clear' to start a new conversation.
    """)

    try:
        # Initialize the gateway
        gateway = FreqtradeGateway(model=args.model)
        print(args.model)

        # Main interaction loop
        while True:
            user_input = input("\n🤖 > ")

            # Check for exit command
            if user_input.lower() in ["exit", "quit"]:
                print("Goodbye!")
                break

            # Check for clear command
            if user_input.lower() == "clear":
                gateway.clear_conversation()
                print("Conversation cleared. Starting fresh.")
                continue

            # Skip empty input
            if not user_input.strip():
                continue
                
            # Process the query
            try:
                response = await gateway.process_query(user_input)
                print(f"\n{response}")
            except Exception as e:
                logger.error(f"Error processing query: {str(e)}", exc_info=True)
                print(f"\nError: {str(e)}")
    
    except KeyboardInterrupt:
        print("\nGoodbye!")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        print(f"\nAn unexpected error occurred: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
