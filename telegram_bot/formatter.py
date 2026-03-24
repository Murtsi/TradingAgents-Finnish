from __future__ import annotations
from datetime import datetime

DISCLAIMER = "⚠️ Tämä on AI:n tuottama analyysi, ei sijoitussuositus."

DECISION_MAP = {
    "buy":  "OSTA",
    "sell": "MYY",
    "hold": "PIDÄ",
}

DECISION_EMOJI = {
    "OSTA": "🟢",
    "MYY":  "🔴",
    "PIDÄ": "🟡",
}


def parse_decision(raw: str) -> str:
    """Muuntaa upstream BUY/SELL/HOLD → OSTA/MYY/PIDÄ."""
    first = raw.strip().split()[0].lower().rstrip("-,:.")
    return DECISION_MAP.get(first, "PIDÄ")


def format_finnish_price(price: float) -> str:
    """1234.56 → '1 234,56 €'"""
    formatted = f"{price:,.2f}".replace(",", " ").replace(".", ",")
    return f"{formatted} €"


def format_summary(state: dict, current_price: float | None = None) -> str:
    """Lyhyt yhteenveto Telegram-viestiksi."""
    ticker_raw = state.get("company_of_interest", "?")
    ticker = ticker_raw.replace(".HE", "")
    date_str = state.get("trade_date", datetime.now().strftime("%Y-%m-%d"))
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
        date_fi = d.strftime("%d.%m.%Y")
    except ValueError:
        date_fi = date_str

    raw_decision = state.get("final_trade_decision", "")
    suositus = parse_decision(raw_decision)
    emoji = DECISION_EMOJI.get(suositus, "⬜")
    price_str = format_finnish_price(current_price) if current_price else "—"

    plan = state.get("trader_investment_plan", "")
    lyhyt = plan[:200].strip()
    if len(plan) > 200:
        lyhyt += "…"

    lines = [
        f"📊 *{ticker}* ({ticker_raw}) — {date_fi}",
        "━━━━━━━━━━━━━━━━━━━━━",
        f"{emoji} *SUOSITUS: {suositus}*",
        f"💰 Kurssi: {price_str}",
        "",
        f"📝 _{lyhyt}_",
        "",
        DISCLAIMER,
    ]
    return "\n".join(lines)


def format_full_report(state: dict) -> str:
    """Koko raportti kaikilla agenttien tuloksilla."""
    ticker_raw = state.get("company_of_interest", "?")
    ticker = ticker_raw.replace(".HE", "")
    date_str = state.get("trade_date", "")
    raw_decision = state.get("final_trade_decision", "")
    suositus = parse_decision(raw_decision)
    emoji = DECISION_EMOJI.get(suositus, "⬜")

    sections = [
        f"📊 *{ticker} — Täysi analyysi* ({date_str})",
        "━━━━━━━━━━━━━━━━━━━━━",
        f"{emoji} *Lopullinen suositus: {suositus}*",
        "",
        "📈 *Tekninen analyysi*",
        state.get("market_report", "—")[:800],
        "",
        "💬 *Sentimenttianalyysi*",
        state.get("sentiment_report", "—")[:800],
        "",
        "📰 *Uutisanalyysi*",
        state.get("news_report", "—")[:800],
        "",
        "📋 *Fundamenttianalyysi*",
        state.get("fundamentals_report", "—")[:800],
        "",
        "⚖️ *Kaupankäyntipäätös*",
        state.get("trader_investment_plan", "—")[:600],
        "",
        "🛡 *Riskiarvio*",
        state.get("investment_plan", "—")[:400],
        "",
        DISCLAIMER,
    ]
    return "\n".join(sections)
