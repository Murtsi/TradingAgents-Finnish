from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import time
import json
from tradingagents.agents.utils.agent_utils import (
    build_instrument_context,
    get_balance_sheet,
    get_cashflow,
    get_fundamentals,
    get_income_statement,
    get_insider_transactions,
)
from tradingagents.agents.utils.prompt_loader import load_fi_prompt  # FORK: Suomi-lokalisointi
from tradingagents.dataflows.config import get_config


def create_fundamentals_analyst(llm):
    def fundamentals_analyst_node(state):
        current_date = state["trade_date"]
        instrument_context = build_instrument_context(state["company_of_interest"])

        tools = [
            get_fundamentals,
            get_balance_sheet,
            get_cashflow,
            get_income_statement,
            get_insider_transactions,  # FORK: Vaihe 2.75 — sisäpiiri-ilmoitukset
        ]

        # FORK: Suomi-lokalisointi — ladataan Finnish system prompt fi_prompts/-kansiosta
        # FORK: sanarajat terminaalikäyttöä varten (ei Telegram-rajoituksia)
        system_message = (
            "TIIVIYSOHJE: Raporttisi maksimipituus on 900 sanaa. "
            "Lopeta AINA täyteen lauseeseen ennen tokenirajaa. "
            "Älä aloita uutta osiota jos et pysty viimeistelemään sitä.\n"
            "Älä kirjoita metakommentteja kuten 'Let me compile', 'Perfect', "
            "'I now have all data', 'Analysoin nyt'. "
            "Aloita raportti suoraan otsikolla tai ensimmäisillä havainnoilla.\n\n"
            "KRIITTINEN OHJE: Kirjoita KAIKKI analyysit ja raportit AINA suomeksi. "
            "Aloita analyysi välittömästi ilman johdantolauseita kuten 'Kiitos!' tai 'Hyvä!'.\n\n"
            + load_fi_prompt("fundamentals_system")
            + "\n\nKäytä seuraavia työkaluja: `get_fundamentals` kattavaan yhtiöanalyysiin, "
            "`get_balance_sheet`, `get_cashflow` ja `get_income_statement` tilinpäätöstiedoille. "
            "Kirjoita raportti suomeksi."
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
            "fundamentals_report": report,
        }

    return fundamentals_analyst_node
