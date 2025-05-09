"""
Chart Generator for Trading-Copilot
Layer 6 in the architecture - Post-Processor
"""

import logging
import json
import asyncio
import os
import io
import base64
import re
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter
import seaborn as sns

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure style
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_context("talk")

# Constants
CHART_DIR = os.path.join("user_data", "trading_copilot", "charts")
DEFAULT_CHART_SIZE = (12, 8)
DEFAULT_DPI = 100

# Create charts directory if it doesn't exist
os.makedirs(CHART_DIR, exist_ok=True)

async def generate_chart(chart_data: Dict[str, Any]) -> str:
    """
    Generate a chart based on the chart data
    Returns a data URI or a path to the saved chart
    """
    chart_type = chart_data.get("type", "line")
    
    try:
        if chart_type == "line":
            return await generate_line_chart(chart_data)
        elif chart_type == "bar":
            return await generate_bar_chart(chart_data)
        elif chart_type == "scatter":
            return await generate_scatter_chart(chart_data)
        elif chart_type == "pie":
            return await generate_pie_chart(chart_data)
        elif chart_type == "candlestick":
            return await generate_candlestick_chart(chart_data)
        else:
            logger.warning(f"Unsupported chart type: {chart_type}")
            return ""
    except Exception as e:
        logger.error(f"Error generating chart: {str(e)}", exc_info=True)
        return ""

async def generate_line_chart(chart_data: Dict[str, Any]) -> str:
    """
    Generate a line chart from the provided data
    """
    title = chart_data.get("title", "Line Chart")
    data = chart_data.get("data", [])
    x_label = chart_data.get("x_label", "")
    y_label = chart_data.get("y_label", "")
    x_column = chart_data.get("x_column", "x")
    y_columns = chart_data.get("y_columns", ["y"])
    
    if not data:
        logger.warning("No data provided for line chart")
        return ""
    
    # Create DataFrame from data
    df = pd.DataFrame(data)
    
    # Create figure
    plt.figure(figsize=DEFAULT_CHART_SIZE)
    
    # Set style
    plt.title(title, fontsize=16)
    plt.xlabel(x_label, fontsize=12)
    plt.ylabel(y_label, fontsize=12)
    plt.grid(True, alpha=0.3)
    
    # Plot each y column
    for column in y_columns:
        if column in df.columns:
            plt.plot(df[x_column], df[column], label=column, linewidth=2, marker='o', markersize=4)
    
    # Add legend if multiple columns
    if len(y_columns) > 1:
        plt.legend()
    
    # Format axes based on data type
    if pd.api.types.is_datetime64_any_dtype(df[x_column]):
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.gcf().autofmt_xdate()
    
    # Adjust layout
    plt.tight_layout()
    
    # Save chart to memory
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=DEFAULT_DPI)
    plt.close()
    
    # Convert to data URI
    buffer.seek(0)
    chart_uri = f"data:image/png;base64,{base64.b64encode(buffer.read()).decode('utf-8')}"
    
    return chart_uri

async def generate_bar_chart(chart_data: Dict[str, Any]) -> str:
    """
    Generate a bar chart from the provided data
    """
    title = chart_data.get("title", "Bar Chart")
    data = chart_data.get("data", [])
    x_label = chart_data.get("x_label", "")
    y_label = chart_data.get("y_label", "")
    x_column = chart_data.get("x_column", "x")
    y_column = chart_data.get("y_column", "y")
    color_column = chart_data.get("color_column")
    
    if not data:
        logger.warning("No data provided for bar chart")
        return ""
    
    # Create DataFrame from data
    df = pd.DataFrame(data)
    
    # Create figure
    plt.figure(figsize=DEFAULT_CHART_SIZE)
    
    # Set style
    plt.title(title, fontsize=16)
    plt.xlabel(x_label, fontsize=12)
    plt.ylabel(y_label, fontsize=12)
    plt.grid(True, alpha=0.3, axis='y')
    
    # Plot bar chart
    if color_column and color_column in df.columns:
        # Use color column for coloring
        bar_colors = plt.cm.viridis(np.linspace(0, 1, len(df)))
        bars = plt.bar(df[x_column], df[y_column], color=bar_colors)
        
        # Add colorbar
        sm = plt.cm.ScalarMappable(cmap=plt.cm.viridis)
        sm.set_array(df[color_column])
        plt.colorbar(sm, label=color_column)
    else:
        # Use default coloring
        bars = plt.bar(df[x_column], df[y_column])
    
    # Add value labels on top of bars
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.2f}',
                ha='center', va='bottom')
    
    # Adjust layout
    plt.tight_layout()
    
    # Save chart to memory
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=DEFAULT_DPI)
    plt.close()
    
    # Convert to data URI
    buffer.seek(0)
    chart_uri = f"data:image/png;base64,{base64.b64encode(buffer.read()).decode('utf-8')}"
    
    return chart_uri

