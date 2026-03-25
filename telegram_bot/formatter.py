from __future__ import annotations
import re
from datetime import datetime

DISCLAIMER = "[HUOMIO] Tämä on AI:n tuottama analyysi, ei sijoitussuositus."

# BUY/SELL/HOLD -variantit joita agentit käyttävät (ensimmäinen osuma voittaa)
_SELL_WORDS  = {"sell", "underweight", "myy", "myyda", "myi"}
_BUY_WORDS   = {"buy", "overweight", "osta"}
_HOLD_WORDS  = {"hold", "neutral", "pidä", "pida", "maintain"}

DECISION_MAP = {
    "buy":  "OSTA",
    "sell": "MYY",
    "hold": "PIDÄ",
}

DECISION_LABEL = {
    "OSTA": "[OSTA-SIGNAALI]",
    "MYY":  "[MYY-SIGNAALI]",
    "PIDÄ": "[PIDÄ-SIGNAALI]",
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


def _strip_emojis(text: str) -> str:
    """Poistaa Unicode-emojit tekstistä (agentit tuottavat niitä prompteistaan huolimatta)."""
    # Kattaa yleisimmät emoji-alueet: Emoticons, Misc Symbols, Dingbats,
    # Supplemental Symbols, Transport & Map, Enclosed Alphanumeric Supplement
    return re.sub(
        r"[\U0001F300-\U0001F9FF"   # Misc Symbols and Pictographs, Emoticons, Transport
        r"\U00002702-\U000027B0"    # Dingbats
        r"\U000024C2-\U0001F251"    # Enclosed characters
        r"\u2600-\u26FF"            # Misc symbols (☀ ★ ⬜ jne.)
        r"\u2700-\u27BF"            # Dingbats
        r"\uFE00-\uFE0F"            # Variation selectors (modifier)
        r"]+",
        "",
        text,
    )


def _strip_markdown(text: str) -> str:
    """Poistaa Markdown-muotoilun ja emojit tekstistä jotta se on luettavaa plain textinä."""
    # Emojit pois ensin — agentit tuottavat niitä vaikka promptit kieltäisivät
    text = _strip_emojis(text)
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


def _strip_openers(text: str) -> str:
    """
    Poistaa LLM:n konversaatio-avaajat raportin alusta.
    Esim: "Kiitos! Nyt minulla on kattava data." tai "I can see there are some relevant..."
    Säilyttää tekstin ensimmäisestä oikeasta sisältörivistä eteenpäin.
    """
    # Tunnistaa meta-kommenttirivin: ei numeroita/prosentteja, lyhyt (<120 merkkiä),
    # loppuu pisteeseen/huutomerkkiin, ei ala listamerkillä tai otsikolla
    opener_patterns = [
        # Suomalaiset avaajat
        r"^(Kiitos!?|Hyvä!?|Loistava!?|Erinomainen!?|Selvä!?)\s.*\n",
        r"^Nyt minulla on kattav\w+.*\n",
        # Englanninkieliset avaajat
        r"^(Based on|I can see|Let me|I will|I'll|I have|I now|I've|Great|Perfect|Thank)[^\n]{0,150}\n",
        r"^(Here is|Here's|Below is|This is a|Now I|Now let me)[^\n]{0,150}\n",
    ]
    for pat in opener_patterns:
        text = re.sub(pat, "", text, flags=re.IGNORECASE | re.MULTILINE)
    return text.lstrip("\n")


def _is_llm_truncated(text: str) -> bool:
    """
    Tunnistaa onko LLM-vastaus katkaisttu max_tokens-rajan takia.
    Tarkistaa viimeisen ei-tyhjän rivin — taulukkorivit, listaalkiot ja
    otsikot hyväksytään päättyneiksi vaikka niissä ei ole loppupistettä.
    """
    if not text:
        return False
    lines = [ln for ln in text.rstrip().splitlines() if ln.strip()]
    if not lines:
        return False
    last = lines[-1].rstrip()
    if last.endswith("…"):
        return False
    # Lause päättyy oikein: .  !  ?  )  "
    if re.search(r"[.!?)\"][\s]*$", last):
        return False
    # Taulukkorivin loppu tai alku
    if last.endswith("|") or last.startswith("|"):
        return False
    # Bullet-kohta tai numeroitu lista
    if re.match(r"^[-*•]\s+", last) or re.match(r"^\d+\.\s+", last):
        return False
    # Erotinrivi (---  tai ━━━)
    if re.match(r"^[─━\-]{3,}$", last):
        return False
    return True


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
    signaali_label = DECISION_LABEL.get(suositus, "[SIGNAALI]")
    price_str = format_finnish_price(current_price) if current_price else "—"

    # Kauppiaan lyhyt perustelu — siistiä plain text, katkaistaan lauseelta
    plan = state.get("trader_investment_decision", "") or state.get("trader_investment_plan", "")
    plan_clean = _strip_markdown(plan)
    lyhyt = _truncate(plan_clean, 300)

    lines = [
        f"*{ticker}* — {date_fi}",
        "━━━━━━━━━━━━━━━━━━━━━",
        f"*{signaali_label}*",
        f"Kurssi: {price_str}",
        "",
        lyhyt,
        "",
        DISCLAIMER,
    ]
    return "\n".join(lines)


def format_full_report(state: dict) -> str:
    """
    Koko raportti — lähetetään plain textinä (ei parse_mode).
    Markdown ja emojit poistetaan. Ei per-osio-rajoituksia — handlers.py jakaa
    pitkän tekstin useampaan Telegram-viestiin _split_at_newline():lla.
    """
    ticker_raw = state.get("company_of_interest", "?")
    ticker = ticker_raw.replace(".HE", "")
    date_str = state.get("trade_date", "")
    suositus = parse_decision(state.get("final_trade_decision", ""))
    signaali_label = DECISION_LABEL.get(suositus, "[SIGNAALI]")

    def section(raw: str) -> str:
        """Strippaaa markdown + emojit + konversaatio-avaajat, ei katkaisua."""
        if not raw:
            return "—"
        cleaned = _strip_openers(raw)
        return _strip_markdown(cleaned).strip()

    parts = [
        f"{ticker} — Taysi analyysi ({date_str})",
        "━━━━━━━━━━━━━━━━━━━━━",
        f"Signaali: {signaali_label}",
        "",
        "━━━ TEKNINEN ANALYYSI ━━━",
        section(state.get("market_report", "")),
        "",
        "━━━ SENTIMENTTIANALYYSI ━━━",
        section(state.get("sentiment_report", "")),
        "",
        "━━━ UUTISANALYYSI ━━━",
        section(state.get("news_report", "")),
        "",
        "━━━ FUNDAMENTTIANALYYSI ━━━",
        section(state.get("fundamentals_report", "")),
        "",
        "━━━ KAUPANKÄYNTIPÄÄTÖS ━━━",
        section(state.get("trader_investment_decision") or state.get("trader_investment_plan", "")),
        "",
        "━━━ TUTKIJOIDEN PÄÄTELMÄT ━━━",
        section(state.get("investment_plan", "")),
        "",
        "━━━ SALKUNHOITAJAN PÄÄTÖS ━━━",
        section(state.get("final_trade_decision", "")),
        "",
        DISCLAIMER,
    ]
    return "\n".join(parts)


# Max merkkejä per osio — pitää yksittäisen viestin Telegramin 4096 rajan alla
# Otsikko + ━━━ -rivi vie ~80 merkkiä → jätetään 3900 merkkiä sisällölle (4096 - 196 turvamarginaali)
_SECTION_MAX = 3900


def format_full_report_parts(state: dict) -> list[str]:
    """
    Jokainen analyytikkoraportti omana Telegram-viestiään (8 viestiä).
    Otsikot Markdown-lihavoituina (*OTSIKKO*). Sisältö plain text (emojit/md poistettu).

      1. Otsikkoviesti (ticker, päivä, signaali)
      2. Tekninen analyysi
      3. Sentimenttianalyysi
      4. Uutisanalyysi
      5. Fundamenttianalyysi
      6. Kaupankäyntipäätös
      7. Tutkijoiden päätelmät
      8. Salkunhoitajan päätös + Vastuuvapautus
    """
    ticker_raw = state.get("company_of_interest", "?")
    ticker = ticker_raw.replace(".HE", "")
    date_str = state.get("trade_date", "")
    try:
        date_fi = datetime.strptime(date_str, "%Y-%m-%d").strftime("%d.%m.%Y")
    except (ValueError, TypeError):
        date_fi = date_str
    suositus = parse_decision(state.get("final_trade_decision", ""))
    signaali_label = DECISION_LABEL.get(suositus, "[SIGNAALI]")

    def section(raw: str) -> str:
        if not raw:
            return "—"
        cleaned = _strip_openers(raw)
        text = _strip_markdown(cleaned).strip()
        return _truncate(text, _SECTION_MAX)

    trader = state.get("trader_investment_decision") or state.get("trader_investment_plan", "")

    snap = state.get("_price_snapshot") or {}
    price_line = ""
    if snap.get("price"):
        price_line = f"\nKurssi analyysihetkella: {snap['price']:.2f} EUR"
        if snap.get("volume"):
            price_line += f"  |  Volyymi: {int(snap['volume']):,}".replace(",", " ")
        if snap.get("bid") and snap.get("ask"):
            price_line += f"\nBid: {snap['bid']:.2f}  |  Ask: {snap['ask']:.2f}"

    parts = [
        # 1. Otsikkoviesti
        f"*{ticker} — Taysi analyysi*\n{date_fi}\n━━━━━━━━━━━━━━━━━━━━━\nSignaali: *{signaali_label}*{price_line}",

        # 2. Tekninen analyysi
        f"*TEKNINEN ANALYYSI — {ticker}*\n━━━━━━━━━━━━━━━━━━━━━\n{section(state.get('market_report', ''))}",

        # 3. Sentimenttianalyysi
        f"*SENTIMENTTIANALYYSI — {ticker}*\n━━━━━━━━━━━━━━━━━━━━━\n{section(state.get('sentiment_report', ''))}",

        # 4. Uutisanalyysi
        f"*UUTISANALYYSI — {ticker}*\n━━━━━━━━━━━━━━━━━━━━━\n{section(state.get('news_report', ''))}",

        # 5. Fundamenttianalyysi
        f"*FUNDAMENTTIANALYYSI — {ticker}*\n━━━━━━━━━━━━━━━━━━━━━\n{section(state.get('fundamentals_report', ''))}",

        # 6. Kaupankäyntipäätös
        f"*KAUPANKÄYNTIPÄÄTÖS — {ticker}*\n━━━━━━━━━━━━━━━━━━━━━\n{section(trader)}",

        # 7. Tutkijoiden päätelmät
        f"*TUTKIJOIDEN PÄÄTELMÄT — {ticker}*\n━━━━━━━━━━━━━━━━━━━━━\n{section(state.get('investment_plan', ''))}",

        # 8. Salkunhoitajan päätös + vastuuvapautus
        f"*SALKUNHOITAJAN PÄÄTÖS — {ticker}*\n━━━━━━━━━━━━━━━━━━━━━\n{section(state.get('final_trade_decision', ''))}\n\n{DISCLAIMER}",
    ]
    return parts
