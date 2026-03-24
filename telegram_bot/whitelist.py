import os
import logging

logger = logging.getLogger(__name__)


def load_whitelist() -> set[int]:
    """Lataa sallitut Telegram-käyttäjä-ID:t TELEGRAM_WHITELIST-muuttujasta."""
    raw = os.getenv("TELEGRAM_WHITELIST", "")
    if not raw.strip():
        return set()
    ids = set()
    for part in raw.split(","):
        part = part.strip()
        if part:
            try:
                ids.add(int(part))
            except ValueError:
                logger.warning(f"Virheellinen käyttäjä-ID whitelistissä: {part!r}")
    return ids


def is_allowed(user_id: int) -> bool:
    """Tarkistaa onko käyttäjä sallitulla whitelistillä."""
    whitelist = load_whitelist()
    allowed = user_id in whitelist
    if not allowed:
        logger.warning(f"Whitelist-esto: käyttäjä {user_id}")
    return allowed
