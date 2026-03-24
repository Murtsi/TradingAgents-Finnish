import time
import json
from tradingagents.agents.utils.prompt_loader import load_fi_prompt  # FORK: Suomi-lokalisointi


def create_aggressive_debator(llm):
    def aggressive_node(state) -> dict:
        risk_debate_state = state["risk_debate_state"]
        history = risk_debate_state.get("history", "")
        aggressive_history = risk_debate_state.get("aggressive_history", "")

        current_conservative_response = risk_debate_state.get("current_conservative_response", "")
        current_neutral_response = risk_debate_state.get("current_neutral_response", "")

        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]

        trader_decision = state["trader_investment_plan"]

        # FORK: Suomi-lokalisointi — aggressiivinen riskianalyytikko, puolustaa rohkeita päätöksiä
        _fi_prompt = load_fi_prompt("risk_system")
        prompt = f"""{_fi_prompt}

## Roolisi: Aggressiivinen riskianalyytikko
Puolustat kauppiaan päätöstä ja korostat kasvupotentiaalia ja tuotto-odotuksia. Haasta konservatiivisen ja neutraalin analyytikon argumentit rohkeasti. Vastaa suomeksi.

## Kauppiaan päätös
{trader_decision}

## Data
Markkinatutkimus: {market_research_report}
Sentimentti: {sentiment_report}
Uutiset: {news_report}
Fundamentit: {fundamentals_report}
Väittelyhistoria: {history}
Konservatiivisen analyytikon viimeisin argumentti: {current_conservative_response}
Neutraalin analyytikon viimeisin argumentti: {current_neutral_response}

Esitä argumenttisi suomeksi keskustelevassa tyylissä ilman erikoismuotoilua."""

        response = llm.invoke(prompt)

        argument = f"Aggressive Analyst: {response.content}"

        new_risk_debate_state = {
            "history": history + "\n" + argument,
            "aggressive_history": aggressive_history + "\n" + argument,
            "conservative_history": risk_debate_state.get("conservative_history", ""),
            "neutral_history": risk_debate_state.get("neutral_history", ""),
            "latest_speaker": "Aggressive",
            "current_aggressive_response": argument,
            "current_conservative_response": risk_debate_state.get("current_conservative_response", ""),
            "current_neutral_response": risk_debate_state.get(
                "current_neutral_response", ""
            ),
            "count": risk_debate_state["count"] + 1,
        }

        return {"risk_debate_state": new_risk_debate_state}

    return aggressive_node
