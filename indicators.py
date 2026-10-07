"""Chỉ báo phân tích kỹ thuật, tính bằng pandas/numpy thuần (không phụ thuộc thư viện ngoài)."""

import numpy as np
import pandas as pd


def _wilder(series: pd.Series, n: int) -> pd.Series:
    """Trung bình trượt kiểu Wilder (dùng cho RSI, ATR, ADX)."""
    return series.ewm(alpha=1 / n, min_periods=n, adjust=False).mean()


def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    delta = close.diff()
    avg_gain = _wilder(delta.clip(lower=0), n)
    avg_loss = _wilder(-delta.clip(upper=0), n)
    rs = avg_gain / avg_loss.replace(0, np.nan)
    out = 100 - 100 / (1 + rs)
    no_loss = avg_loss == 0
    out = out.mask(no_loss & (avg_gain > 0), 100.0)  # chỉ có phiên tăng -> 100
    return out.mask(no_loss & (avg_gain == 0), 50.0)  # giá đứng yên -> trung tính


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    line = close.ewm(span=fast, adjust=False).mean() - close.ewm(span=slow, adjust=False).mean()
    sig = line.ewm(span=signal, adjust=False).mean()
    return line, sig, line - sig


def bollinger(close: pd.Series, n: int = 20, k: float = 2.0):
    mid = close.rolling(n).mean()
    std = close.rolling(n).std(ddof=0)
    return mid + k * std, mid, mid - k * std


def stochastic(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 14, d: int = 3):
    lowest = low.rolling(n).min()
    highest = high.rolling(n).max()
    k = 100 * (close - lowest) / (highest - lowest).replace(0, np.nan)
    return k, k.rolling(d).mean()


def adx(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 14):
    up = high.diff()
    down = -low.diff()
    plus_dm = pd.Series(np.where((up > down) & (up > 0), up, 0.0), index=high.index)
    minus_dm = pd.Series(np.where((down > up) & (down > 0), down, 0.0), index=high.index)
    prev_close = close.shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    atr = _wilder(tr, n).replace(0, np.nan)
    plus_di = 100 * _wilder(plus_dm, n) / atr
    minus_di = 100 * _wilder(minus_dm, n) / atr
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return _wilder(dx, n), plus_di, minus_di


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Trả về bản sao df có thêm toàn bộ cột chỉ báo."""
    out = df.copy()
    c, h, l = out["close"], out["high"], out["low"]

    for n in (20, 50, 200):
        out[f"MA{n}"] = c.rolling(n).mean()
    out["EMA20"] = c.ewm(span=20, adjust=False).mean()
    out["RSI"] = rsi(c)
    out["MACD"], out["MACD_signal"], out["MACD_hist"] = macd(c)
    out["BB_upper"], out["BB_mid"], out["BB_lower"] = bollinger(c)
    out["STOCH_K"], out["STOCH_D"] = stochastic(h, l, c)
    out["ADX"], out["DI_plus"], out["DI_minus"] = adx(h, l, c)
    out["VOL_MA20"] = out["volume"].rolling(20).mean()
    return out


def support_resistance(df: pd.DataFrame, windows=(20, 60)) -> dict:
    """Hỗ trợ/kháng cự đơn giản: đáy thấp nhất / đỉnh cao nhất trong N phiên gần nhất."""
    levels = {}
    for n in windows:
        recent = df.tail(n)
        if len(recent):
            levels[n] = (float(recent["low"].min()), float(recent["high"].max()))
    return levels
