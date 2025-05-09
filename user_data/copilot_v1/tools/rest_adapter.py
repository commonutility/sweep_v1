"""
REST API Adapter for Trading-Copilot
Part of Layer 4 in the architecture - Tool Adapters
"""

import logging
import json
import aiohttp
from typing import Dict, List, Any, Optional, Union
import os
from urllib.parse import urljoin

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
API_BASE_URL = os.getenv("FREQTRADE_API_URL", "http://127.0.0.1:8080")
API_USERNAME = os.getenv("FREQTRADE_API_USERNAME", "")
API_PASSWORD = os.getenv("FREQTRADE_API_PASSWORD", "")
JWT_TOKEN = os.getenv("FREQTRADE_JWT_TOKEN", "")

# Allowed endpoints for security
ALLOWED_ENDPOINTS = [
    "/api/v1/status",
    "/api/v1/profit",
    "/api/v1/balance",
    "/api/v1/trades",
    "/api/v1/trade",
    "/api/v1/pairs",
    "/api/v1/performance",
    "/api/v1/count",
    "/api/v1/daily",
    "/api/v1/stats",
    "/api/v1/whitelist",
    "/api/v1/blacklist",
    "/api/v1/locks",
    "/api/v1/show_config",
    "/api/v1/strategies",
    "/api/v1/strategy",
    "/api/v1/ping",
]

async def get_auth_token() -> str:
    """
    Get JWT auth token for the Freqtrade API
    """
    if JWT_TOKEN:
        return JWT_TOKEN
        
    if not API_USERNAME or not API_PASSWORD:
        raise ValueError("API_USERNAME and API_PASSWORD must be set if JWT_TOKEN is not provided")
    
    async with aiohttp.ClientSession() as session:
        try:
            auth_url = urljoin(API_BASE_URL, "/api/v1/token/login")
            auth_data = {
                "username": API_USERNAME,
                "password": API_PASSWORD
            }
            
            async with session.post(auth_url, json=auth_data) as response:
                if response.status != 200:
                    raise ValueError(f"Authentication failed: {response.status}")
                
                auth_result = await response.json()
                return auth_result.get("access_token", "")
                
        except Exception as e:
            logger.error(f"Error getting auth token: {str(e)}", exc_info=True)
            raise

async def call_rest_api(
    endpoint: str,
    method: str = "GET",
    params: Optional[Dict[str, Any]] = None,
    data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Call the Freqtrade REST API
    """
    logger.info(f"Calling REST API: {endpoint}")
    
    # Validate endpoint for security
    if not any(endpoint.startswith(allowed) for allowed in ALLOWED_ENDPOINTS):
        return {
            "error": f"Endpoint not allowed. Must be one of: {', '.join(ALLOWED_ENDPOINTS)}",
            "status_code": 403
        }
    
    try:
        # Get auth token
        token = await get_auth_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        # Prepare URL
        url = urljoin(API_BASE_URL, endpoint)
        
        # Make request
        async with aiohttp.ClientSession() as session:
            method = method.upper()
            req_kwargs = {
                "headers": headers,
                "params": params,
            }
            
            if method in ["POST", "PUT", "PATCH"] and data:
                req_kwargs["json"] = data
            
            async with session.request(method, url, **req_kwargs) as response:
                try:
                    result = await response.json()
                except Exception:
                    # If not JSON, try to get text
                    result = {"text": await response.text()}
                
                return {
                    "status_code": response.status,
                    "result": result,
                    "headers": dict(response.headers),
                    "url": str(response.url),
                    "method": method,
                }
    
    except Exception as e:
        logger.error(f"Error calling REST API: {str(e)}", exc_info=True)
        return {
            "error": f"Error calling REST API: {str(e)}",
            "status_code": 500
        }

# Convenience methods for common API calls
async def get_status() -> Dict[str, Any]:
    """
    Get current status of the bot
    """
    return await call_rest_api("/api/v1/status")

async def get_profit() -> Dict[str, Any]:
    """
    Get profit statistics
    """
    return await call_rest_api("/api/v1/profit")

async def get_balance() -> Dict[str, Any]:
    """
    Get account balance
    """
    return await call_rest_api("/api/v1/balance")

async def get_trades(limit: int = 50) -> Dict[str, Any]:
    """
    Get trade history
    """
    return await call_rest_api("/api/v1/trades", params={"limit": limit})

async def get_trade(trade_id: int) -> Dict[str, Any]:
    """
    Get specific trade by ID
    """
    return await call_rest_api(f"/api/v1/trade/{trade_id}")

async def get_pairs() -> Dict[str, Any]:
    """
    Get available pairs
    """
    return await call_rest_api("/api/v1/pairs")

async def get_performance() -> Dict[str, Any]:
    """
    Get performance by pair
    """
    return await call_rest_api("/api/v1/performance")

async def get_daily_stats() -> Dict[str, Any]:
    """
    Get daily profit statistics
    """
    return await call_rest_api("/api/v1/daily")

async def get_strategies() -> Dict[str, Any]:
    """
    Get available strategies
    """
    return await call_rest_api("/api/v1/strategies")

async def get_strategy(strategy_name: str) -> Dict[str, Any]:
    """
    Get strategy details
    """
    return await call_rest_api(f"/api/v1/strategy/{strategy_name}")
