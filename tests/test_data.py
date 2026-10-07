"""Kiểm thử ghép báo giá realtime vào lịch sử giá. Chạy: python -m pytest -q"""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import data  # noqa: E402
from data import fetch_group, merge_quote  # noqa: E402


# ------------------------------------------------------------ thành phần rổ
def fake_rows(n):
    return {"data": [{"stockSymbol": f"A{i:02d}"} for i in range(n)]}


@pytest.mark.parametrize(
    "payload, ok",
    [
        (fake_rows(50), True),
        (fake_rows(5), False),                    # quá ít mã -> nghi API trả thiếu
        ({"data": None}, False),
        ({"data": "abc"}, False),
        ({}, False),
        (None, False),
    ],
)
def test_fetch_group_payloads(monkeypatch, payload, ok):
    monkeypatch.setattr(data, "_get_json", lambda *a, **k: payload)
    symbols, err = fetch_group("VN100")
    assert (symbols is not None) == ok
    assert (err is None) == ok


def test_fetch_group_cleans_symbols(monkeypatch):
    rows = fake_rows(25)["data"] + [{"stockSymbol": "acb"}, {"stockSymbol": "A00"}, {"stockSymbol": "<x>"},
                                    {"stockSymbol": None}, {}, "rác"]
    monkeypatch.setattr(data, "_get_json", lambda *a, **k: {"data": rows})
    symbols, err = fetch_group("VN100")
    assert err is None
    assert "ACB" in symbols and "<X>" not in symbols and "NONE" not in symbols
    assert symbols == sorted(set(symbols))


def test_fetch_group_network_error(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError(f"{data.NETWORK_ERROR} (ConnectionError)")

    monkeypatch.setattr(data, "_get_json", boom)
    symbols, err = fetch_group("VN100")
    assert symbols is None and err.startswith(data.NETWORK_ERROR)


# ------------------------------------------------------------ ghép báo giá realtime


def history():
    idx = pd.to_datetime(["2026-10-05", "2026-10-06"])
    return pd.DataFrame(
        {"open": [10.0, 10.2], "high": [10.5, 10.6], "low": [9.8, 10.0], "close": [10.2, 10.4], "volume": [1000.0, 1200.0]},
        index=idx,
    )


def quote(**kw):
    q = {"price": 10.8, "open": 10.5, "high": 10.9, "low": 10.4, "volume": 500.0, "trading_date": "07/10/2026"}
    q.update(kw)
    return q


def test_append_new_session():
    out = merge_quote(history(), quote())
    assert len(out) == 3
    assert out.index[-1] == pd.Timestamp("2026-10-07")
    assert out.iloc[-1].tolist() == [10.5, 10.9, 10.4, 10.8, 500.0]
    assert out.index.is_monotonic_increasing


def test_update_same_session():
    out = merge_quote(history(), quote(trading_date="06/10/2026", price=10.7, high=10.75))
    assert len(out) == 2
    assert out.loc["2026-10-06", "close"] == 10.7
    assert out.loc["2026-10-06", "high"] == 10.75


def test_high_low_cover_price():
    out = merge_quote(history(), quote(price=11.5, high=None, low=None))
    last = out.iloc[-1]
    assert last["high"] >= last["close"] >= last["low"]


def test_original_not_modified():
    df = history()
    merge_quote(df, quote())
    assert len(df) == 2


def test_skip_cases():
    df = history()
    for q in (
        None,
        {},
        quote(volume=0),            # chưa khớp lệnh
        quote(volume=None),
        quote(price=None),
        quote(trading_date="01/10/2026"),  # báo giá cũ hơn lịch sử
        quote(trading_date=""),
        quote(trading_date="2026-10-07"),  # sai định dạng
    ):
        assert merge_quote(df, q).equals(df)


def test_empty_history():
    assert merge_quote(pd.DataFrame(), quote()).empty
    assert merge_quote(None, quote()) is None
