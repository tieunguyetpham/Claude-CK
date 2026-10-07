"""Kiểm thử đầu vào: mã người dùng nhập và dữ liệu giá bất thường. Chạy: python -m pytest -q"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from analysis import analyze  # noqa: E402
from indicators import add_indicators, rsi, support_resistance  # noqa: E402
from symbols import BANKS, DEFAULT_SYMBOLS, VN50_FALLBACK, parse_symbols  # noqa: E402


# ------------------------------------------------------------ mã người dùng nhập
@pytest.mark.parametrize(
    "selected, typed, valid, invalid",
    [
        ([], "", [], []),
        (None, None, [], []),
        ([], "   ", [], []),
        ([], "vcb", ["VCB"], []),
        ([], " tcb , mwg ", ["TCB", "MWG"], []),
        ([], "TCB;MWG FPT\tHPG\nVNM", ["TCB", "MWG", "FPT", "HPG", "VNM"], []),
        ([], "vcb,VCB, Vcb", ["VCB"], []),
        (["VCB"], "vcb", ["VCB"], []),
        ([], ",,,;;", [], []),
        ([], "AB", [], ["AB"]),
        ([], "@@, $$$", [], ["@@", "$$$"]),
        ([], "VCB-X", [], ["VCB-X"]),
        ([], "ĐCM", [], ["ĐCM"]),
        ([], "E1VFVN30", ["E1VFVN30"], []),
        ([], "A" * 50, [], ["A" * 20]),
        ([], "<script>", [], ["<SCRIPT>"]),
        ([], "zz1, zz1", ["ZZ1"], []),
    ],
)
def test_parse_symbols(selected, typed, valid, invalid):
    assert parse_symbols(selected, typed) == (valid, invalid)


def test_symbol_lists():
    assert len(VN50_FALLBACK) == 50 and len(set(VN50_FALLBACK)) == 50
    assert len(set(BANKS)) == len(BANKS)
    for s in VN50_FALLBACK + BANKS:
        assert parse_symbols([], s) == ([s], [])
    # mã mặc định luôn có trong danh sách dự phòng (multiselect báo lỗi nếu default không thuộc options)
    assert set(DEFAULT_SYMBOLS) <= set(VN50_FALLBACK) | set(BANKS)


# ------------------------------------------------------------ dữ liệu giá bất thường
def make_df(closes, volume=1000.0):
    closes = np.asarray(closes, dtype=float)
    idx = pd.bdate_range("2025-01-01", periods=len(closes))
    return pd.DataFrame(
        {"open": closes, "high": closes * 1.01, "low": closes * 0.99, "close": closes, "volume": volume},
        index=idx,
    )


@pytest.mark.parametrize(
    "closes",
    [
        [10.0],                                   # mã mới niêm yết: 1 phiên
        [10.0, 10.5],                             # 2 phiên
        np.linspace(10, 12, 30),                  # chưa đủ dữ liệu MA50/MA200
        [10.0] * 300,                             # giá đứng yên
        np.linspace(10, 50, 300),                 # chỉ tăng
        np.linspace(50, 10, 300),                 # chỉ giảm
        10 + np.sin(np.arange(300) / 5),          # dao động
    ],
)
def test_analyze_never_crashes(closes):
    df = add_indicators(make_df(closes))
    res = analyze("VCB", df)
    assert res["recommendation"] in {"MUA", "GIỮ", "BÁN"}
    assert -res["max_score"] <= res["score"] <= res["max_score"]
    assert support_resistance(df)


def test_rsi_edge_cases():
    assert rsi(pd.Series([10.0] * 40)).iloc[-1] == 50.0
    assert rsi(pd.Series(np.linspace(10, 20, 40))).iloc[-1] == 100.0
    assert rsi(pd.Series(np.linspace(20, 10, 40))).iloc[-1] == pytest.approx(0.0)
    values = rsi(pd.Series(10 + np.sin(np.arange(200) / 3))).dropna()
    assert ((values >= 0) & (values <= 100)).all()


def test_zero_volume_does_not_crash():
    df = add_indicators(make_df(np.linspace(10, 12, 60), volume=0.0))
    assert analyze("FPT", df)["recommendation"] in {"MUA", "GIỮ", "BÁN"}
