import functools
import time
import json

from tradingagents.agents.utils.agent_utils import build_instrument_context
from tradingagents.agents.utils.prompt_loader import load_fi_prompt  # FORK: Suomi-lokalisointi


def create_trader(llm, memory):
    def trader_node(state, name):
        company_name = state["company_of_interest"]
        instrument_context = build_instrument_context(company_name)
        investment_plan = state["investment_plan"]
        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]

        curr_situation = f"{market_research_report}\n\n{sentiment_report}\n\n{news_report}\n\n{fundamentals_report}"
        past_memories = memory.get_memories(curr_situation, n_matches=2)

        past_memory_str = ""
        if past_memories:
            for i, rec in enumerate(past_memories, 1):
                past_memory_str += rec["recommendation"] + "\n\n"
        else:
            past_memory_str = "Ei aiempia muistoja."

        # FORK: Suomi-lokalisointi — Finnish system prompt
        _fi_prompt = load_fi_prompt("trader_system")
        context = {
            "role": "user",
            "content": (
                f"Analyytikkojen kattavan analyysin pohjalta tässä on sijoitussuunnitelma yhtiölle {company_name}. "
                f"{instrument_context} Suunnitelma sisältää näkemykset teknisistä trendeistä, "
                f"makrotaloudesta ja sentimentistä. Käytä tätä kaupankäyntipäätöksesi pohjana.\n\n"
                f"Ehdotettu sijoitussuunnitelma: {investment_plan}\n\n"
                f"Päätä analyysisi selkeään suositukseen: OSTA, PIDÄ tai MYY. "
                f"Päätä vastauksesi aina lauseeseen 'FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL**'."
            ),
        }

        # FORK: sanarajat terminaalikäyttöä varten (ei Telegram-rajoituksia)
        messages = [
            {
                "role": "system",
                "content": (
                    "TIIVIYSOHJE: Raporttisi maksimipituus on 500 sanaa. "
                    "Lopeta AINA täyteen lauseeseen ennen tokenirajaa. "
                    "Älä aloita uutta osiota jos et pysty viimeistelemään sitä.\n"
                    "Älä kirjoita metakommentteja kuten 'Let me compile', 'Perfect', "
                    "'I now have all data', 'Analysoin nyt'. "
                    "Aloita raportti suoraan otsikolla tai ensimmäisillä havainnoilla.\n\n"
                    f"{_fi_prompt}\n\n"
                    f"Aiemmista tilanteista opitut opit: {past_memory_str}"
                ),
            },
            context,
        ]

        result = llm.invoke(messages)

        return {
            "messages": [result],
            "trader_investment_plan": result.content,
            "sender": name,
        }

    return functools.partial(trader_node, name="Trader")
