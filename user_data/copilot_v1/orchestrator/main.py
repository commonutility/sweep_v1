"""
Orchestrator for Trading-Copilot
Layer 3 in the architecture
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, AsyncGenerator, Union
import asyncio
from datetime import datetime, timedelta

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import Tool, tool
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda

# LLM Imports will depend on which hosted model you use
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Tool adapters
from user_data.trading_copilot.tools.trade_tools import get_trades, get_performance, get_current_positions
from user_data.trading_copilot.tools.sql_adapter import run_sql_query
from user_data.trading_copilot.tools.rest_adapter import call_rest_api
from user_data.trading_copilot.tools.ws_adapter import fetch_from_websocket

# Cache
from user_data.trading_copilot.cache.redis_cache import RedisCache

# Initialize cache
cache = RedisCache(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    password=os.getenv("REDIS_PASSWORD", ""),
)

# Constants
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")  # or "anthropic"
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o")  # or "claude-3-opus-20240229"
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.0"))
LLM_API_KEY = os.getenv("LLM_API_KEY", "")

# Simple mock LLM for demonstration
class MockLLM:
    def __init__(self, model="mock-model", temperature=0.0, streaming=True):
        self.model = model
        self.temperature = temperature
        self.streaming = streaming
        logger.info(f"Using MockLLM with model={model}, temperature={temperature}")
    
    async def ainvoke(self, messages, **kwargs):
        # Simple mock response based on the query
        query = ""
        for m in messages:
            if isinstance(m, dict) and m.get('role') == 'user' and 'content' in m:
                query = m['content']
                break
            
        return f"This is a mock response to: {query}\n\nFor demonstration purposes only. In production, this would be an actual response from the LLM."
    
    async def astream(self, messages, **kwargs):
        response = await self.ainvoke(messages)
        words = response.split()
        for i in range(0, len(words), 3):
            chunk = " ".join(words[i:i+3])
            yield chunk
            await asyncio.sleep(0.1)  # Simulate streaming delay
    
    def with_structured_output(self, **kwargs):
        # For mock purposes, just return a properly structured runnable
        return MockRunnable(self)

class MockRunnable:
    def __init__(self, llm):
        self.llm = llm
    
    async def ainvoke(self, input_data, **kwargs):
        messages = input_data.get("messages", [])
        if not messages:
            # Try to construct messages from the input
            if isinstance(input_data, dict) and "query" in input_data:
                messages = [{"role": "user", "content": input_data["query"]}]
            elif isinstance(input_data, str):
                messages = [{"role": "user", "content": input_data}]
        
        result = await self.llm.ainvoke(messages)
        return result
    
    async def astream(self, input_data, **kwargs):
        messages = input_data.get("messages", [])
        if not messages and "query" in input_data:
            messages = [{"role": "user", "content": input_data["query"]}]
        
        async for chunk in self.llm.astream(messages):
            yield chunk

# Initialize LLM based on provider
def get_llm():
    if LLM_PROVIDER == "openai":
        return ChatOpenAI(
            model=LLM_MODEL,
            temperature=LLM_TEMPERATURE,
            api_key=os.getenv("OPENAI_API_KEY", LLM_API_KEY),
            streaming=True
        )
    elif LLM_PROVIDER == "anthropic":
        return ChatAnthropic(
            model=LLM_MODEL,
            temperature=LLM_TEMPERATURE,
            api_key=os.getenv("ANTHROPIC_API_KEY", LLM_API_KEY),
            streaming=True
        )
    elif LLM_PROVIDER == "mock":
        return MockLLM(model=LLM_MODEL, temperature=LLM_TEMPERATURE)
    else:
        raise ValueError(f"Unsupported LLM provider: {LLM_PROVIDER}")

# Define available tools
def get_available_tools() -> List[Tool]:
    """
    Define and return the available tools for the LLM to use
    """
    tools = [
        Tool(
            name="get_trades",
            func=get_trades,
            description="Get trade history filtered by pair, timeframe, or status",
            args_schema={
                "type": "object",
                "properties": {
                    "pair": {"type": "string", "description": "Trading pair (e.g., 'BTC/USDT')"},
                    "from_date": {"type": "string", "format": "date", "description": "Start date for filtering"},
                    "to_date": {"type": "string", "format": "date", "description": "End date for filtering"},
                    "status": {"type": "string", "enum": ["open", "closed", "all"], "description": "Trade status"}
                }
            },
            return_direct=False,
        ),
        Tool(
            name="get_performance",
            func=get_performance,
            description="Get performance metrics for the portfolio or specific pair",
            args_schema={
                "type": "object",
                "properties": {
                    "pair": {"type": "string", "description": "Trading pair (optional)"},
                    "timeframe": {"type": "string", "description": "Timeframe for metrics (e.g., '1d', '7d', '30d')"},
                    "metrics": {"type": "array", "items": {"type": "string"}, "description": "Specific metrics to retrieve"}
                }
            },
            return_direct=False,
        ),
        Tool(
            name="get_current_positions",
            func=get_current_positions,
            description="Get currently open positions",
            args_schema={
                "type": "object",
                "properties": {
                    "pair": {"type": "string", "description": "Filter by trading pair (optional)"},
                    "min_profit": {"type": "number", "description": "Minimum profit percentage (optional)"},
                    "max_age": {"type": "string", "description": "Maximum age of position (e.g., '2h', '1d')"}
                }
            },
            return_direct=False,
        ),
        Tool(
            name="run_sql_query",
            func=run_sql_query,
            description="Run a SQL query against the trades database (read-only)",
            args_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "SQL query to execute (SELECT only)"},
                    "parameters": {"type": "object", "description": "Query parameters"}
                },
                "required": ["query"]
            },
            return_direct=False,
        ),
    ]
    return tools

# Define system prompt
SYSTEM_PROMPT = """
You are Trading-Copilot, an AI assistant specialized in analyzing cryptocurrency trading performance using Freqtrade.
You have access to tools that can retrieve trade data, performance metrics, and current positions.

