from langchain_core.messages import AIMessage
import time
import json
from tradingagents.agents.utils.agent_utils import build_instrument_context  # FORK: instrument context — estää väärän yhtiön tunnistuksen
from tradingagents.agents.utils.prompt_loader import load_fi_prompt  # FORK: Suomi-lokalisointi


def create_bear_researcher(llm, memory):
    def bear_node(state) -> dict:
        investment_debate_state = state["investment_debate_state"]
        history = investment_debate_state.get("history", "")
        bear_history = investment_debate_state.get("bear_history", "")

        current_response = investment_debate_state.get("current_response", "")
        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]

        # FORK: instrument context — estää väärän yhtiön tunnistuksen
        instrument_context = build_instrument_context(state["company_of_interest"])

        curr_situation = f"{market_research_report}\n\n{sentiment_report}\n\n{news_report}\n\n{fundamentals_report}"
        past_memories = memory.get_memories(curr_situation, n_matches=2)

        past_memory_str = ""
        for i, rec in enumerate(past_memories, 1):
            past_memory_str += rec["recommendation"] + "\n\n"

        # FORK: Suomi-lokalisointi — Finnish system prompt + data
        # FORK: sanarajat terminaalikäyttöä varten (ei Telegram-rajoituksia)
        _fi_prompt = load_fi_prompt("bear_researcher_system")
        prompt = f"""TIIVIYSOHJE: Raporttisi maksimipituus on 700 sanaa. Lopeta AINA täyteen lauseeseen ennen tokenirajaa. Älä aloita uutta osiota jos et pysty viimeistelemään sitä.
Älä kirjoita metakommentteja kuten 'Let me compile', 'Perfect', 'I now have all data', 'Analysoin nyt'. Aloita raportti suoraan otsikolla tai ensimmäisillä havainnoilla.

{_fi_prompt}

{instrument_context}

## Käytettävissä oleva data

Markkinatutkimusraportti: {market_research_report}
Sentimenttiraportti: {sentiment_report}
Uutisraportti: {news_report}
Fundamenttiraportti: {fundamentals_report}
Väittelyhistoria: {history}
Viimeisin bull-argumentti: {current_response}
Aiemmista tilanteista opitut opit: {past_memory_str}

Esitä argumenttisi suomeksi.
"""

        response = llm.invoke(prompt)

        argument = f"Bear Analyst: {response.content}"

        new_investment_debate_state = {
            "history": history + "\n" + argument,
            "bear_history": bear_history + "\n" + argument,
            "bull_history": investment_debate_state.get("bull_history", ""),
            "current_response": argument,
            "count": investment_debate_state["count"] + 1,
        }

        return {"investment_debate_state": new_investment_debate_state}

    return bear_node