async def generate_scatter_chart(chart_data: Dict[str, Any]) -> str:
    """
    Generate a scatter chart from the provided data
    """
    title = chart_data.get("title", "Scatter Chart")
    data = chart_data.get("data", [])
    x_label = chart_data.get("x_label", "")
    y_label = chart_data.get("y_label", "")
    x_column = chart_data.get("x_column", "x")
    y_column = chart_data.get("y_column", "y")
    color_column = chart_data.get("color_column")
    size_column = chart_data.get("size_column")
    
    if not data:
        logger.warning("No data provided for scatter chart")
        return ""
    
    # Create DataFrame from data
    df = pd.DataFrame(data)
    
    # Create figure
    plt.figure(figsize=DEFAULT_CHART_SIZE)
    
    # Set style
    plt.title(title, fontsize=16)
    plt.xlabel(x_label, fontsize=12)
    plt.ylabel(y_label, fontsize=12)
    plt.grid(True, alpha=0.3)
    
    # Plot scatter chart
    scatter_kwargs = {}
    
    if size_column and size_column in df.columns:
        scatter_kwargs['s'] = df[size_column] * 50  # Scale for better visibility
    
    if color_column and color_column in df.columns:
        # Use color column for coloring
        scatter = plt.scatter(df[x_column], df[y_column], c=df[color_column], 
                             cmap='viridis', alpha=0.7, **scatter_kwargs)
        plt.colorbar(label=color_column)
    else:
        # Use default coloring
        scatter = plt.scatter(df[x_column], df[y_column], alpha=0.7, **scatter_kwargs)
    
    # Adjust layout
    plt.tight_layout()
    
    # Save chart to memory
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=DEFAULT_DPI)
    plt.close()
    
    # Convert to data URI
    buffer.seek(0)
    chart_uri = f"data:image/png;base64,{base64.b64encode(buffer.read()).decode('utf-8')}"
    
    return chart_uri

async def generate_pie_chart(chart_data: Dict[str, Any]) -> str:
    """
    Generate a pie chart from the provided data
    """
    title = chart_data.get("title", "Pie Chart")
    data = chart_data.get("data", [])
    label_column = chart_data.get("label_column", "label")
    value_column = chart_data.get("value_column", "value")
    
    if not data:
        logger.warning("No data provided for pie chart")
        return ""
    
    # Create DataFrame from data
    df = pd.DataFrame(data)
    
    # Create figure
    plt.figure(figsize=DEFAULT_CHART_SIZE)
    
    # Set style
    plt.title(title, fontsize=16)
    
    # Plot pie chart
    plt.pie(df[value_column], labels=df[label_column], autopct='%1.1f%%', 
            startangle=90, shadow=False, wedgeprops={'edgecolor': 'w', 'linewidth': 1})
    
    # Equal aspect ratio ensures that pie is drawn as a circle
    plt.axis('equal')
    
    # Adjust layout
    plt.tight_layout()
    
    # Save chart to memory
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=DEFAULT_DPI)
    plt.close()
    
    # Convert to data URI
    buffer.seek(0)
    chart_uri = f"data:image/png;base64,{base64.b64encode(buffer.read()).decode('utf-8')}"
    
    return chart_uri

