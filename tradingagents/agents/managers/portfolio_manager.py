from tradingagents.agents.utils.agent_utils import build_instrument_context
from tradingagents.agents.utils.prompt_loader import load_fi_prompt  # FORK: Suomi-lokalisointi


def create_portfolio_manager(llm, memory):
    def portfolio_manager_node(state) -> dict:

        instrument_context = build_instrument_context(state["company_of_interest"])
        current_date = state.get("trade_date", "")

        history = state["risk_debate_state"]["history"]
        risk_debate_state = state["risk_debate_state"]
        market_research_report = state["market_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]
        sentiment_report = state["sentiment_report"]
        research_plan = state["investment_plan"]
        trader_plan = state["trader_investment_plan"]

        curr_situation = f"{market_research_report}\n\n{sentiment_report}\n\n{news_report}\n\n{fundamentals_report}"
        past_memories = memory.get_memories(curr_situation, n_matches=2)

        past_memory_str = ""
        for i, rec in enumerate(past_memories, 1):
            past_memory_str += rec["recommendation"] + "\n\n"

        # FORK: Suomi-lokalisointi — Finnish system prompt + data
        # FORK: sanarajat terminaalikäyttöä varten (ei Telegram-rajoituksia)
        _fi_prompt = load_fi_prompt("portfolio_manager_system")
        prompt = f"""TIIVIYSOHJE: Raporttisi maksimipituus on 600 sanaa. Lopeta AINA täyteen lauseeseen ennen tokenirajaa. Älä aloita uutta osiota jos et pysty viimeistelemään sitä.
Älä kirjoita metakommentteja kuten 'Let me compile', 'Perfect', 'I now have all data', 'Analysoin nyt'. Aloita raportti suoraan otsikolla tai ensimmäisillä havainnoilla.

{_fi_prompt}

{instrument_context}
**Analyysipäivämäärä:** {current_date} — käytä tätä päivämäärää raportissa, älä hallusinoi muuta päivämäärää.

---

**Suositusasteikko** (käytä täsmälleen yhtä):
- **Osta** (Buy): Vahva vakaumus — osta tai lisää positiota
- **Ylipainota** (Overweight): Myönteinen näkymä, lisää altistusta asteittain
- **Pidä** (Hold): Säilytä nykyinen positio, ei toimenpiteitä
- **Alipainota** (Underweight): Vähennä altistusta, ota osittaisia voittoja
- **Myy** (Sell): Sulje positio tai vältä ostamista

**Konteksti:**
- Tutkimuspäällikkö suunnitelma: {research_plan}
- Kauppiaan transaktiosuositus: {trader_plan}
- Aiemmista päätöksistä opitut opit: {past_memory_str}

---

**Riskianalyytikkojen väittelyhistoria:**
{history}

---

Ole päättäväinen ja perusta kaikki päätelmät analyytikkojen konkreettisiin havaintoihin. Kirjoita koko raportti suomeksi."""

        response = llm.invoke(prompt)

        new_risk_debate_state = {
            "judge_decision": response.content,
            "history": risk_debate_state["history"],
            "aggressive_history": risk_debate_state["aggressive_history"],
            "conservative_history": risk_debate_state["conservative_history"],
            "neutral_history": risk_debate_state["neutral_history"],
            "latest_speaker": "Judge",
            "current_aggressive_response": risk_debate_state["current_aggressive_response"],
            "current_conservative_response": risk_debate_state["current_conservative_response"],
            "current_neutral_response": risk_debate_state["current_neutral_response"],
            "count": risk_debate_state["count"],
        }

        return {
            "risk_debate_state": new_risk_debate_state,
            "final_trade_decision": response.content,
        }

    return portfolio_manager_node
