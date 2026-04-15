"""
Minimal usage example. Runs a single analysis using FINNISH_CONFIG.
See cli/ for the interactive CLI, telegram_bot/ for the Telegram bot.
"""
from dotenv import load_dotenv
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.finnish_config import get_finnish_config

load_dotenv()

config = get_finnish_config()
ta = TradingAgentsGraph(debug=True, config=config)
_, decision = ta.propagate("NOKIA", "2026-03-24")
print(decision)
