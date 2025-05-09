"""
REST API Adapter for Freqtrade API - Copilot V2
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
API_USERNAME = os.getenv("FREQTRADE_API_USERNAME", "a")
API_PASSWORD = os.getenv("FREQTRADE_API_PASSWORD", "a")
# If a valid JWT token is already available (for example obtained manually via
# /api/v1/token/login), expose it via the environment variable
# `FREQTRADE_JWT_TOKEN`.  If it is not set we will obtain a fresh token using
# HTTP-Basic login.
JWT_TOKEN = os.getenv("FREQTRADE_JWT_TOKEN", "")

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

            # Freqtrade expects HTTP Basic authentication for this endpoint, not a JSON payload.
            # aiohttp.BasicAuth will build the proper "Authorization: Basic <base64>" header.
            async with session.post(
                auth_url,
                auth=aiohttp.BasicAuth(API_USERNAME, API_PASSWORD),
            ) as response:
                if response.status != 200:
                    raise ValueError(f"Authentication failed: {response.status}")

                # Read and parse the JSON **while the connection is still open**.
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

# API command implementations
async def available_pairs(timeframe: Optional[str] = None, stake_currency: Optional[str] = None) -> Dict[str, Any]:
    """
    Return available pair (backtest data) based on timeframe / stake_currency selection
    """
    params = {}
    if timeframe:
        params["timeframe"] = timeframe
    if stake_currency:
        params["stake_currency"] = stake_currency
    return await call_rest_api("/api/v1/available_pairs", params=params)

async def balance() -> Dict[str, Any]:
    """
    Get the account balance
    """
    return await call_rest_api("/api/v1/balance")

async def blacklist(add: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Show the current blacklist. Optionally add coins to the blacklist.
    """
    if add:
        return await call_rest_api("/api/v1/blacklist", method="POST", data={"blacklist": add})
    return await call_rest_api("/api/v1/blacklist")

async def cancel_open_order(trade_id: int) -> Dict[str, Any]:
    """
    Cancel open order for trade
    """
    return await call_rest_api(f"/api/v1/trades/{trade_id}/cancel", method="POST")

async def count() -> Dict[str, Any]:
    """
    Return the amount of open trades
    """
    return await call_rest_api("/api/v1/count")

async def daily() -> Dict[str, Any]:
    """
    Return the profits for each day, and amount of trades
    """
    return await call_rest_api("/api/v1/daily")

async def delete_lock(lock_id: int) -> Dict[str, Any]:
    """
    Delete (disable) lock from the database
    """
    return await call_rest_api(f"/api/v1/locks/{lock_id}", method="DELETE")

async def delete_trade(trade_id: int) -> Dict[str, Any]:
    """
    Delete trade from the database
    """
    return await call_rest_api(f"/api/v1/trades/{trade_id}", method="DELETE")

async def edge() -> Dict[str, Any]:
    """
    Return information about edge
    """
    return await call_rest_api("/api/v1/edge")

async def forcebuy(pair: str, price: Optional[float] = None) -> Dict[str, Any]:
    """
    Buy an asset
    """
    data = {"pair": pair}
    if price:
        data["price"] = price
    return await call_rest_api("/api/v1/forcebuy", method="POST", data=data)

async def forceenter(pair: str, side: str, price: Optional[float] = None) -> Dict[str, Any]:
    """
    Force entering a trade
    """
    data = {"pair": pair, "side": side}
    if price:
        data["price"] = price
    return await call_rest_api("/api/v1/forceenter", method="POST", data=data)

async def forceexit(trade_id: int, ordertype: Optional[str] = None, amount: Optional[float] = None) -> Dict[str, Any]:
    """
    Force-exit a trade
    """
    data = {}
    if ordertype:
        data["ordertype"] = ordertype
    if amount:
        data["amount"] = amount
    return await call_rest_api(f"/api/v1/forceexit/{trade_id}", method="POST", data=data)

async def health() -> Dict[str, Any]:
    """
    Provides a quick health check of the running bot
    """
    return await call_rest_api("/api/v1/health")

async def lock_add(pair: str, until: Optional[str] = None, side: Optional[str] = None, reason: Optional[str] = None) -> Dict[str, Any]:
    """
    Manually lock a specific pair
    """
    data = {"pair": pair}
    if until:
        data["until"] = until
    if side:
        data["side"] = side
    if reason:
        data["reason"] = reason
    return await call_rest_api("/api/v1/locks/add", method="POST", data=data)

async def locks() -> Dict[str, Any]:
    """
    Return current locks
    """
    return await call_rest_api("/api/v1/locks")

async def logs(limit: Optional[int] = None) -> Dict[str, Any]:
    """
    Show latest logs
    """
    params = {}
    if limit:
        params["limit"] = limit
    return await call_rest_api("/api/v1/logs", params=params)

