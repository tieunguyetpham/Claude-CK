"""Kiểm thử logic tín hiệu: giao cắt gần nhất, Stochastic. Chạy: python -m pytest -q"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from analysis import _crossed, analyze  # noqa: E402
from indicators import add_indicators  # noqa: E402

B = pd.Series([1.5] * 4)


@pytest.mark.parametrize(
    "a, expected",
    [
        ([1, 2, 1, 1], -1),   # cắt lên rồi cắt xuống -> lần gần nhất là cắt xuống
        ([2, 1, 2, 2], 1),    # cắt xuống rồi cắt lên -> lần gần nhất là cắt lên
        ([1, 1, 1, 2], 1),    # vừa cắt lên ở phiên cuối
        ([2, 2, 2, 1], -1),   # vừa cắt xuống ở phiên cuối
        ([2, 2, 2, 2], 0),    # không cắt
        ([1, 1, 1, 1], 0),
    ],
)
def test_crossed_reports_most_recent(a, expected):
    assert _crossed(pd.Series(a, dtype=float), B) == expected


def test_crossed_outside_lookback_ignored():
    a = pd.Series([1, 2, 2, 2, 2, 2], dtype=float)  # cắt lên cách đây 4 phiên
    assert _crossed(a, pd.Series([1.5] * 6), lookback=3) == 0


def stoch_df(k, d):
    """DataFrame tối thiểu để analyze chấm Stochastic (các chỉ báo khác để NaN)."""
    n = len(k)
    df = add_indicators(pd.DataFrame(
        {"open": 10.0, "high": 10.0, "low": 10.0, "close": 10.0, "volume": 1000.0},
        index=pd.bdate_range("2026-01-01", periods=n),
    ))
    for col in df.columns:
        if col not in ("open", "high", "low", "close", "volume"):
            df[col] = np.nan
    df["STOCH_K"], df["STOCH_D"] = k, d
    return df


def stoch_reason(df):
    return [(s, t) for s, t in analyze("FPT", df)["reasons"] if "Stochastic" in t][0]


def test_stochastic_buy_only_on_actual_cross():
    # %K vừa cắt lên %D trong vùng quá bán -> +1
    assert stoch_reason(stoch_df([10, 12], [15, 11]))[0] == 1
    # %K đã nằm trên %D từ trước (không có giao cắt) -> không được chấm "cắt lên"
    score, text = stoch_reason(stoch_df([12, 13, 14, 15], [10, 11, 12, 13]))
    assert score == 0 and "cắt" not in text


def test_stochastic_sell_only_on_actual_cross():
    assert stoch_reason(stoch_df([90, 85], [86, 88]))[0] == -1
    score, text = stoch_reason(stoch_df([88, 87, 86, 85], [90, 89, 88, 87]))
    assert score == 0 and "cắt" not in text