Only use the provided tools to answer questions about trading data. Never make up numbers or statistics.
Always base your answers on the actual data returned by the tools.

When responding:
1. First decide which tool you need
2. Call the appropriate tool with the required parameters
3. Analyze the data returned by the tool
4. Provide a clear, concise answer based on the data
5. For numerical analyses, consider including a chart by specifying a chart type and data

Remember that all financial data comes from Freqtrade, an algorithmic trading bot for cryptocurrency markets.
"""

# Intent classification 
async def classify_intent(query: str) -> Dict[str, Any]:
    """
    Classify the user's query to determine intent and required tools
    """
    intent_prompt = ChatPromptTemplate.from_messages([
        ("system", """
        You are an intent classifier for trading queries. Categorize the user's query into one of the following intents:
        - TRADE_HISTORY: Questions about past trades, completed trades, trade history
        - PERFORMANCE: Questions about ROI, profit/loss, best/worst pairs, overall performance
        - CURRENT_POSITIONS: Questions about currently open trades, active positions
        - MARKET_DATA: Questions about market conditions, prices, trends
        - STRATEGY_ANALYSIS: Questions about strategy performance, parameter analysis
        - OTHER: General questions not fitting the above categories
        
        Return a JSON object with the following properties:
        - intent: The classified intent
        - needs_live_data: Boolean indicating if query requires current/live data
        - time_range: Any time range mentioned in the query (e.g., "yesterday", "last week", "since January")
        - pairs: Any specific trading pairs mentioned (e.g., "BTC/USDT", "ETH/USDT")
        - metrics: Specific metrics mentioned (e.g., "profit", "ROI", "drawdown")
        """),
        ("user", query)
    ])
    
    llm = get_llm()
    chain = intent_prompt | llm | StrOutputParser()
    
    # Check cache first
    cache_key = f"intent:{query}"
    cached_result = await cache.get(cache_key)
    if cached_result:
        return json.loads(cached_result)
    
    # Process with LLM if not in cache
    result = await chain.ainvoke({"query": query})
    
    try:
        intent_data = json.loads(result)
        # Cache the result
        await cache.set(cache_key, result, expire=3600)  # 1 hour cache
        return intent_data
    except json.JSONDecodeError:
        logger.error(f"Failed to parse intent classification result: {result}")
        # Return default intent
        return {
            "intent": "OTHER",
            "needs_live_data": True,
            "time_range": None,
            "pairs": [],
            "metrics": []
        }

async def process_query(query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Process a natural language query using the orchestrator
    """
    # Step 1: Classify intent
    intent_data = await classify_intent(query)
    logger.info(f"Classified intent: {intent_data}")
    
    # Step 2: Get tools based on intent
    tools = get_available_tools()
    
    # Step 3: Prepare the prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("user", query)
    ])
    
    # Step 4: Create the chain with tools
    llm = get_llm()
    
    # Step 5: Execute the chain with tools
    if LLM_PROVIDER == "mock":
        # Special handling for mock provider
        mock_result = f"Mock response to: {query}\n\nThis is a demonstration response. In production, this would be generated by a real LLM with access to trading data."
        result = mock_result
    else:
        # Normal processing for real LLMs
        chain = prompt | llm.with_structured_output()
        result = await chain.ainvoke({
            "tools": tools,
            "context": context or {}
        })
    
    # Step 6: Post-process the result
    response = {
        "response": result,
        "context": {
            "intent": intent_data,
            "timestamp": datetime.now().isoformat(),
            "query": query
        }
    }
    
    # Check if we need to generate a chart
    if "chart" in result.lower():
        # Call the post-processor to generate a chart
        from user_data.trading_copilot.processors.chart_generator import generate_chart
        chart_data = extract_chart_data(result)
        if chart_data:
            chart_uri = await generate_chart(chart_data)
            response["chart_uri"] = chart_uri
    
    return response

async def process_streaming_query(query: str) -> AsyncGenerator[str, None]:
    """
    Process a query and stream the results back
    """
    # Classify intent
    intent_data = await classify_intent(query)
    
    # Get tools
    tools = get_available_tools()
    
    # Prepare the prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("user", query)
    ])
    
    # Create the chain with tools
    llm = get_llm()
    
    # Handle different providers
    if LLM_PROVIDER == "mock":
        # For mock provider, simulate streaming response
        mock_response = f"Mock response to: {query}\n\nThis is a demonstration response. In production, this would be generated by a real LLM with access to trading data."
        words = mock_response.split()
        for i in range(0, len(words), 3):
            chunk = " ".join(words[i:i+3])
            yield chunk
            await asyncio.sleep(0.1)  # Simulate streaming delay
    else:
        # For real LLMs, use the proper streaming interface
        chain = prompt | llm.with_structured_output()
        async for chunk in chain.astream({
            "tools": tools,
            "context": {"intent": intent_data}
        }):
            yield chunk

def extract_chart_data(result: str) -> Optional[Dict[str, Any]]:
    """
    Extract chart data from the result
    """
    # Implement logic to extract chart specification from the result
    # This is a placeholder - in a real implementation, you would parse the 
    # result to find chart specifications
    return None
