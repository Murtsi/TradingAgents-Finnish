from langchain_core.messages import HumanMessage, RemoveMessage

# Import tools from separate utility files
from tradingagents.agents.utils.core_stock_tools import (
    get_stock_data
)
from tradingagents.agents.utils.technical_indicators_tools import (
    get_indicators
)
from tradingagents.agents.utils.fundamental_data_tools import (
    get_fundamentals,
    get_balance_sheet,
    get_cashflow,
    get_income_statement
)
from tradingagents.agents.utils.news_data_tools import (
    get_news,
    get_insider_transactions,
    get_global_news,
    get_all_stock_news_combined,
    get_finnish_news,
)
from tradingagents.dataflows.omxh_utils import resolve_company_name


def build_instrument_context(ticker: str) -> str:
    """
    Describe the exact instrument so agents preserve exchange-qualified tickers.
    Includes resolved company name to prevent misidentification (e.g. FIA1S.HE → Finnair Oyj,
    not Finavia or Embraer).
    """
    try:
        company_name = resolve_company_name(ticker)
    except Exception:
        company_name = ticker

    return (
        f"The instrument to analyze is `{ticker}` ({company_name}). "
        f"The company name is '{company_name}'. "
        "Use this exact ticker in every tool call, report, and recommendation, "
        "preserving any exchange suffix (e.g. `.HE`, `.TO`, `.L`). "
        f"IMPORTANT: Only use data and news that refers to '{company_name}' — "
        "discard any results about other companies even if the ticker search returns them."
    )

def create_msg_delete():
    def delete_messages(state):
        """Clear messages and add placeholder for Anthropic compatibility"""
        messages = state["messages"]

        # Remove all messages
        removal_operations = [RemoveMessage(id=m.id) for m in messages]

        # Add a minimal placeholder message
        placeholder = HumanMessage(content="Continue")

        return {"messages": removal_operations + [placeholder]}

    return delete_messages


        