async def generate_candlestick_chart(chart_data: Dict[str, Any]) -> str:
    """
    Generate a candlestick chart from the provided data
    """
    title = chart_data.get("title", "Candlestick Chart")
    data = chart_data.get("data", [])
    date_column = chart_data.get("date_column", "date")
    open_column = chart_data.get("open_column", "open")
    high_column = chart_data.get("high_column", "high")
    low_column = chart_data.get("low_column", "low")
    close_column = chart_data.get("close_column", "close")
    volume_column = chart_data.get("volume_column")
    
    if not data:
        logger.warning("No data provided for candlestick chart")
        return ""
    
    # Create DataFrame from data
    df = pd.DataFrame(data)
    
    # Sort by date
    if date_column in df.columns:
        df = df.sort_values(by=date_column)
    
    # Create figure with two subplots if volume is included
    if volume_column and volume_column in df.columns:
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=DEFAULT_CHART_SIZE, 
                                      gridspec_kw={'height_ratios': [3, 1]}, sharex=True)
    else:
        fig, ax1 = plt.subplots(figsize=DEFAULT_CHART_SIZE)
    
    # Set title
    fig.suptitle(title, fontsize=16)
    
    # Plot candlesticks
    width = 0.6
    width2 = 0.1
    
    up = df[close_column] > df[open_column]
    down = df[close_column] <= df[open_column]
    
    # Plot up candles
    ax1.bar(df.index[up], df[high_column][up] - df[low_column][up], width=width2, 
           bottom=df[low_column][up], color='g', alpha=0.5)
    ax1.bar(df.index[up], df[close_column][up] - df[open_column][up], width=width, 
           bottom=df[open_column][up], color='g')
    
    # Plot down candles
    ax1.bar(df.index[down], df[high_column][down] - df[low_column][down], width=width2, 
           bottom=df[low_column][down], color='r', alpha=0.5)
    ax1.bar(df.index[down], df[open_column][down] - df[close_column][down], width=width, 
           bottom=df[close_column][down], color='r')
    
    # Set x-axis labels
    if date_column in df.columns:
        x_labels = df[date_column]
        ax1.set_xticks(range(len(x_labels)))
        
        # Only show a subset of labels to avoid overcrowding
        step = max(1, len(x_labels) // 10)
        ax1.set_xticklabels(x_labels[::step], rotation=45)
    
    # Add grid
    ax1.grid(True, alpha=0.3)
    
    # Add volume subplot if requested
    if volume_column and volume_column in df.columns:
        # Plot volume bars
        ax2.bar(df.index[up], df[volume_column][up], color='g', alpha=0.5, width=width)
        ax2.bar(df.index[down], df[volume_column][down], color='r', alpha=0.5, width=width)
        
        # Set labels and grid
        ax2.set_ylabel('Volume')
        ax2.grid(True, alpha=0.3)
    
    # Adjust layout
    plt.tight_layout()
    
    # Save chart to memory
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=DEFAULT_DPI)
    plt.close()
    
    # Convert to data URI
    buffer.seek(0)
    chart_uri = f"data:image/png;base64,{base64.b64encode(buffer.read()).decode('utf-8')}"
    
    return chart_uri

# Helper functions

def extract_chart_spec_from_text(text: str) -> Optional[Dict[str, Any]]:
    """
    Extract chart specification from LLM-generated text
    """
    # Look for JSON blocks that might contain chart specifications
    json_pattern = r'```json\s*(.*?)\s*```'
    matches = re.findall(json_pattern, text, re.DOTALL)
    
    for match in matches:
        try:
            data = json.loads(match)
            if "chart" in data or "type" in data:
                return data
        except json.JSONDecodeError:
            continue
    
    # Fallback to more aggressive pattern matching if no valid JSON blocks
    chart_section_pattern = r'(?:Chart|Graph|Visualization)[\s\S]*?{([\s\S]*?)}'
    matches = re.findall(chart_section_pattern, text)
    
    for match in matches:
        try:
            # Try to fix and parse the possible JSON fragment
            fixed_json = "{" + match.replace("'", "\"") + "}"
            data = json.loads(fixed_json)
            return data
        except json.JSONDecodeError:
            continue
    
    return None

def generate_profit_chart(trades_data: List[Dict[str, Any]]) -> str:
    """
    Generate a profit chart from trades data
    """
    if not trades_data:
        return ""
    
    # Convert to DataFrame
    df = pd.DataFrame(trades_data)
    
    # Convert dates to datetime
    for date_col in ['open_date', 'close_date']:
        if date_col in df.columns:
            df[date_col] = pd.to_datetime(df[date_col])
    
    # Calculate cumulative profit
    df = df.sort_values('close_date')
    df['cumulative_profit'] = df['profit_abs'].cumsum()
    
    # Create chart data
    chart_data = {
        "type": "line",
        "title": "Cumulative Profit Over Time",
        "data": df[['close_date', 'cumulative_profit']].to_dict('records'),
        "x_column": "close_date",
        "y_columns": ["cumulative_profit"],
        "x_label": "Date",
        "y_label": "Cumulative Profit"
    }
    
    return asyncio.run(generate_line_chart(chart_data))

def generate_pair_performance_chart(performance_data: List[Dict[str, Any]]) -> str:
    """
    Generate a bar chart showing performance by pair
    """
    if not performance_data:
        return ""
    
    # Convert to DataFrame
    df = pd.DataFrame(performance_data)
    
    # Sort by profit
    df = df.sort_values('profit_abs', ascending=False)
    
    # Create chart data
    chart_data = {
        "type": "bar",
        "title": "Profit by Trading Pair",
        "data": df[['pair', 'profit_abs']].to_dict('records'),
        "x_column": "pair",
        "y_column": "profit_abs",
        "x_label": "Trading Pair",
        "y_label": "Profit"
    }
    
    return asyncio.run(generate_bar_chart(chart_data))
