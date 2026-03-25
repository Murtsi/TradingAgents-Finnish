import time
import json

from tradingagents.agents.utils.agent_utils import build_instrument_context
from tradingagents.agents.utils.prompt_loader import load_fi_prompt  # FORK: Suomi-lokalisointi


def create_research_manager(llm, memory):
    def research_manager_node(state) -> dict:
        instrument_context = build_instrument_context(state["company_of_interest"])
        history = state["investment_debate_state"].get("history", "")
        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]

        investment_debate_state = state["investment_debate_state"]

        curr_situation = f"{market_research_report}\n\n{sentiment_report}\n\n{news_report}\n\n{fundamentals_report}"
        past_memories = memory.get_memories(curr_situation, n_matches=2)

        past_memory_str = ""
        for i, rec in enumerate(past_memories, 1):
            past_memory_str += rec["recommendation"] + "\n\n"

        # FORK: Suomi-lokalisointi — Finnish system prompt
        # FORK: sanarajat terminaalikäyttöä varten (ei Telegram-rajoituksia)
        _fi_prompt = load_fi_prompt("research_manager_system")
        prompt = f"""TIIVIYSOHJE: Raporttisi maksimipituus on 600 sanaa. Lopeta AINA täyteen lauseeseen ennen tokenirajaa. Älä aloita uutta osiota jos et pysty viimeistelemään sitä.
Älä kirjoita metakommentteja kuten 'Let me compile', 'Perfect', 'I now have all data', 'Analysoin nyt'. Aloita raportti suoraan otsikolla tai ensimmäisillä havainnoilla.

{_fi_prompt}

{instrument_context}

---

**Aiemmista tilanteista opitut opit:**
{past_memory_str}

**Analyysidata:**
Markkinaraportti: {market_research_report}
Sentimenttiraportti: {sentiment_report}
Uutisraportti: {news_report}
Fundamenttiraportti: {fundamentals_report}

---

**Väittelyhistoria:**
{history}

Kirjoita koko analyysi ja investointisuunnitelma suomeksi."""
        response = llm.invoke(prompt)

        new_investment_debate_state = {
            "judge_decision": response.content,
            "history": investment_debate_state.get("history", ""),
            "bear_history": investment_debate_state.get("bear_history", ""),
            "bull_history": investment_debate_state.get("bull_history", ""),
            "current_response": response.content,
            "count": investment_debate_state["count"],
        }

        return {
            "investment_debate_state": new_investment_debate_state,
            "investment_plan": response.content,
        }

    return research_manager_node
