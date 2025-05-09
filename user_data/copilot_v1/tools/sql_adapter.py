"""
SQL Adapter for Trading-Copilot
Part of Layer 4 in the architecture - Tool Adapters
"""

import logging
import re
from typing import Dict, List, Any, Optional, Tuple, Union
import json
import pandas as pd
from sqlalchemy import text, create_engine, inspect
from sqlalchemy.exc import SQLAlchemyError

# Freqtrade imports
from freqtrade.persistence.models import Trade
from freqtrade.persistence import LocalTrade

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
ALLOWED_TABLES = ['trades', 'orders', 'pairlocks']
SENSITIVE_COLUMNS = ['api_key', 'secret', 'password', 'token']
MAX_ROWS = 1000
READ_ONLY_REGEX = re.compile(r'^SELECT\s+', re.IGNORECASE)

async def run_sql_query(
    query: str,
    parameters: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Run a SQL query against the trades database (read-only)
    """
    logger.info(f"Running SQL query: {query[:100]}...")
    
    try:
        # Validate that this is a SELECT query
        if not READ_ONLY_REGEX.match(query):
            return {
                "error": "Only SELECT queries are allowed for security reasons",
                "results": []
            }
        
        # Check for allowed tables
        for table in ALLOWED_TABLES:
            # Simple check for table names - in a real system you would use a proper SQL parser
            if f"FROM {table}" in query.upper() or f"JOIN {table}" in query.upper():
                break
        else:
            return {
                "error": f"Query must use at least one of the allowed tables: {', '.join(ALLOWED_TABLES)}",
                "results": []
            }
        
        # Get database connection from Freqtrade
        # This is a simplified approach - in production, you might want to create
        # a read-only user for these queries
        engine = LocalTrade.get_engine()
        
        # Execute the query
        with engine.connect() as conn:
            # Add LIMIT if not present
            if "LIMIT" not in query.upper():
                query = f"{query} LIMIT {MAX_ROWS}"
            
            # Execute with parameters
            params = parameters or {}
            result = conn.execute(text(query), params)
            
            # Convert to dictionary
            column_names = result.keys()
            rows = []
            for row in result:
                row_dict = dict(zip(column_names, row))
                
                # Sanitize sensitive columns
                for col in row_dict:
                    if any(sensitive in col.lower() for sensitive in SENSITIVE_COLUMNS):
                        row_dict[col] = "***REDACTED***"
                
                rows.append(row_dict)
            
            # Convert datetime objects to ISO format for JSON serialization
            for row in rows:
                for key, value in row.items():
                    if hasattr(value, 'isoformat'):
                        row[key] = value.isoformat()
            
            # Get basic metadata about the query
            metadata = {
                "row_count": len(rows),
                "column_count": len(column_names),
                "columns": list(column_names),
                "truncated": len(rows) >= MAX_ROWS
            }
            
            # Return result
            return {
                "results": rows,
                "metadata": metadata,
                "query": query
            }
    
    except SQLAlchemyError as e:
        logger.error(f"SQL error: {str(e)}", exc_info=True)
        return {
            "error": f"SQL error: {str(e)}",
            "results": []
        }
    except Exception as e:
        logger.error(f"Error executing SQL query: {str(e)}", exc_info=True)
        return {
            "error": f"Error executing SQL query: {str(e)}",
            "results": []
        }

async def get_database_schema() -> Dict[str, Any]:
    """
    Get the database schema for the trades database
    This is helpful for the LLM to understand the structure when writing queries
    """
    try:
        engine = LocalTrade.get_engine()
        inspector = inspect(engine)
        
        schema = {}
        for table_name in inspector.get_table_names():
            if table_name not in ALLOWED_TABLES:
                continue
                
            columns = []
            for column in inspector.get_columns(table_name):
                # Exclude sensitive columns from the schema
                if not any(sensitive in column['name'].lower() for sensitive in SENSITIVE_COLUMNS):
                    columns.append({
                        "name": column['name'],
                        "type": str(column['type']),
                        "nullable": column.get('nullable', True)
                    })
            
            # Get primary key
            pk = inspector.get_pk_constraint(table_name)
            
            # Get foreign keys
            fks = []
            for fk in inspector.get_foreign_keys(table_name):
                fks.append({
                    "constrained_columns": fk['constrained_columns'],
                    "referred_table": fk['referred_table'],
                    "referred_columns": fk['referred_columns']
                })
            
            # Add table to schema
            schema[table_name] = {
                "columns": columns,
                "primary_key": pk.get('constrained_columns', []),
                "foreign_keys": fks
            }
        
        return {
            "schema": schema,
            "allowed_tables": ALLOWED_TABLES
        }
        
    except Exception as e:
        logger.error(f"Error fetching database schema: {str(e)}", exc_info=True)
        return {
            "error": f"Error fetching database schema: {str(e)}",
            "schema": {}
        }

async def get_common_queries() -> Dict[str, str]:
    """
    Return a dictionary of common SQL queries that can be used with the database
    """
    return {
        "recent_trades": "SELECT * FROM trades ORDER BY open_date DESC LIMIT 10",
        "profitable_trades": "SELECT * FROM trades WHERE profit_abs > 0 AND close_date IS NOT NULL ORDER BY profit_abs DESC LIMIT 10",
        "losing_trades": "SELECT * FROM trades WHERE profit_abs < 0 AND close_date IS NOT NULL ORDER BY profit_abs ASC LIMIT 10",
        "open_trades": "SELECT * FROM trades WHERE is_open = 1",
        "trades_by_pair": "SELECT pair, COUNT(*) as trade_count, SUM(profit_abs) as total_profit FROM trades GROUP BY pair ORDER BY total_profit DESC",
        "daily_profit": "SELECT date(close_date) as date, SUM(profit_abs) as daily_profit FROM trades WHERE close_date IS NOT NULL GROUP BY date(close_date) ORDER BY date DESC",
        "strategy_performance": "SELECT strategy, COUNT(*) as trade_count, SUM(profit_abs) as total_profit, AVG(profit_ratio) * 100 as avg_profit_pct FROM trades WHERE close_date IS NOT NULL GROUP BY strategy ORDER BY total_profit DESC",
    }
