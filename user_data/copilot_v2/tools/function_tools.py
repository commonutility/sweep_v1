"""
Function Tools for Freqtrade API - Copilot V2
Defines the function tools for OpenAI tool calling
"""

from typing import Dict, List, Any, Optional

# Define the tools for OpenAI function calling
# These tools will be passed to the OpenAI API for tool calling

FREQTRADE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "available_pairs",
            "description": "Return available pair (backtest data) based on timeframe / stake_currency selection",
            "parameters": {
                "type": "object",
                "properties": {
                    "timeframe": {
                        "type": "string",
                        "description": "Only pairs with this timeframe available"
                    },
                    "stake_currency": {
                        "type": "string",
                        "description": "Only pairs that include this stake currency"
                    }
                },
                "required": ["timeframe", "stake_currency"],
                "additionalProperties": False
            },
            "strict": True
        }
    },
    {
        "type": "function",
        "function": {
            "name": "balance",
            "description": "Get the account balance.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False
            },
            "strict": True
        }
    },
    {
        "type": "function",
        "function": {
            "name": "blacklist",
            "description": "Show the current blacklist or add coins to blacklist.",
            "parameters": {
                "type": "object",
                "properties": {
                    "add": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "description": "List of coins to add (example: 'BNB/BTC')"
                    }
                },
                "required": ["add"],
                "additionalProperties": False
            },
            "strict": True
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_open_order",
            "description": "Cancel open order for trade.",
            "parameters": {
                "type": "object",
                "properties": {
                    "trade_id": {
                        "type": "integer",
                        "description": "Cancels open orders for this trade"
                    }
                },
                "required": ["trade_id"],
                "additionalProperties": False
            },
            "strict": True
        }
    },
    {
        "type": "function",
        "function": {
            "name": "count",
            "description": "Return the amount of open trades.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False
            },
            "strict": True
        }
    },
    {
        "type": "function",
        "function": {
            "name": "daily",
            "description": "Return the profits for each day, and amount of trades.",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False
            },
            "strict": True
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_lock",
            "description": "Delete (disable) lock from the database.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lock_id": {
                        "type": "integer",
                        "description": "ID for the lock to delete"
                    }
                },
                "required": ["lock_id"],
                "additionalProperties": False
            },
            "strict": True
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_trade",
            "description": "Delete trade from the database. Tries to close open orders. Requires manual handling of this asset on the exchange.",
            "parameters": {
                "type": "object",
                "properties": {
                    "trade_id": {
                        "type": "integer",
                        "description": "Deletes the trade with this ID from the database"
                    }
                },
                "required": ["trade_id"],
                "additionalProperties": False
            },
            "strict": True
        }
    },
    {
        "type": "function",
        "function": {
            "name": "edge",
            "description": "Return information about edge.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False
            },
            "strict": True
        }
    },
    {
        "type": "function",
        "function": {
            "name": "forcebuy",
            "description": "Buy an asset.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pair": {
                        "type": "string",
                        "description": "Pair to buy (e.g., ETH/BTC)"
                    },
                    "price": {
                        "type": "number",
                        "description": "Optional - price to buy"
                    }
                },
                "required": ["pair", "price"],
                "additionalProperties": False
            },
            "strict": True
        }
    },
    {
        "type": "function",
        "function": {
            "name": "forceenter",
            "description": "Force entering a trade",
            "parameters": {
                "type": "object",
                "properties": {
                    "pair": {
                        "type": "string",
                        "description": "Pair to buy (e.g., ETH/BTC)"
                    },
                    "side": {
                        "type": "string",
                        "description": "'long' or 'short'",
                        "enum": ["long", "short"]
                    },
                    "price": {
                        "type": "number",
                        "description": "Optional - price to buy"
                    }
                },
                "required": ["pair", "side", "price"],
                "additionalProperties": False
            },
            "strict": True
        }
    },
    {
        "type": "function",
        "function": {
            "name": "forceexit",
            "description": "Force-exit a trade.",
            "parameters": {
                "type": "object",
                "properties": {
                    "trade_id": {
                        "type": "integer",
                        "description": "Id of the trade (can be received via status command)"
                    },
                    "ordertype": {
                        "type": "string",
                        "description": "Order type to use (must be market or limit)",
                        "enum": ["market", "limit"]
                    },
                    "amount": {
                        "type": "number",
                        "description": "Amount to sell. Full sell if not given"
                    }
                },
                "required": ["trade_id", "ordertype", "amount"],
                "additionalProperties": False
            },
            "strict": True
        }
    },
    {
        "type": "function",
        "function": {
            "name": "health",
            "description": "Provides a quick health check of the running bot.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False
            },
            "strict": True
        }
    },
    {
        "type": "function",
        "function": {
            "name": "lock_add",
            "description": "Manually lock a specific pair",
            "parameters": {
                "type": "object",
                "properties": {
                    "pair": {
                        "type": "string",
                        "description": "Pair to lock"
                    },
                    "until": {
                        "type": "string",
                        "description": "Lock until this date (format '2024-03-30 16:00:00Z')"
                    },
                    "side": {
                        "type": "string",
                        "description": "Side to lock (long, short, *)",
                        "enum": ["long", "short", "*"]
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for the lock"
                    }
                },
                "required": ["pair", "until", "side", "reason"],
                "additionalProperties": False
            },
            "strict": True
        }
    },
    {
        "type": "function",
        "function": {
            "name": "locks",
            "description": "Return current locks",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False
            },
            "strict": True
        }
    },
    {
        "type": "function",
        "function": {
            "name": "logs",
            "description": "Show latest logs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Limits log messages to the last <limit> logs. No limit to get the entire log."
                    }
                },
                "required": ["limit"],
                "additionalProperties": False
            },
            "strict": True
        }
    },
    {
        "type": "function",
        "function": {
            "name": "pair_candles",
            "description": "Return live dataframe for <pair><timeframe>.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pair": {
                        "type": "string",
                        "description": "Pair to get data for"
                    },
                    "timeframe": {
                        "type": "string",
                        "description": "Only pairs with this timeframe available"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Limit result to the last n candles"
                    }
                },
                "required": ["pair", "timeframe", "limit"],
                "additionalProperties": False
            },
            "strict": True
        }
    },
    {
        "type": "function",
        "function": {
            "name": "pair_history",
            "description": "Return historic, analyzed dataframe",
            "parameters": {
                "type": "object",
                "properties": {
                    "pair": {
                        "type": "string",
                        "description": "Pair to get data for"
                    },
                    "timeframe": {
                        "type": "string",
                        "description": "Only pairs with this timeframe available"
                    },
                    "strategy": {
                        "type": "string",
                        "description": "Strategy to analyze and get values for"
                    },
                    "timerange": {
                        "type": "string",
                        "description": "Timerange to get data for (same format than --timerange endpoints)"
                    }
                },
                "required": ["pair", "timeframe", "strategy", "timerange"],
                "additionalProperties": False
            },
            "strict": True
        }
    },
    {
        "type": "function",
        "function": {
            "name": "performance",
            "description": "Return the performance of the different coins.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False
            },
            "strict": True
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ping",
            "description": "Simple ping",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False
            },
            "strict": True
        }
    },
    {
        "type": "function",
        "function": {
            "name": "plot_config",
            "description": "Return plot configuration if the strategy defines one.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False
            },
            "strict": True
        }
    },
    {
        "type": "function",
        "function": {
            "name": "profit",
            "description": "Return the profit summary.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False
            },
            "strict": True
        }
    },
    {
        "type": "function",
        "function": {
            "name": "reload_config",
            "description": "Reload configuration.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False
            },
            "strict": True
        }
    },
    {
        "type": "function",
        "function": {
            "name": "show_config",
            "description": "Returns part of the configuration, relevant for trading operations.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False
            },
            "strict": True
        }
    },
    {
        "type": "function",
        "function": {
            "name": "start",
            "description": "Start the bot if it's in the stopped state.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False
            },
            "strict": True
        }
    },
    {
        "type": "function",
        "function": {
            "name": "pause",
            "description": "Pause the bot if it's in the running state. If triggered on stopped state will handle open positions.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False
            },
            "strict": True
        }
    },
    {
        "type": "function",
        "function": {
            "name": "stats",
            "description": "Return the stats report (durations, sell-reasons).",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False
            },
            "strict": True
        }
    },
    {
        "type": "function",
        "function": {
            "name": "status",
            "description": "Get the status of open trades.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False
            },
            "strict": True
        }
    },
    {
        "type": "function",
        "function": {
            "name": "stop",
            "description": "Stop the bot. Use `start` to restart.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False
            },
            "strict": True
        }
    },
    {
        "type": "function",
        "function": {
            "name": "stopbuy",
            "description": "Stop buying (but handle sells gracefully). Use `reload_config` to reset.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False
            },
            "strict": True
        }
    },
    {
        "type": "function",
        "function": {
            "name": "strategies",
            "description": "Lists available strategies",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False
            },
            "strict": True
        }
    },
    {
        "type": "function",
        "function": {
            "name": "strategy",
            "description": "Get strategy details",
            "parameters": {
                "type": "object",
                "properties": {
                    "strategy": {
                        "type": "string",
                        "description": "Strategy class name"
                    }
                },
                "required": ["strategy"],
                "additionalProperties": False
            },
            "strict": True
        }
    },
    {
        "type": "function",
        "function": {
            "name": "sysinfo",
            "description": "Provides system information (CPU, RAM usage)",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False
            },
            "strict": True
        }
    },
    {
        "type": "function",
        "function": {
            "name": "trade",
            "description": "Return specific trade",
            "parameters": {
                "type": "object",
                "properties": {
                    "trade_id": {
                        "type": "integer",
                        "description": "Specify which trade to get"
                    }
                },
                "required": ["trade_id"],
                "additionalProperties": False
            },
            "strict": True
        }
    },
    {
        "type": "function",
        "function": {
            "name": "trades",
            "description": "Return trades history, sorted by id",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Limits trades to the X last trades. Max 500 trades."
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Offset by this amount of trades."
                    }
                },
                "required": ["limit", "offset"],
                "additionalProperties": False
            },
            "strict": True
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_open_trades_custom_data",
            "description": "Return a dict containing open trades custom-datas",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "Key of the custom-data"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Limits trades to X trades."
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Offset by this amount of trades."
                    }
                },
                "required": ["key", "limit", "offset"],
                "additionalProperties": False
            },
            "strict": True
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_custom_data",
            "description": "Return a dict containing custom-datas of a specified trade",
            "parameters": {
                "type": "object",
                "properties": {
                    "trade_id": {
                        "type": "integer",
                        "description": "ID of the trade"
                    },
                    "key": {
                        "type": "string",
                        "description": "Key of the custom-data"
                    }
                },
                "required": ["trade_id", "key"],
                "additionalProperties": False
            },
            "strict": True
        }
    },
    {
        "type": "function",
        "function": {
            "name": "version",
            "description": "Return the version of the bot.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False
            },
            "strict": True
        }
    },
    {
        "type": "function",
        "function": {
            "name": "whitelist",
            "description": "Show the current whitelist.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False
            },
            "strict": True
        }
    }
]