async def pair_candles(pair: str, timeframe: str, limit: Optional[int] = None) -> Dict[str, Any]:
    """
    Return live dataframe for <pair><timeframe>
    """
    params = {"pair": pair, "timeframe": timeframe}
    if limit:
        params["limit"] = limit
    return await call_rest_api("/api/v1/pair_candles", params=params)

async def pair_history(pair: str, timeframe: str, strategy: Optional[str] = None, timerange: Optional[str] = None) -> Dict[str, Any]:
    """
    Return historic, analyzed dataframe
    """
    params = {"pair": pair, "timeframe": timeframe}
    if strategy:
        params["strategy"] = strategy
    if timerange:
        params["timerange"] = timerange
    return await call_rest_api("/api/v1/pair_history", params=params)

async def performance() -> Dict[str, Any]:
    """
    Return the performance of the different coins
    """
    return await call_rest_api("/api/v1/performance")

async def ping() -> Dict[str, Any]:
    """
    Simple ping
    """
    return await call_rest_api("/api/v1/ping")

async def plot_config() -> Dict[str, Any]:
    """
    Return plot configuration if the strategy defines one
    """
    return await call_rest_api("/api/v1/plot_config")

async def profit() -> Dict[str, Any]:
    """
    Return the profit summary
    """
    return await call_rest_api("/api/v1/profit")

async def reload_config() -> Dict[str, Any]:
    """
    Reload configuration
    """
    return await call_rest_api("/api/v1/reload_config", method="POST")

async def show_config() -> Dict[str, Any]:
    """
    Returns part of the configuration, relevant for trading operations
    """
    return await call_rest_api("/api/v1/show_config")

async def start() -> Dict[str, Any]:
    """
    Start the bot if it's in the stopped state
    """
    return await call_rest_api("/api/v1/start", method="POST")

async def pause() -> Dict[str, Any]:
    """
    Pause the bot if it's in the running state
    """
    return await call_rest_api("/api/v1/pause", method="POST")

async def stats() -> Dict[str, Any]:
    """
    Return the stats report (durations, sell-reasons)
    """
    return await call_rest_api("/api/v1/stats")

async def status() -> Dict[str, Any]:
    """
    Get the status of open trades
    """
    return await call_rest_api("/api/v1/status")

async def stop() -> Dict[str, Any]:
    """
    Stop the bot. Use `start` to restart
    """
    return await call_rest_api("/api/v1/stop", method="POST")

async def stopbuy() -> Dict[str, Any]:
    """
    Stop buying (but handle sells gracefully). Use `reload_config` to reset
    """
    return await call_rest_api("/api/v1/stopbuy", method="POST")

async def strategies() -> Dict[str, Any]:
    """
    Lists available strategies
    """
    return await call_rest_api("/api/v1/strategies")

async def strategy(strategy: str) -> Dict[str, Any]:
    """
    Get strategy details
    """
    return await call_rest_api(f"/api/v1/strategy/{strategy}")

async def sysinfo() -> Dict[str, Any]:
    """
    Provides system information (CPU, RAM usage)
    """
    return await call_rest_api("/api/v1/sysinfo")

async def trade(trade_id: int) -> Dict[str, Any]:
    """
    Return specific trade
    """
    return await call_rest_api(f"/api/v1/trade/{trade_id}")

async def trades(limit: Optional[int] = None, offset: Optional[int] = None) -> Dict[str, Any]:
    """
    Return trades history, sorted by id
    """
    params = {}
    if limit:
        params["limit"] = limit
    if offset:
        params["offset"] = offset
    return await call_rest_api("/api/v1/trades", params=params)

async def list_open_trades_custom_data(key: Optional[str] = None, limit: Optional[int] = None, offset: Optional[int] = None) -> Dict[str, Any]:
    """
    Return a dict containing open trades custom-datas
    """
    params = {}
    if key:
        params["key"] = key
    if limit:
        params["limit"] = limit
    if offset:
        params["offset"] = offset
    return await call_rest_api("/api/v1/open_trades_custom_data", params=params)

async def list_custom_data(trade_id: int, key: Optional[str] = None) -> Dict[str, Any]:
    """
    Return a dict containing custom-datas of a specified trade
    """
    params = {}
    if key:
        params["key"] = key
    return await call_rest_api(f"/api/v1/trades/{trade_id}/custom_data", params=params)

async def version() -> Dict[str, Any]:
    """
    Return the version of the bot
    """
    return await call_rest_api("/api/v1/version")

async def whitelist() -> Dict[str, Any]:
    """
    Show the current whitelist
    """
    return await call_rest_api("/api/v1/whitelist")
