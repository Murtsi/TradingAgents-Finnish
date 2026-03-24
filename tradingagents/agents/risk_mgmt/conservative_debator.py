from langchain_core.messages import AIMessage
import time
import json
from tradingagents.agents.utils.prompt_loader import load_fi_prompt  # FORK: Suomi-lokalisointi


def create_conservative_debator(llm):
    def conservative_node(state) -> dict:
        risk_debate_state = state["risk_debate_state"]
        history = risk_debate_state.get("history", "")
        conservative_history = risk_debate_state.get("conservative_history", "")

        current_aggressive_response = risk_debate_state.get("current_aggressive_response", "")
        current_neutral_response = risk_debate_state.get("current_neutral_response", "")

        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]

        trader_decision = state["trader_investment_plan"]

        # FORK: Suomi-lokalisointi — konservatiivinen riskianalyytikko, korostaa riskejä
        _fi_prompt = load_fi_prompt("risk_system")
        prompt = f"""{_fi_prompt}

## Roolisi: Konservatiivinen riskianalyytikko
Tehtäväsi on suojata varallisuutta ja minimoida volatiliteetti. Haasta aggressiivisen ja neutraalin analyytikon argumentit varovaisuuden näkökulmasta. Vastaa suomeksi.

## Kauppiaan päätös
{trader_decision}

## Data
Markkinatutkimus: {market_research_report}
Sentimentti: {sentiment_report}
Uutiset: {news_report}
Fundamentit: {fundamentals_report}
Väittelyhistoria: {history}
Aggressiivisen analyytikon viimeisin argumentti: {current_aggressive_response}
Neutraalin analyytikon viimeisin argumentti: {current_neutral_response}

Esitä argumenttisi suomeksi keskustelevassa tyylissä ilman erikoismuotoilua."""

        response = llm.invoke(prompt)

        argument = f"Conservative Analyst: {response.content}"

        new_risk_debate_state = {
            "history": history + "\n" + argument,
            "aggressive_history": risk_debate_state.get("aggressive_history", ""),
            "conservative_history": conservative_history + "\n" + argument,
            "neutral_history": risk_debate_state.get("neutral_history", ""),
            "latest_speaker": "Conservative",
            "current_aggressive_response": risk_debate_state.get(
                "current_aggressive_response", ""
            ),
            "current_conservative_response": argument,
            "current_neutral_response": risk_debate_state.get(
                "current_neutral_response", ""
            ),
            "count": risk_debate_state["count"] + 1,
        }

        return {"risk_debate_state": new_risk_debate_state}

    return conservative_node
