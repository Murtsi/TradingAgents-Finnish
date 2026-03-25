"""
Hintahälytysten hallinta Telegram-botille.

Tallentaa hälytykset JSON-tiedostoon ~/.kauppaagentit/halytykset.json.
Tukee nousua (+%) ja laskua (-%) koskevia hälytyksiä OMXH-osakkeille.

FORK: Suomi-lokalisointi — uusi tiedosto
"""
from __future__ import annotations

import json
import logging
import re
from datetime import date
from pathlib import Path
from typing import TypedDict

from telegram import Update
from telegram.ext import ContextTypes

from telegram_bot.omxh import validate_ticker, get_current_price
from telegram_bot.whitelist import is_allowed
from tradingagents.dataflows.omxh_utils import resolve_ticker

logger = logging.getLogger(__name__)

# Maksimi hälytyksiä per käyttäjä
MAX_HALYTYKSET_PER_KAYTTAJA = 20

# Tallennuspolku
HALYTYKSET_HAKEMISTO = Path.home() / ".kauppaagentit"
HALYTYKSET_TIEDOSTO = HALYTYKSET_HAKEMISTO / "halytykset.json"

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
    """Lukee hälytykset JSON-tiedostosta. Palauttaa tyhjän dictin virhetilanteessa."""
    if not HALYTYKSET_TIEDOSTO.exists():
        return {}
    try:
        with open(HALYTYKSET_TIEDOSTO, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.error(f"Hälytysten lukeminen epäonnistui: {e}")
        return {}


def _tallenna_halytykset(data: dict[str, list[Halytys]]) -> bool:
    """Tallentaa hälytykset JSON-tiedostoon. Palauttaa True onnistuessa."""
    try:
        HALYTYKSET_HAKEMISTO.mkdir(parents=True, exist_ok=True)
        with open(HALYTYKSET_TIEDOSTO, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except OSError as e:
        logger.error(f"Hälytysten tallennus epäonnistui: {e}")
        return False


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
        data = _lue_halytykset()
        kayttajan_halytykset: list[Halytys] = data.get(str(user_id), [])
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
        data = _lue_halytykset()
        kayttajan_halytykset = data.get(str(user_id), [])

        alkuperainen_maara = len(kayttajan_halytykset)
        suodatettu = [h for h in kayttajan_halytykset if h["nimi"] != poistettava_nimi]

        if len(suodatettu) == alkuperainen_maara:
            await update.message.reply_text(
                f"[VIRHE] Hälytystä ei löydy: {poistettava_nimi}\n\nTarkista aktiiviset hälytykset: /halytys lista"
            )
            return

        data[str(user_id)] = suodatettu
        if _tallenna_halytykset(data):
            await update.message.reply_text(
                f"[VALMIS] Hälytys poistettu: {poistettava_nimi}\n\nAktiiviset hälytykset: /halytys lista"
            )
        else:
            await update.message.reply_text("[VIRHE] Tallennus epäonnistui. Yrita uudelleen.")
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
    data = _lue_halytykset()
    kayttajan_halytykset = data.get(str(user_id), [])

    if len(kayttajan_halytykset) >= MAX_HALYTYKSET_PER_KAYTTAJA:
        await update.message.reply_text(
            f"[VIRHE] Hälytysraja ({MAX_HALYTYKSET_PER_KAYTTAJA}) saavutettu.\n\n"
            "Poista ensin vanha hälytys: /halytys poista <OSAKE>"
        )
        return

    # Poista mahdollinen aiempi hälytys samalle osakkeelle (yksi per osake)
    kayttajan_halytykset = [h for h in kayttajan_halytykset if h["nimi"] != raw_nimi]

    uusi: Halytys = {
        "ticker": yf_ticker,
        "nimi": raw_nimi,
        "tyyppi": tyyppi,
        "prosentti": prosentti,
        "hinta_luontihetkella": hinta,
        "luotu": date.today().isoformat(),
    }
    kayttajan_halytykset.append(uusi)
    data[str(user_id)] = kayttajan_halytykset

    if not _tallenna_halytykset(data):
        await update.message.reply_text("[VIRHE] Tallennus epäonnistui. Yrita uudelleen.")
        return

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
