"""Nasdaq Helsingin kaupankäyntipäivien tarkistus."""

from __future__ import annotations

from datetime import date, timedelta


def _easter_sunday(year: int) -> date:
    """Laske pääsiäissunnuntai gregoriaanisella algoritmilla."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def nasdaq_helsinki_holidays(year: int) -> set[date]:
    """Palauta yleiset Nasdaq Helsingin pörssipyhät."""
    easter = _easter_sunday(year)
    fixed = {
        date(year, 1, 1),
        date(year, 1, 6),
        date(year, 5, 1),
        date(year, 12, 6),
        date(year, 12, 24),
        date(year, 12, 25),
        date(year, 12, 26),
    }
    movable = {
        easter - timedelta(days=2),  # pitkäperjantai
        easter + timedelta(days=1),  # toinen pääsiäispäivä
        easter + timedelta(days=39),  # helatorstai
    }

    midsummer_eve = next(
        day
        for day in (date(year, 6, candidate) for candidate in range(19, 26))
        if day.weekday() == 4
    )
    movable.add(midsummer_eve)
    return fixed | movable


def is_trading_day(day: date) -> bool:
    """Tarkista onko päivä Nasdaq Helsingin kaupankäyntipäivä."""
    if day.weekday() >= 5:
        return False
    return day not in nasdaq_helsinki_holidays(day.year)
