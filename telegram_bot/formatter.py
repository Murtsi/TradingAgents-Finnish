from __future__ import annotations
import re
from datetime import datetime

DISCLAIMER = "⚠️ Tämä on AI:n tuottama analyysi, ei sijoitussuositus."

# BUY/SELL/HOLD -variantit joita agentit käyttävät (ensimmäinen osuma voittaa)
_SELL_WORDS  = {"sell", "underweight", "myy", "myyda", "myi"}
_BUY_WORDS   = {"buy", "overweight", "osta"}
_HOLD_WORDS  = {"hold", "neutral", "pidä", "pida", "maintain"}

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
    """
    Etsii ensimmäisen selvän BUY/SELL/HOLD-signaalin koko tekstistä.
    Agentit käyttävät mm. OVERWEIGHT/UNDERWEIGHT/RATING: **SELL** -muotoja
    joten pelkkä ensimmäisen sanan tarkistus ei riitä.
    """
    if not raw:
        return "PIDÄ"

    # Etsi kaikki sanat tekstistä (lowercase, ilman erikoismerkkejä)
    words = set(re.findall(r"[a-zäöå]+", raw.lower()))

    # SELL saa etusijan — epäselvässä tilanteessa varovaisuus ensin
    if words & _SELL_WORDS:
        return "MYY"
    if words & _BUY_WORDS:
        return "OSTA"
    if words & _HOLD_WORDS:
        return "PIDÄ"
    return "PIDÄ"


def _strip_markdown(text: str) -> str:
    """Poistaa Markdown-muotoilun tekstistä jotta se on luettavaa plain textinä."""
    # Otsikot: ### Foo → FOO (isolla korostuksena)
    text = re.sub(r"^#{1,6}\s+(.+)$", lambda m: m.group(1).upper(), text, flags=re.MULTILINE)
    # Lihavointi/kursiivi: **foo** / *foo* / __foo__ / _foo_
    text = re.sub(r"\*{1,2}([^*\n]+)\*{1,2}", r"\1", text)
    text = re.sub(r"_{1,2}([^_\n]+)_{1,2}", r"\1", text)
    # Vaakaviivat
    text = re.sub(r"^[-─]{3,}\s*$", "─────────────", text, flags=re.MULTILINE)
    # Linkit: [teksti](url) → teksti
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    # Useampi tyhjä rivi → yksi
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _truncate(text: str, max_chars: int) -> str:
    """
    Katkaisee tekstin viimeisen täyden lauseen kohdalta, ei sanan keskeltä.
    """
    if len(text) <= max_chars:
        return text
    chunk = text[:max_chars]
    # Etsi viimeisin lauseen loppu (. ! ?) joka on vähintään puolessa välissä
    for pattern in (r"[.!?]\s", r"[.!?]\n", r"\n\n"):
        matches = list(re.finditer(pattern, chunk))
        if matches:
            last = matches[-1]
            if last.end() > max_chars // 2:
                return chunk[:last.end()].rstrip() + "…"
    return chunk.rstrip() + "…"


def format_finnish_price(price: float) -> str:
    """1234.56 → '1 234,56 €'"""
    formatted = f"{price:,.2f}".replace(",", " ").replace(".", ",")
    return f"{formatted} €"


def format_summary(state: dict, current_price: float | None = None) -> str:
    """Lyhyt yhteenveto Telegram-viestiksi (käyttää Markdown-muotoilua)."""
    ticker_raw = state.get("company_of_interest", "?")
    ticker = ticker_raw.replace(".HE", "")
    date_str = state.get("trade_date", datetime.now().strftime("%Y-%m-%d"))
    try:
        date_fi = datetime.strptime(date_str, "%Y-%m-%d").strftime("%d.%m.%Y")
    except ValueError:
        date_fi = date_str

    raw_decision = state.get("final_trade_decision", "")
    suositus = parse_decision(raw_decision)
    emoji = DECISION_EMOJI.get(suositus, "⬜")
    price_str = format_finnish_price(current_price) if current_price else "—"

    # Kauppiaan lyhyt perustelu — siistiä plain text, katkaistaan lauseelta
    plan = state.get("trader_investment_decision", "") or state.get("trader_investment_plan", "")
    plan_clean = _strip_markdown(plan)
    lyhyt = _truncate(plan_clean, 300)

    lines = [
        f"📊 *{ticker}* — {date_fi}",
        "━━━━━━━━━━━━━━━━━━━━━",
        f"{emoji} *SIGNAALI: {suositus}*",
        f"💰 Kurssi: {price_str}",
        "",
        lyhyt,
        "",
        DISCLAIMER,
    ]
    return "\n".join(lines)


def format_full_report(state: dict) -> str:
    """
    Koko raportti — lähetetään plain textinä (ei parse_mode).
    Markdown poistetaan _strip_markdown():lla, teksti katkaistaan lauseelta.
    """
    ticker_raw = state.get("company_of_interest", "?")
    ticker = ticker_raw.replace(".HE", "")
    date_str = state.get("trade_date", "")
    suositus = parse_decision(state.get("final_trade_decision", ""))
    emoji = DECISION_EMOJI.get(suositus, "⬜")

    def section(raw: str, limit: int) -> str:
        return _truncate(_strip_markdown(raw), limit) if raw else "—"

    parts = [
        f"📊 {ticker} — Täysi analyysi ({date_str})",
        "━━━━━━━━━━━━━━━━━━━━━",
        f"{emoji} Signaali: {suositus}",
        "",
        "📈 TEKNINEN ANALYYSI",
        section(state.get("market_report", ""), 900),
        "",
        "💬 SENTIMENTTIANALYYSI",
        section(state.get("sentiment_report", ""), 900),
        "",
        "📰 UUTISANALYYSI",
        section(state.get("news_report", ""), 900),
        "",
        "📋 FUNDAMENTTIANALYYSI",
        section(state.get("fundamentals_report", ""), 900),
        "",
        "⚖️ KAUPANKÄYNTIPÄÄTÖS",
        section(
            state.get("trader_investment_decision") or state.get("trader_investment_plan", ""),
            700,
        ),
        "",
        "📊 TUTKIJOIDEN PÄÄTELMÄT",
        section(state.get("investment_plan", ""), 500),
        "",
        "🛡 SALKUNHOITAJAN PÄÄTÖS",
        section(state.get("final_trade_decision", ""), 700),
        "",
        DISCLAIMER,
    ]
    return "\n".join(parts)
