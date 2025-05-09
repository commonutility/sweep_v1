"""
API Gateway - Connects the LLM interface with the Freqtrade API
"""

import os
import json
import asyncio
from typing import Dict, List, Any, Optional, Union, Tuple
import logging
from openai import OpenAI
import sys
import inspect

# Import our tools
from user_data.copilot_v2.tools.function_tools import FREQTRADE_TOOLS
from user_data.copilot_v2.tools import rest_adapter

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default model to use
DEFAULT_MODEL = "gpt-o1"

def get_openai_client():
    """
    Get the OpenAI client with API key
    Raises ValueError if API key is not set
    """
    # Get OpenAI API key
    api_token = os.getenv("OPENAI_API_KEY")
    if not api_token:
        raise ValueError("OPENAI_API_TOKEN environment variable is not set")

    # Initialize and return OpenAI client
    return OpenAI(api_key=api_token)

class FreqtradeGateway:
    """
    Gateway class that connects OpenAI's API with Freqtrade's API
    """

    def __init__(self, model: str = DEFAULT_MODEL):
        """
        Initialize the gateway with the specified model
        """
        self.model = model
        self.client = None  # Will be initialized when needed
        self.messages = []
        
        # Initialize chat with system message
        self.messages.append({
            "role": "system", 
            "content": "You are a helpful assistant for managing a Freqtrade cryptocurrency trading bot. "
                      "You can help users check the status of trades, manage the bot, and analyze performance. "
                      "Always provide concise answers. When appropriate, use the available tools to fetch real data."
        })
        
        # Create a map of function names to their corresponding async functions
        self.function_map = {}
        for name, func in inspect.getmembers(rest_adapter, inspect.iscoroutinefunction):
            self.function_map[name] = func
    
    async def process_query(self, query: str) -> str:
        """
        Process a user query by sending it to the LLM and executing any function calls
        """
        # Add user message to conversation history
        self.messages.append({"role": "user", "content": query})
        
        # Get response from OpenAI
        response = await self._get_llm_response()
        
        # Add assistant's response to conversation history
        if response:
            self.messages.append(response)

            print(response)
            
            # Extract content or function call result
            if "content" in response and response["content"]:
                return response["content"]
            elif "tool_calls" in response:
                tool_results = []
                for tool_call in response.get("tool_calls", []):
                    result = await self._process_tool_call(tool_call, query)
                    if result:
                        tool_results.append(result)
                
                if tool_results:
                    return "\n\n".join(tool_results)
        
        return "I encountered an error processing your request."
    
    async def _get_llm_response(self) -> Dict[str, Any]:
        """
        Get a response from the LLM
        """
        try:
            # Initialize the client if not already done
            if self.client is None:
                self.client = get_openai_client()

            completion = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=self.model,
                messages=self.messages,
                tools=FREQTRADE_TOOLS
            )

            # Extract and return the response
            if completion.choices and len(completion.choices) > 0:
                return completion.choices[0].message.model_dump()

            return {}

        except Exception as e:
            logger.error(f"Error getting LLM response: {str(e)}", exc_info=True)
            return {"content": f"Error: {str(e)}"}
    
    async def _process_tool_call(self, tool_call: Dict[str, Any], user_query: str) -> str:
        """
        Process a tool call by executing the corresponding function
        """
        try:
            function = tool_call.get("function", {})
            function_name = function.get("name")
            arguments = json.loads(function.get("arguments", "{}"))
            
            logger.info(f"Executing function: {function_name} with args: {arguments}")
            
            # Get the corresponding async function
            if function_name in self.function_map:
                async_func = self.function_map[function_name]
                
                # Execute the function with the provided arguments
                result = await async_func(**arguments)
                
                pretty_json = json.dumps(result, indent=2)

                # Add the function result to the conversation history as a tool message
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.get("id"),
                    "name": function_name,
                    "content": pretty_json,
                })

                # Summarize the JSON payload in user-friendly form, with context.
                summary = await self._summarize_json(function_name, pretty_json, user_query)

                # Add the summary back into the ongoing conversation so the model keeps context.
                self.messages.append({"role": "assistant", "content": summary})

                raw_block = f"**{function_name}** result:\n```json\n{pretty_json}\n```"

                return f"{raw_block}\n\n---\n\n{summary}"
            else:
                error_msg = f"Function {function_name} not found in rest_adapter"
                logger.error(error_msg)
                return f"Error: {error_msg}"
        
        except Exception as e:
            logger.error(f"Error processing tool call: {str(e)}", exc_info=True)
            return f"Error executing function: {str(e)}"

    async def _summarize_json(self, function_name: str, json_str: str, user_query: str) -> str:
        """Summarize a JSON payload into a concise response in the context of the user's question."""

        # Guard against excessively large payloads
        MAX_JSON_CHARS = 4000
        if len(json_str) > MAX_JSON_CHARS:
            json_str = json_str[:MAX_JSON_CHARS - 100] + "\n…TRUNCATED…"

        system_prompt = (
            "You are a helpful trading assistant. "
            "Given JSON data returned from the Freqtrade API, answer the user's question "
            "clearly and concisely. Highlight key numbers and use bullet points when helpful."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    f'The user asked: "{user_query}"\n\n'
                    f'The function `{function_name}` returned this JSON:\n```json\n{json_str}\n```\n'
                    "Please summarise this result for the user."
                ),
            },
        ]

        try:
            completion = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=self.model,
                messages=messages,
            )

            return completion.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error during JSON summarisation: {str(e)}", exc_info=True)
            return "(Error summarising JSON payload)"

    def clear_conversation(self) -> None:
        """
        Clear the conversation history, keeping only the system message
        """
        system_message = self.messages[0]
        self.messages = [system_message]
