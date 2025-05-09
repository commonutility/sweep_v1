"""
Trade Tools for Trading-Copilot
Part of Layer 4 in the architecture - Tool Adapters
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import pandas as pd

# Freqtrade imports - to connect with the bot's database and API
from freqtrade.persistence.models import Trade
from freqtrade.persistence.pairlock import PairLock
from freqtrade.persistence import LocalTrade
from sqlalchemy import select, and_, or_, func, desc

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Trade retrieval tool
async def get_trades(
    pair: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    status: str = "all"
) -> Dict[str, Any]:
    """
    Get trade history filtered by pair, date range, and status
    """
    logger.info(f"Fetching trades: pair={pair}, from={from_date}, to={to_date}, status={status}")
    
    try:
        # Parse dates if provided
        from_datetime = datetime.strptime(from_date, "%Y-%m-%d") if from_date else None
        to_datetime = datetime.strptime(to_date, "%Y-%m-%d") if to_date else None
        
        # Build query filters
        filters = []
        if pair:
            filters.append(Trade.pair == pair)
        
        if from_datetime:
            filters.append(Trade.open_date >= from_datetime)
            
        if to_datetime:
            # Add one day to include the to_date
            to_datetime = to_datetime + timedelta(days=1)
            filters.append(Trade.open_date < to_datetime)
            
        # Status filter
        if status == "open":
            filters.append(Trade.is_open.is_(True))
        elif status == "closed":
            filters.append(Trade.is_open.is_(False))
        
        # Execute query
        trades_query = select(Trade)
        if filters:
            trades_query = trades_query.where(and_(*filters))
        
        # Order by open date, most recent first
        trades_query = trades_query.order_by(desc(Trade.open_date))
        
        # Execute through the LocalTrade proxy
        trades = LocalTrade.get_trades_query(trades_query).all()
        
        # Convert to dictionary for JSON serialization
        result = []
        for trade in trades:
            trade_dict = {
                "trade_id": trade.id,
                "pair": trade.pair,
                "open_date": trade.open_date.isoformat(),
                "close_date": trade.close_date.isoformat() if trade.close_date else None,
                "open_rate": float(trade.open_rate),
                "close_rate": float(trade.close_rate) if trade.close_rate else None,
                "stake_amount": float(trade.stake_amount),
                "amount": float(trade.amount),
                "fee_open": float(trade.fee_open) if trade.fee_open else 0,
                "fee_close": float(trade.fee_close) if trade.fee_close else 0,
                "profit_abs": float(trade.profit_abs) if trade.profit_abs else 0,
                "profit_ratio": float(trade.profit_ratio) if trade.profit_ratio else 0,
                "profit_pct": float(trade.profit_ratio) * 100 if trade.profit_ratio else 0,
                "enter_tag": trade.enter_tag,
                "exit_reason": trade.exit_reason,
                "strategy": trade.strategy,
                "duration": (trade.close_date - trade.open_date).total_seconds() / 3600 if trade.close_date else None,
                "is_open": trade.is_open,
            }
            result.append(trade_dict)
        
        # Provide summary statistics
        total_trades = len(result)
        total_profit = sum(t["profit_abs"] for t in result if not t["is_open"])
        win_trades = sum(1 for t in result if not t["is_open"] and t["profit_abs"] > 0)
        loss_trades = sum(1 for t in result if not t["is_open"] and t["profit_abs"] <= 0)
        
        # Return full result with metadata
        return {
            "trades": result,
            "summary": {
                "total_trades": total_trades,
                "profitable_trades": win_trades,
                "losing_trades": loss_trades,
                "win_rate": win_trades / (win_trades + loss_trades) if (win_trades + loss_trades) > 0 else 0,
                "total_profit": total_profit,
            },
            "query_details": {
                "pair": pair,
                "from_date": from_date,
                "to_date": to_date,
                "status": status
            }
        }
        
    except Exception as e:
        logger.error(f"Error fetching trades: {str(e)}", exc_info=True)
        return {
            "error": f"Failed to fetch trades: {str(e)}",
            "trades": [],
            "summary": {}
        }

# Performance metrics tool
async def get_performance(
    pair: Optional[str] = None,
    timeframe: str = "all",
    metrics: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Get performance metrics for the portfolio or specific pair
    """
    logger.info(f"Fetching performance metrics: pair={pair}, timeframe={timeframe}, metrics={metrics}")
    
    try:
        # Define time range based on timeframe
        end_date = datetime.now()
        start_date = None
        
        if timeframe == "1d":
            start_date = end_date - timedelta(days=1)
        elif timeframe == "7d":
            start_date = end_date - timedelta(days=7)
        elif timeframe == "30d":
            start_date = end_date - timedelta(days=30)
        elif timeframe == "90d":
            start_date = end_date - timedelta(days=90)
        elif timeframe == "ytd":  # Year to date
            start_date = datetime(end_date.year, 1, 1)
        elif timeframe == "all":
            start_date = None
        else:
            # Try to parse as custom timeframe
            try:
                days = int(timeframe.replace("d", ""))
                start_date = end_date - timedelta(days=days)
            except ValueError:
                return {"error": f"Invalid timeframe: {timeframe}"}
        
        # Build query filters
        filters = []
        if pair:
            filters.append(Trade.pair == pair)
        
        if start_date:
            filters.append(Trade.open_date >= start_date)
        
        # Query closed trades
        closed_filters = filters.copy()
        closed_filters.append(Trade.is_open.is_(False))
        
        closed_trades_query = select(Trade).where(and_(*closed_filters))
        closed_trades = LocalTrade.get_trades_query(closed_trades_query).all()
        
        # Query open trades
        open_filters = filters.copy()
        open_filters.append(Trade.is_open.is_(True))
        
        open_trades_query = select(Trade).where(and_(*open_filters))
        open_trades = LocalTrade.get_trades_query(open_trades_query).all()
        
        # Process metrics
        total_profit = sum(trade.profit_abs for trade in closed_trades)
        
        # Calculate profit percentage relative to investment
        total_invested = sum(trade.stake_amount for trade in closed_trades)
        profit_percentage = (total_profit / total_invested * 100) if total_invested > 0 else 0
        
        # Win rate
        win_trades = sum(1 for trade in closed_trades if trade.profit_abs > 0)
        loss_trades = sum(1 for trade in closed_trades if trade.profit_abs <= 0)
        win_rate = (win_trades / len(closed_trades) * 100) if closed_trades else 0
        
        # Average profit per trade
        avg_profit = total_profit / len(closed_trades) if closed_trades else 0
        
        # Average holding time
        avg_holding_time = None
        if closed_trades:
            holding_times = [(trade.close_date - trade.open_date).total_seconds() / 3600 for trade in closed_trades]
            avg_holding_time = sum(holding_times) / len(holding_times)
        
        # Compile performance by pair
        pair_performance = {}
        for trade in closed_trades:
            if trade.pair not in pair_performance:
                pair_performance[trade.pair] = {
                    "pair": trade.pair,
                    "profit_abs": 0,
                    "profit_pct": 0,
                    "trade_count": 0,
                    "win_count": 0,
                    "loss_count": 0,
                }
            
            pair_data = pair_performance[trade.pair]
            pair_data["profit_abs"] += trade.profit_abs
            pair_data["trade_count"] += 1
            
            if trade.profit_abs > 0:
                pair_data["win_count"] += 1
            else:
                pair_data["loss_count"] += 1
        
        # Calculate pair-specific metrics
        for pair_data in pair_performance.values():
            pair_data["win_rate"] = (pair_data["win_count"] / pair_data["trade_count"] * 100) if pair_data["trade_count"] > 0 else 0
            pair_data["avg_profit"] = pair_data["profit_abs"] / pair_data["trade_count"] if pair_data["trade_count"] > 0 else 0
        
        # Sort pairs by profit
        best_pairs = sorted(
            list(pair_performance.values()), 
            key=lambda x: x["profit_abs"], 
            reverse=True
        )[:5]
        
        worst_pairs = sorted(
            list(pair_performance.values()), 
            key=lambda x: x["profit_abs"]
        )[:5]
        
        # Open position statistics
        current_exposure = sum(trade.stake_amount for trade in open_trades)
        unrealized_profit = sum(trade.current_profit_abs for trade in open_trades if hasattr(trade, 'current_profit_abs'))
        
        # Prepare result
        result = {
            "timeframe": {
                "start": start_date.isoformat() if start_date else "all-time",
                "end": end_date.isoformat(),
            },
            "overall": {
                "total_closed_trades": len(closed_trades),
                "open_trades": len(open_trades),
                "total_profit": float(total_profit),
                "profit_percentage": float(profit_percentage),
                "win_rate": float(win_rate),
                "avg_profit_per_trade": float(avg_profit),
                "avg_holding_time_hours": float(avg_holding_time) if avg_holding_time else None,
            },
            "current": {
                "open_positions": len(open_trades),
                "current_exposure": float(current_exposure),
                "unrealized_profit": float(unrealized_profit) if unrealized_profit else 0,
            },
            "pairs": {
                "best_performing": best_pairs,
                "worst_performing": worst_pairs,
            }
        }
        
        # Filter metrics if specified
        if metrics:
            filtered_result = {"timeframe": result["timeframe"]}
            for category in ["overall", "current", "pairs"]:
                if category in metrics:
                    filtered_result[category] = result[category]
            result = filtered_result
        
        return result
        
    except Exception as e:
        logger.error(f"Error fetching performance metrics: {str(e)}", exc_info=True)
        return {
            "error": f"Failed to fetch performance metrics: {str(e)}",
        }

