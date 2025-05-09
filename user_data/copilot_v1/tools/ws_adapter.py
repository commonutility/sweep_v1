"""
WebSocket Adapter for Trading-Copilot
Part of Layer 4 in the architecture - Tool Adapters
"""

import logging
import json
import asyncio
from typing import Dict, List, Any, Optional, Union, AsyncGenerator
import websockets
import os
from urllib.parse import urljoin

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
WS_BASE_URL = os.getenv("FREQTRADE_WS_URL", "ws://127.0.0.1:8080/api/v1/message/ws")
WS_TOKEN = os.getenv("FREQTRADE_WS_TOKEN", "")

# WebSocket listener
async def fetch_from_websocket(
    channel: str,
    timeout: Optional[float] = 5.0
) -> Dict[str, Any]:
    """
    Connect to Freqtrade's WebSocket and listen for messages on a specific channel
    """
    logger.info(f"Connecting to WebSocket on channel: {channel}")
    
    if not WS_TOKEN:
        return {
            "error": "WebSocket token not configured. Please set FREQTRADE_WS_TOKEN environment variable.",
            "messages": []
        }
    
    # Validate channel
    valid_channels = ["trades", "whitelist", "logs", "status", "analyzed_df"]
    if channel not in valid_channels:
        return {
            "error": f"Invalid channel. Must be one of: {', '.join(valid_channels)}",
            "messages": []
        }
    
    try:
        messages = []
        
        # Connect to WebSocket
        async with websockets.connect(WS_BASE_URL) as websocket:
            # Send authentication message
            auth_message = {
                "type": "subscribe",
                "data": {
                    "token": WS_TOKEN,
                    "channels": [channel]
                }
            }
            await websocket.send(json.dumps(auth_message))
            
            # Wait for confirmation
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5)
                response_data = json.loads(response)
                
                if response_data.get("type") != "subscription" or not response_data.get("success", False):
                    return {
                        "error": f"Failed to subscribe to channel: {response_data.get('message', 'Unknown error')}",
                        "messages": []
                    }
            except asyncio.TimeoutError:
                return {
                    "error": "Timeout waiting for subscription confirmation",
                    "messages": []
                }
            
            # Listen for messages with timeout
            try:
                start_time = asyncio.get_event_loop().time()
                while True:
                    elapsed = asyncio.get_event_loop().time() - start_time
                    if timeout and elapsed > timeout:
                        break
                    
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=min(1.0, timeout - elapsed if timeout else 1.0))
                        message_data = json.loads(message)
                        
                        # Only collect messages for the requested channel
                        if message_data.get("type") == channel:
                            messages.append(message_data)
                            
                            # Special case: For status channel, one message is usually enough
                            if channel == "status":
                                break
                    except asyncio.TimeoutError:
                        continue
            except Exception as e:
                logger.error(f"Error receiving messages: {str(e)}", exc_info=True)
                
        # Process collected messages
        return {
            "channel": channel,
            "messages": messages,
            "count": len(messages),
            "timeout": timeout
        }
        
    except Exception as e:
        logger.error(f"Error connecting to WebSocket: {str(e)}", exc_info=True)
        return {
            "error": f"Error connecting to WebSocket: {str(e)}",
            "messages": []
        }

async def stream_websocket(
    channel: str,
    callback,
    duration: Optional[float] = None
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Stream WebSocket messages for a specific duration.
    This is an advanced usage, primarily for internal system use.
    """
    logger.info(f"Streaming WebSocket on channel: {channel}")
    
    if not WS_TOKEN:
        yield {
            "error": "WebSocket token not configured. Please set FREQTRADE_WS_TOKEN environment variable.",
        }
        return
    
    # Validate channel
    valid_channels = ["trades", "whitelist", "logs", "status", "analyzed_df"]
    if channel not in valid_channels:
        yield {
            "error": f"Invalid channel. Must be one of: {', '.join(valid_channels)}",
        }
        return
    
    try:
        # Connect to WebSocket
        async with websockets.connect(WS_BASE_URL) as websocket:
            # Send authentication message
            auth_message = {
                "type": "subscribe",
                "data": {
                    "token": WS_TOKEN,
                    "channels": [channel]
                }
            }
            await websocket.send(json.dumps(auth_message))
            
            # Wait for confirmation
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5)
                response_data = json.loads(response)
                
                if response_data.get("type") != "subscription" or not response_data.get("success", False):
                    yield {
                        "error": f"Failed to subscribe to channel: {response_data.get('message', 'Unknown error')}",
                    }
                    return
            except asyncio.TimeoutError:
                yield {
                    "error": "Timeout waiting for subscription confirmation",
                }
                return
            
            # Stream messages until duration is reached
            start_time = asyncio.get_event_loop().time()
            while True:
                if duration and asyncio.get_event_loop().time() - start_time > duration:
                    break
                
                try:
                    message = await websocket.recv()
                    message_data = json.loads(message)
                    
                    # Only process messages for the requested channel
                    if message_data.get("type") == channel:
                        # Process through callback if provided
                        if callback:
                            processed = await callback(message_data)
                            yield processed
                        else:
                            yield message_data
                except Exception as e:
                    logger.error(f"Error in WebSocket stream: {str(e)}", exc_info=True)
                    yield {"error": f"Stream error: {str(e)}"}
                    break
    
    except Exception as e:
        logger.error(f"Error setting up WebSocket stream: {str(e)}", exc_info=True)
        yield {"error": f"Error setting up WebSocket stream: {str(e)}"}

# Convenience methods for specific WebSocket channels
async def get_status_update() -> Dict[str, Any]:
    """
    Get latest status update from the bot
    """
    return await fetch_from_websocket("status", timeout=3.0)

async def get_trade_updates(timeout: float = 5.0) -> Dict[str, Any]:
    """
    Get recent trade updates from the bot
    """
    return await fetch_from_websocket("trades", timeout=timeout)

async def get_log_updates(timeout: float = 5.0) -> Dict[str, Any]:
    """
    Get recent log messages from the bot
    """
    return await fetch_from_websocket("logs", timeout=timeout)

async def get_whitelist_updates() -> Dict[str, Any]:
    """
    Get whitelist updates from the bot
    """
    return await fetch_from_websocket("whitelist", timeout=3.0)
