"""
LLM-vastausten SQLite-välimuisti (kehitys- ja testikäyttöön).
=============================================================
Permanent file-based cache keyed by SHA-256(llm_string + prompt).
Käyttää langchain-core:n omaa serialisointia (dumps/loads) joten
ChatGeneration-objektit toimivat oikein.

Ei ulkoisia riippuvuuksia — sqlite3 on standardikirjastossa,
langchain-core on jo asennettu.

Käyttö:
    from tradingagents.llm_cache import setup_llm_cache
    setup_llm_cache()   # kutsutaan kerran sovelluksen alussa

FORK: Suomi-lokalisointi — uusi tiedosto
"""
from __future__ import annotations

import hashlib
import logging
import sqlite3
from pathlib import Path
from typing import Optional, Sequence

from langchain_core.caches import BaseCache
from langchain_core.globals import set_llm_cache
from langchain_core.load import dumps, loads
from langchain_core.outputs import Generation

logger = logging.getLogger(__name__)

_DEFAULT_DB = ".llm_cache.db"


class SQLiteLLMCache(BaseCache):
    """
    Pysyvä tiedostopohjainen LLM-välimuisti kehityskäyttöön.

    Sama osake, sama päivä → toinen kutsu palauttaa välimuistista
    eikä maksa uusia API-kuluja.

    Välimuisti ei vanhene automaattisesti — tyhjennä manuaalisesti
    kun haluat pakottaa tuoreet LLM-vastaukset:
        python -c "from tradingagents.llm_cache import get_cache; get_cache().clear()"
    """

    def __init__(self, db_path: str = _DEFAULT_DB) -> None:
        self._db_path = str(Path(db_path).resolve())
        self._init_db()
        logger.info("LLM-välimuisti: %s", self._db_path)

    # ── sisäiset apumetodit ──────────────────────────────────────────────

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path, check_same_thread=False)

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS llm_cache (
                    cache_key  TEXT PRIMARY KEY,
                    payload    TEXT NOT NULL,
                    created_at INTEGER DEFAULT (strftime('%s','now'))
                )
            """)

    @staticmethod
    def _make_key(prompt: str, llm_string: str) -> str:
        return hashlib.sha256(
            f"{llm_string}\x00{prompt}".encode("utf-8")
        ).hexdigest()

    # ── BaseCache-rajapinta ──────────────────────────────────────────────

    def lookup(
        self, prompt: str, llm_string: str
    ) -> Optional[list[Generation]]:
        key = self._make_key(prompt, llm_string)
        with self._conn() as conn:
            row = conn.execute(
                "SELECT payload FROM llm_cache WHERE cache_key = ?", (key,)
            ).fetchone()
        if row is None:
            return None
        try:
            result = loads(row[0])
            logger.debug("LLM cache HIT  %.8s…", key)
            return result
        except Exception as exc:
            logger.warning("Välimuistin purku epäonnistui: %s", exc)
            return None

    def update(
        self,
        prompt: str,
        llm_string: str,
        return_val: Sequence[Generation],
    ) -> None:
        key = self._make_key(prompt, llm_string)
        try:
            payload = dumps(list(return_val))
            with self._conn() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO llm_cache (cache_key, payload) VALUES (?, ?)",
                    (key, payload),
                )
        except Exception as exc:
            logger.warning("Välimuistiin kirjoitus epäonnistui: %s", exc)

    def clear(self, **kwargs) -> None:  # type: ignore[override]
        with self._conn() as conn:
            conn.execute("DELETE FROM llm_cache")
        logger.info("LLM-välimuisti tyhjennetty.")

    # ── apufunktio tilastoille ───────────────────────────────────────────

    def stats(self) -> dict:
        with self._conn() as conn:
            count: int = conn.execute(
                "SELECT COUNT(*) FROM llm_cache"
            ).fetchone()[0]
        size_bytes = Path(self._db_path).stat().st_size
        return {"entries": count, "size_mb": round(size_bytes / 1024 / 1024, 2)}


# Moduulitason singleton — asetetaan setup_llm_cache():lla
_cache_instance: Optional[SQLiteLLMCache] = None


def setup_llm_cache(db_path: str = _DEFAULT_DB) -> SQLiteLLMCache:
    """
    Aktivoi globaalin LLM-välimuistin.
    Kutsu kerran sovelluksen käynnistyksessä (bot.py tai main.py).
    """
    global _cache_instance
    _cache_instance = SQLiteLLMCache(db_path)
    set_llm_cache(_cache_instance)
    s = _cache_instance.stats()
    logger.info(
        "LLM-välimuisti aktiivinen — %d tallennettua vastausta (%.1f MB)",
        s["entries"],
        s["size_mb"],
    )
    return _cache_instance


def get_cache() -> Optional[SQLiteLLMCache]:
    """Palauttaa aktiivisen cache-instanssin tai None."""
    return _cache_instance
