"""
Hintahälytysten hallinta Telegram-botille.

Tallentaa hälytykset DATABASE_URL:n mukaiseen tietokantaan.
Tukee nousua (+%) ja laskua (-%) koskevia hälytyksiä OMXH-osakkeille.

FORK: Suomi-lokalisointi — uusi tiedosto
"""
from __future__ import annotations

import logging
import re
from datetime import date
from typing import TypedDict

from telegram import Update
from telegram.ext import ContextTypes

from telegram_bot.omxh import validate_ticker, get_current_price
from telegram_bot.whitelist import is_allowed
from autotrader.storage import get_storage

logger = logging.getLogger(__name__)

# Maksimi hälytyksiä per käyttäjä
MAX_HALYTYKSET_PER_KAYTTAJA = 20

# Regex prosentin parsimiseen: +5%, -3%, +10.5%
PROSENTTI_REGEX = re.compile(r"^([+-])(\d+(?:\.\d+)?)%$")


class Halytys(TypedDict):
    """Yksittäisen hälytyksen tietorakenne."""

    ticker: str          # Yahoo Finance -tunnus, esim. NOKIA.HE
    nimi: str            # Lyhyttunnus, esim. NOKIA
    tyyppi: str          # "lasku" tai "nousu"
    prosentti: float     # Positiivinen luku, esim. 5.0
    hinta_luontihetkella: float  # EUR-kurssi hälytyksen luontihetkellä
    luotu: str           # ISO-päivä, esim. 2026-03-25


def _lue_halytykset() -> dict[str, list[Halytys]]:
    """Yhteensopivuusfunktio vanhalle JSON-polulle; DB-koodi lukee käyttäjäkohtaisesti."""
    return {}


def _tallenna_halytykset(data: dict[str, list[Halytys]]) -> bool:
    """Yhteensopivuusfunktio vanhalle JSON-polulle."""
    return True


def _laske_halytysraja(hinta: float, tyyppi: str, prosentti: float) -> float:
    """
    Laskee EUR-halytysrajan annetusta hinnasta.

    Args:
        hinta: Osakkeen kurssi hälytyksen luontihetkellä (EUR).
        tyyppi: "lasku" tai "nousu".
        prosentti: Positiivinen prosenttiluku.

    Returns:
        Halytysraja euroissa pyöristettynä kahteen desimaaliin.
    """
    if tyyppi == "lasku":
        return round(hinta * (1 - prosentti / 100), 2)
    return round(hinta * (1 + prosentti / 100), 2)


def _muotoile_lista(halytykset: list[Halytys]) -> str:
    """Muotoilee hälytykset listanäkymää varten."""
    if not halytykset:
        return "[HALYTYKSET] Ei aktiivisia hälytyksiä.\n\nAseta hälytys:\n/halytys <OSAKE> <+/->PROSENTTI%\nEsim: /halytys NOKIA -5%"

    rivit = ["[HALYTYKSET] Aktiiviset hälytykset\n"]
    for i, h in enumerate(halytykset, start=1):
        suunta = f"lasku -{h['prosentti']:.0f}%" if h["tyyppi"] == "lasku" else f"nousu +{h['prosentti']:.0f}%"
        rivit.append(f"{i}. {h['nimi']}  {suunta}  (asetettu: {h['hinta_luontihetkella']:.2f} EUR)")

    rivit.append("\nKomennot:")
    rivit.append("/halytys <OSAKE> <+/->PROSENTTI%")
    rivit.append("/halytys poista <OSAKE>")
    return "\n".join(rivit)


