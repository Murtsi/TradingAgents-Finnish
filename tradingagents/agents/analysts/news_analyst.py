from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import time
import json
from tradingagents.agents.utils.agent_utils import build_instrument_context
from tradingagents.agents.utils.news_data_tools import (
    get_all_stock_news_combined,
    get_news,
    get_global_news,
    get_finnish_news,
)
from tradingagents.agents.utils.prompt_loader import load_fi_prompt  # FORK: Suomi-lokalisointi
from tradingagents.dataflows.config import get_config


def create_news_analyst(llm):
    def news_analyst_node(state):
        current_date = state["trade_date"]
        instrument_context = build_instrument_context(state["company_of_interest"])

        # get_all_stock_news_combined fetches Yahoo Finance + Kauppalehti/YLE RSS +
        # ECB/Nordic macro in ONE tool call instead of three separate calls.
        # The individual tools remain as fallback if the LLM chooses to dig deeper.
        tools = [
            get_all_stock_news_combined,
            get_news,
            get_global_news,
            get_finnish_news,
        ]

        # FORK: Suomi-lokalisointi — Finnish system prompt + tool calling instructions
        system_message = (
            "KRIITTINEN OHJE: Kirjoita KAIKKI analyysit ja raportit AINA suomeksi. "
            "Älä koskaan kirjoita englanniksi. Älä kysy tarkentavia kysymyksiä. "
            "Aloita analyysi välittömästi ilman johdantolauseita.\n\n"
            + load_fi_prompt("news_system")
            + "\n\nALWAYS start by calling get_all_stock_news_combined(ticker, trade_date) — "
            "it fetches Yahoo Finance news, Finnish RSS sources (Kauppalehti, YLE Talous), "
            "and ECB/Nordic macro context in a single call. "
            "Only use the individual tools (get_news, get_global_news, get_finnish_news) "
            "if you need additional targeted searches after the combined call.\n\n"
            "TICKER VALIDATION: Before using any news results, verify that the company name "
            "in the results matches the expected company for the ticker. For example, FIA1S.HE "
            "is Finnair — if results mention a different company (e.g. Embraer), explicitly note "
            "the mismatch in your report and do not use those results as evidence for this company."
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a helpful AI assistant, collaborating with other assistants."
                    " Use the provided tools to progress towards answering the question."
                    " If you are unable to fully answer, that's OK; another assistant with different tools"
                    " will help where you left off. Execute what you can to make progress."
                    " If you or any other assistant has the FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** or deliverable,"
                    " prefix your response with FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** so the team knows to stop."
                    " You have access to the following tools: {tool_names}.\n{system_message}"
                    "For your reference, the current date is {current_date}. {instrument_context}",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))
        prompt = prompt.partial(current_date=current_date)
        prompt = prompt.partial(instrument_context=instrument_context)

        chain = prompt | llm.bind_tools(tools)
        result = chain.invoke(state["messages"])

        report = ""

        if len(result.tool_calls) == 0:
            report = result.content

        return {
            "messages": [result],
            "news_report": report,
        }

    return news_analyst_node
