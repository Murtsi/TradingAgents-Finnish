import pytest
from telegram_bot.formatter import format_summary, format_full_report, parse_decision

MOCK_STATE = {
    "company_of_interest": "NOKIA.HE",
    "trade_date": "2026-03-24",
    "final_trade_decision": "BUY - Nokia on aliarvostettu. Luottamustaso: Korkea.",
    "market_report": "Tekninen analyysi: RSI 45, trendi nouseva...",
    "sentiment_report": "Sentimentti positiivinen Kauppalehdessä...",
    "news_report": "Nokia voitti 5G-sopimuksen...",
    "fundamentals_report": "P/E 12, EV/EBITDA 8...",
    "trader_investment_plan": "Suositus: OSTA. Hintatavoite 5,00 €.",
    "investment_plan": "Riskiarvio: Kohtuullinen.",
}

def test_parse_decision_buy():
    assert parse_decision("BUY - perustelut") == "OSTA"

def test_parse_decision_sell():
    assert parse_decision("SELL - perustelut") == "MYY"

def test_parse_decision_hold():
    assert parse_decision("HOLD - perustelut") == "PIDÄ"

def test_parse_decision_case_insensitive():
    assert parse_decision("buy - lowercase") == "OSTA"

def test_format_summary_contains_ticker():
    summary = format_summary(MOCK_STATE, current_price=4.23)
    assert "NOKIA" in summary

def test_format_summary_contains_suositus():
    summary = format_summary(MOCK_STATE, current_price=4.23)
    assert "OSTA" in summary

def test_format_summary_contains_disclaimer():
    summary = format_summary(MOCK_STATE, current_price=4.23)
    assert "sijoitussuositus" in summary.lower()

def test_format_summary_contains_price():
    summary = format_summary(MOCK_STATE, current_price=4.23)
    assert "4,23" in summary

def test_format_full_report_contains_all_sections():
    report = format_full_report(MOCK_STATE)
    assert "Tekninen" in report
    assert "Sentimentti" in report
    assert "Fundamentti" in report