# Current positions tool
async def get_current_positions(
    pair: Optional[str] = None,
    min_profit: Optional[float] = None,
    max_age: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get currently open positions with optional filtering
    """
    logger.info(f"Fetching current positions: pair={pair}, min_profit={min_profit}, max_age={max_age}")
    
    try:
        # Build query filters
        filters = [Trade.is_open.is_(True)]
        
        if pair:
            filters.append(Trade.pair == pair)
        
        # Execute query
        trades_query = select(Trade).where(and_(*filters))
        
        # Get open trades
        open_trades = LocalTrade.get_trades_query(trades_query).all()
        
        # Post-filtering based on min_profit
        if min_profit is not None:
            open_trades = [
                trade for trade in open_trades 
                if hasattr(trade, 'current_profit_ratio') and 
                trade.current_profit_ratio * 100 >= min_profit
            ]
        
        # Post-filtering based on max_age
        if max_age:
            now = datetime.now()
            max_age_hours = 0
            
            # Parse max_age
            if max_age.endswith("h"):
                max_age_hours = int(max_age[:-1])
            elif max_age.endswith("d"):
                max_age_hours = int(max_age[:-1]) * 24
            
            if max_age_hours > 0:
                open_trades = [
                    trade for trade in open_trades 
                    if (now - trade.open_date).total_seconds() / 3600 <= max_age_hours
                ]
        
        # Convert to dictionary for JSON serialization
        result = []
        for trade in open_trades:
            current_rate = getattr(trade, 'current_rate', None)
            current_profit = getattr(trade, 'current_profit_ratio', None)
            
            trade_dict = {
                "trade_id": trade.id,
                "pair": trade.pair,
                "open_date": trade.open_date.isoformat(),
                "open_rate": float(trade.open_rate),
                "current_rate": float(current_rate) if current_rate else None,
                "stake_amount": float(trade.stake_amount),
                "amount": float(trade.amount),
                "fee_open": float(trade.fee_open) if trade.fee_open else 0,
                "current_profit_abs": float(trade.current_profit_abs) if hasattr(trade, 'current_profit_abs') else None,
                "current_profit_pct": float(current_profit) * 100 if current_profit else None,
                "enter_tag": trade.enter_tag,
                "strategy": trade.strategy,
                "duration_hours": (datetime.now() - trade.open_date).total_seconds() / 3600,
            }
            result.append(trade_dict)
        
        # Calculate summary statistics
        total_invested = sum(t["stake_amount"] for t in result)
        total_profit = sum(t["current_profit_abs"] for t in result if t["current_profit_abs"] is not None)
        
        # Return result with summary
        return {
            "positions": result,
            "summary": {
                "total_positions": len(result),
                "total_invested": float(total_invested),
                "unrealized_profit": float(total_profit),
                "profit_percentage": float(total_profit / total_invested * 100) if total_invested > 0 else 0,
            },
            "query_details": {
                "pair": pair,
                "min_profit": min_profit,
                "max_age": max_age
            }
        }
        
    except Exception as e:
        logger.error(f"Error fetching current positions: {str(e)}", exc_info=True)
        return {
            "error": f"Failed to fetch current positions: {str(e)}",
            "positions": [],
            "summary": {}
        }
