import pytest
from telegram_bot.whitelist import load_whitelist, is_allowed

def test_load_whitelist_parses_ids(monkeypatch):
    monkeypatch.setenv("TELEGRAM_WHITELIST", "111,222,333")
    assert load_whitelist() == {111, 222, 333}

def test_load_whitelist_empty_env(monkeypatch):
    monkeypatch.setenv("TELEGRAM_WHITELIST", "")
    assert load_whitelist() == set()

def test_load_whitelist_missing_env(monkeypatch):
    monkeypatch.delenv("TELEGRAM_WHITELIST", raising=False)
    assert load_whitelist() == set()

def test_load_whitelist_strips_spaces(monkeypatch):
    monkeypatch.setenv("TELEGRAM_WHITELIST", " 111 , 222 ")
    assert load_whitelist() == {111, 222}

def test_is_allowed_true(monkeypatch):
    monkeypatch.setenv("TELEGRAM_WHITELIST", "42")
    assert is_allowed(42) is True

def test_is_allowed_false(monkeypatch):
    monkeypatch.setenv("TELEGRAM_WHITELIST", "42")
    assert is_allowed(99) is False
