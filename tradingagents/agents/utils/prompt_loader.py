"""
Suomenkielisten agenttipromptien lataaja.
Lukee fi_prompts/-kansion .md-tiedostot.

FORK: Suomi-lokalisointi — uusi tiedosto
"""
from __future__ import annotations
from pathlib import Path

# fi_prompts/ sijaitsee projektin juuressa (4 tasoa ylöspäin tästä tiedostosta)
_FI_PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "fi_prompts"


def load_fi_prompt(name: str) -> str:
    """
    Lataa suomenkielisen system-promptin fi_prompts/<name>.md -tiedostosta.
    Palauttaa tyhjän merkkijonon jos tiedostoa ei löydy.
    """
    path = _FI_PROMPTS_DIR / f"{name}.md"
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return ""
