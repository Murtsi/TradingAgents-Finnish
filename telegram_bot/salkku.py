"""
KauppaAgentit — /salkku-komento.

Hallitsee käyttäjän osakkeiden seurantalistaa (watchlist).
Tallennus: DATABASE_URL:n mukaiseen tietokantaan.

Alikomennot:
    /salkku          — näytä seurantalista
    /salkku lisaa NOKIA  — lisää osaketta seurantaan
    /salkku poista NOKIA — poista osaketta seurannasta
"""
from __future__ import annotations

import logging
from datetime import date

from telegram import Update
from telegram.ext import ContextTypes

from telegram_bot.omxh import validate_ticker
from telegram_bot.whitelist import is_allowed
from autotrader.storage import get_storage

logger = logging.getLogger(__name__)

# Enimmäismäärä osakkeita salkussa
MAX_OSAKKEET = 10

# Tyyppialiakset
Osake = dict[str, str]
Salkku = dict[str, list[Osake]]


# ---------------------------------------------------------------------------
# Tallennuslogiikka
# ---------------------------------------------------------------------------


def _lataa_salkku() -> Salkku:
    """Yhteensopiva koko salkun luku ei ole käytössä DB-tallennuksessa."""
    return {}


def _tallenna_salkku(salkku: Salkku) -> None:
    """Yhteensopivuusfunktio vanhoille testeille; DB-koodi ei kutsu tätä."""
    return None


def _hae_kayttajan_osakkeet(user_id: int) -> list[Osake]:
    """Palauttaa käyttäjän osakkeiden listan. Tyhjä lista jos ei ole."""
    return get_storage().list_watchlist(user_id)


def _aseta_kayttajan_osakkeet(user_id: int, osakkeet: list[Osake]) -> None:
    """Ei käytössä DB-tallennuksessa."""
    return None


# ---------------------------------------------------------------------------
# Salkun muokkausoperaatiot
# ---------------------------------------------------------------------------


def _lisaa_osake(user_id: int, yf_ticker: str, nimi: str) -> tuple[bool, str]:
    """
    Lisää osakkeen käyttäjän seurantalistaan.

    Palauttaa (onnistui: bool, viesti: str).
    """
    osakkeet = _hae_kayttajan_osakkeet(user_id)

    # Tarkista duplikaatti
    for osake in osakkeet:
        if osake["ticker"] == yf_ticker:
            return False, f"[HUOMIO] {nimi} on jo seurantalistalla."

    # Tarkista enimmäismäärä
    if len(osakkeet) >= MAX_OSAKKEET:
        return False, (
            f"[VIRHE] Seurantalista on täynnä ({MAX_OSAKKEET} osaketta).\n"
            "Poista ensin jokin osake: /salkku poista <OSAKE>"
        )

    osakkeet.append({
        "ticker": yf_ticker,
        "nimi": nimi,
        "lisatty": str(date.today()),
    })
    get_storage().add_watchlist_item(user_id, yf_ticker, nimi, str(date.today()))
    return True, f"[VALMIS] {nimi} lisatty seurantaan."


def _poista_osake(user_id: int, nimi: str) -> tuple[bool, str]:
    """
    Poistaa osakkeen käyttäjän seurantalistalta nimen tai tickerin perusteella.

    Vertailu tehdään isoilla kirjaimilla (case-insensitive).
    Palauttaa (onnistui: bool, viesti: str).
    """
    poistettu = get_storage().remove_watchlist_item(user_id, nimi)
    if poistettu <= 0:
        return False, f"[VIRHE] {nimi} ei ole seurantalistalla."

    return True, f"[VALMIS] {nimi} poistettu seurannasta."


# ---------------------------------------------------------------------------
# Vastausformatointi
# ---------------------------------------------------------------------------


def _muodosta_salkku_teksti(osakkeet: list[Osake]) -> str:
    """Muodostaa seurantalistasta Telegram-viestipohjan."""
    if not osakkeet:
        return (
            "[SALKKU] Seurantalista on tyhja.\n\n"
            "Lisaa: /salkku lisaa NOKIA"
        )

    rivit = ["[SALKKU] Seurantalista\n"]
    for i, osake in enumerate(osakkeet, start=1):
        rivit.append(f"{i}. {osake['nimi']}  ({osake['ticker']})")

    rivit.append(
        "\nKomennot:\n"
        "/salkku lisaa <OSAKE>\n"
        "/salkku poista <OSAKE>\n"
        "/analysoi <OSAKE>"
    )
    return "\n".join(rivit)


# ---------------------------------------------------------------------------
# Telegram-komennon käsittelijä
# ---------------------------------------------------------------------------


async def salkku_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /salkku-komennon Telegram-käsittelijä.

    Alikomennot:
        /salkku              — näytä seurantalista
        /salkku lisaa NOKIA  — lisää osake
        /salkku poista NOKIA — poista osake
    """
    user = update.effective_user
    if user is None:
        return

    user_id: int = user.id

    # Whitelist-tarkistus — hiljaisuus tuntemattomille
    if not is_allowed(user_id):
        logger.warning(f"Whitelist-esto /salkku: {user_id} (@{user.username})")
        return

    args: list[str] = context.args or []

    # --- Näytä lista (ei argumentteja) ---
    if not args:
        osakkeet = _hae_kayttajan_osakkeet(user_id)
        await update.message.reply_text(_muodosta_salkku_teksti(osakkeet))
        return

    alikomento = args[0].lower()

    # --- Lisaa ---
    if alikomento == "lisaa":
        if len(args) < 2:
            await update.message.reply_text(
                "[VIRHE] Kerro lisattava osake.\nEsim: /salkku lisaa NOKIA"
            )
            return

        raw = args[1].upper().strip()

        # Validoi ticker Yahoo Financesta
        await update.message.reply_text(f"Tarkistetaan osake {raw}...")
        yf_ticker = validate_ticker(raw)
        if yf_ticker is None:
            await update.message.reply_text(
                f"[VIRHE] En loyda osaketta {raw}.\n"
                "Kokeile esim. /salkku lisaa NOKIA tai /salkku lisaa NESTE"
            )
            return

        # Muodosta lyhyt nimi YF-tunnuksesta (ilman .HE-paatetta)
        nimi = yf_ticker.split(".")[0]

        onnistui, viesti = _lisaa_osake(user_id, yf_ticker, nimi)
        await update.message.reply_text(viesti)
        return

    # --- Poista ---
    if alikomento == "poista":
        if len(args) < 2:
            await update.message.reply_text(
                "[VIRHE] Kerro poistettava osake.\nEsim: /salkku poista NOKIA"
            )
            return

        raw = args[1].upper().strip()
        onnistui, viesti = _poista_osake(user_id, raw)
        await update.message.reply_text(viesti)
        return

    # --- Tuntematon alikomento ---
    await update.message.reply_text(
        "[VIRHE] Tuntematon alikomento.\n\n"
        "Kaytto:\n"
        "/salkku              — nayта seurantalista\n"
        "/salkku lisaa NOKIA  — lisaa osake\n"
        "/salkku poista NOKIA — poista osake"
    )