async def halytys_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /halytys-komennon käsittelijä.

    Alikomennot:
        /halytys NOKIA -5%      — aseta hälytys laskuun
        /halytys NOKIA +5%      — aseta hälytys nousuun
        /halytys lista          — näytä aktiiviset hälytykset
        /halytys poista NOKIA   — poista hälytys
    """
    user = update.effective_user
    if user is None:
        return

    user_id = user.id

    if not is_allowed(user_id):
        logger.warning(f"Whitelist-esto /halytys: {user_id} (@{user.username})")
        return

    args = context.args or []

    # --- /halytys (ilman argumentteja) tai /halytys lista ---
    if not args or args[0].lower() == "lista":
        kayttajan_halytykset: list[Halytys] = get_storage().list_alerts(user_id)
        await update.message.reply_text(_muotoile_lista(kayttajan_halytykset))
        return

    # --- /halytys poista <OSAKE> ---
    if args[0].lower() == "poista":
        if len(args) < 2:
            await update.message.reply_text(
                "[VIRHE] Puuttuva osake.\n\nKaytto: /halytys poista <OSAKE>\nEsim: /halytys poista NOKIA"
            )
            return

        poistettava_nimi = args[1].upper().strip()
        poistettu = get_storage().remove_alert(user_id, poistettava_nimi)
        if poistettu <= 0:
            await update.message.reply_text(
                f"[VIRHE] Hälytystä ei löydy: {poistettava_nimi}\n\nTarkista aktiiviset hälytykset: /halytys lista"
            )
            return

        await update.message.reply_text(
            f"[VALMIS] Hälytys poistettu: {poistettava_nimi}\n\nAktiiviset hälytykset: /halytys lista"
        )
        return

    # --- /halytys <OSAKE> <+/->PROSENTTI% ---
    if len(args) < 2:
        await update.message.reply_text(
            "[VIRHE] Puuttuva prosentti.\n\nKaytto: /halytys <OSAKE> <+/->PROSENTTI%\nEsim: /halytys NOKIA -5%"
        )
        return

    raw_nimi = args[0].upper().strip()
    raw_prosentti = args[1].strip()

    # Parsi prosentti
    osuma = PROSENTTI_REGEX.match(raw_prosentti)
    if not osuma:
        await update.message.reply_text(
            f"[VIRHE] Virheellinen prosentti: {raw_prosentti!r}\n\n"
            "Kaytto: /halytys <OSAKE> <+/->PROSENTTI%\n"
            "Esim: /halytys NOKIA -5%  tai  /halytys NOKIA +3.5%"
        )
        return

    merkki = osuma.group(1)    # "+" tai "-"
    prosentti = float(osuma.group(2))
    tyyppi = "lasku" if merkki == "-" else "nousu"

    if prosentti <= 0:
        await update.message.reply_text("[VIRHE] Prosentti ei voi olla nolla.")
        return

    # Validoi ticker
    await update.message.reply_text(f"Tarkistetaan osake {raw_nimi}...")

    yf_ticker = validate_ticker(raw_nimi)
    if yf_ticker is None:
        await update.message.reply_text(
            f"[VIRHE] Osaketta ei löydy: {raw_nimi}\n\n"
            "Tarkista tunnus. Tuetut osakkeet: NOKIA, NORDEA, NESTE, KONE, UPM..."
        )
        return

    # Hae nykyinen hinta
    hinta = get_current_price(yf_ticker)
    if hinta is None or hinta <= 0:
        await update.message.reply_text(
            f"[VIRHE] Kurssin haku epäonnistui: {raw_nimi}\n\nYritä myöhemmin uudelleen."
        )
        return

    # Tarkista käyttäjän hälytysraja
    kayttajan_halytykset = get_storage().list_alerts(user_id)

    on_paivitys = any(h["nimi"] == raw_nimi or h["ticker"] == yf_ticker for h in kayttajan_halytykset)
    if not on_paivitys and len(kayttajan_halytykset) >= MAX_HALYTYKSET_PER_KAYTTAJA:
        await update.message.reply_text(
            f"[VIRHE] Hälytysraja ({MAX_HALYTYKSET_PER_KAYTTAJA}) saavutettu.\n\n"
            "Poista ensin vanha hälytys: /halytys poista <OSAKE>"
        )
        return

    uusi: Halytys = {
        "ticker": yf_ticker,
        "nimi": raw_nimi,
        "tyyppi": tyyppi,
        "prosentti": prosentti,
        "hinta_luontihetkella": hinta,
        "luotu": date.today().isoformat(),
    }
    get_storage().upsert_alert(user_id, uusi)

    halytysraja = _laske_halytysraja(hinta, tyyppi, prosentti)
    suunta_teksti = f"laskee {prosentti:.0f}%" if tyyppi == "lasku" else f"nousee {prosentti:.0f}%"

    vastaus = (
        f"[VALMIS] Halytys asetettu\n\n"
        f"{raw_nimi}: halytys laukeaa kun kurssi {suunta_teksti}\n"
        f"Nykyinen kurssi: {hinta:.2f} EUR\n"
        f"Halytysraja: {halytysraja:.2f} EUR\n\n"
        f"Tarkistus: /halytys lista"
    )
    await update.message.reply_text(vastaus)
