from langchain_core.tools import tool
from typing import Annotated
from tradingagents.dataflows.interface import route_to_vendor
from tradingagents.dataflows.finnish_news import get_finnish_market_news, get_all_stock_news

@tool
def get_news(
    ticker: Annotated[str, "Ticker symbol"],
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
) -> str:
    """
    Retrieve news data for a given ticker symbol.
    Uses the configured news_data vendor.
    Args:
        ticker (str): Ticker symbol
        start_date (str): Start date in yyyy-mm-dd format
        end_date (str): End date in yyyy-mm-dd format
    Returns:
        str: A formatted string containing news data
    """
    return route_to_vendor("get_news", ticker, start_date, end_date)

@tool
def get_global_news(
    curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    look_back_days: Annotated[int, "Number of days to look back"] = 7,
    limit: Annotated[int, "Maximum number of articles to return"] = 5,
) -> str:
    """
    Retrieve global news data.
    Uses the configured news_data vendor.
    Args:
        curr_date (str): Current date in yyyy-mm-dd format
        look_back_days (int): Number of days to look back (default 7)
        limit (int): Maximum number of articles to return (default 5)
    Returns:
        str: A formatted string containing global news data
    """
    return route_to_vendor("get_global_news", curr_date, look_back_days, limit)

@tool
def get_finnish_news(
    ticker: Annotated[str, "Ticker symbol, e.g. NOKIA.HE or NOKIA"],
    company_name: Annotated[str, "Company name in Finnish/English for keyword search, e.g. Nokia"] = "",
    lookback_days: Annotated[int, "Number of days to look back (default 7)"] = 7,
) -> str:
    """
    Retrieve Finnish-language financial news from Kauppalehti and YLE Talous RSS feeds.
    Use this tool to get Finnish market news, ECB decisions, and OMXH-specific coverage
    that international sources may miss. Especially useful for Finnish stocks.
    Args:
        ticker (str): Ticker symbol
        company_name (str): Company name for better keyword matching
        lookback_days (int): Days to look back
    Returns:
        str: Finnish news articles formatted as text
    """
    return get_finnish_market_news(ticker, company_name, lookback_days)

@tool
def get_all_stock_news_combined(
    ticker: Annotated[str, "Yahoo Finance ticker, e.g. NOKIA.HE"],
    trade_date: Annotated[str, "Analysis date in yyyy-mm-dd format"],
    lookback_days: Annotated[int, "Days of news history to fetch (default 7)"] = 7,
) -> str:
    """
    PREFERRED tool for news analysis. Fetches ALL news sources in a single call:
    (1) Yahoo Finance company-specific news,
    (2) Finnish RSS sources: Kauppalehti + YLE Talous (Finnish-language coverage),
    (3) ECB/Nordic macroeconomic context from Yahoo Finance Search.
    Use this instead of calling get_news, get_global_news, and get_finnish_news separately.
    Returns combined formatted text from all three sources.
    """
    return get_all_stock_news(ticker, trade_date, lookback_days)

@tool
def get_insider_transactions(
    ticker: Annotated[str, "ticker symbol"],
) -> str:
    """
    Retrieve insider transaction information about a company.
    Uses the configured news_data vendor.
    Args:
        ticker (str): Ticker symbol of the company
    Returns:
        str: A report of insider transaction data
    """
    return route_to_vendor("get_insider_transactions", ticker)
