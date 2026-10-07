"""Lấy dữ liệu trực tiếp từ API công khai của SSI iBoard.

- Lịch sử giá OHLCV: giá trả về theo đơn vị NGHÌN ĐỒNG.
- Báo giá realtime: giá trả về theo ĐỒNG -> chia 1000 để thống nhất nghìn đồng.
Mọi hàm đều không ném lỗi ra ngoài: trả về (dữ liệu, None) hoặc (None, "thông báo lỗi").
"""

import time

import pandas as pd
import requests

HISTORY_URL = "https://iboard-api.ssi.com.vn/statistics/charts/history"
QUOTE_URL = "https://iboard-query.ssi.com.vn/stock/{symbol}"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "application/json",
}
TIMEOUT = 15
RETRIES = 2

_session = requests.Session()
_session.headers.update(HEADERS)


def _get_json(url: str, params: dict | None = None) -> dict:
    """GET có thử lại khi lỗi mạng/timeout. Ném RuntimeError nếu vẫn thất bại."""
    last_err = None
    for attempt in range(RETRIES + 1):
        try:
            resp = _session.get(url, params=params, timeout=TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except (requests.RequestException, ValueError) as e:
            last_err = e
            if attempt < RETRIES:
                time.sleep(0.8 * (attempt + 1))
    raise RuntimeError(f"Không kết nối được máy chủ dữ liệu ({last_err.__class__.__name__})")


def fetch_history(symbol: str, days: int = 1100) -> tuple[pd.DataFrame | None, str | None]:
    """Lịch sử nến ngày. Trả DataFrame index=ngày, cột open/high/low/close/volume (nghìn đồng)."""
    to_ts = int(time.time())
    from_ts = to_ts - days * 86400
    params = {"resolution": "1D", "symbol": symbol, "from": from_ts, "to": to_ts}
    try:
        payload = _get_json(HISTORY_URL, params)
    except RuntimeError as e:
        return None, str(e)

    data = (payload or {}).get("data") or {}
    times = data.get("t") or []
    if not times:
        return None, f"Không tìm thấy dữ liệu cho mã {symbol}"

    try:
        df = pd.DataFrame(
            {
                "open": data["o"],
                "high": data["h"],
                "low": data["l"],
                "close": data["c"],
                "volume": data["v"],
            },
            index=pd.to_datetime(times, unit="s", utc=True)
            .tz_convert("Asia/Ho_Chi_Minh")
            .tz_localize(None)
            .normalize(),
        )
    except (KeyError, ValueError) as e:
        return None, f"Dữ liệu mã {symbol} không hợp lệ ({e.__class__.__name__})"

    df = df.apply(pd.to_numeric, errors="coerce").dropna(subset=["close"])
    df = df[~df.index.duplicated(keep="last")].sort_index()
    df.index.name = "date"
    if df.empty:
        return None, f"Không tìm thấy dữ liệu cho mã {symbol}"
    return df, None


def _format_date(raw) -> str:
    """'20261007' -> '07/10/2026'; giữ nguyên nếu không đúng định dạng."""
    s = str(raw or "")
    if len(s) == 8 and s.isdigit():
        return f"{s[6:8]}/{s[4:6]}/{s[0:4]}"
    return s


def fetch_quote(symbol: str) -> tuple[dict | None, str | None]:
    """Báo giá realtime + thông tin cơ bản. Giá quy về nghìn đồng."""
    try:
        payload = _get_json(QUOTE_URL.format(symbol=symbol))
    except RuntimeError as e:
        return None, str(e)

    d = (payload or {}).get("data")
    if not d:
        return None, f"Không tìm thấy mã {symbol}"

    def num(key):
        v = d.get(key)
        try:
            return float(v) if v not in (None, "") else None
        except (TypeError, ValueError):
            return None

    ref = num("refPrice") or num("priorClosePrice")
    price = num("matchedPrice") or ref  # ngoài giờ giao dịch có thể chưa khớp lệnh
    change = num("priceChange")
    change_pct = num("priceChangePercent")
    if price and ref and (change is None or change_pct is None):
        change = price - ref
        change_pct = change / ref * 100

    listed = num("listedShare")
    quote = {
        "symbol": symbol,
        "name": d.get("companyNameVi") or d.get("companyNameEn") or symbol,
        "exchange": (d.get("exchange") or "").upper(),
        "price": price / 1000 if price else None,
        "ref": ref / 1000 if ref else None,
        "change": change / 1000 if change is not None else None,
        "change_pct": change_pct,
        "open": (num("openPrice") or 0) / 1000 or None,
        "high": (num("highest") or 0) / 1000 or None,
        "low": (num("lowest") or 0) / 1000 or None,
        "volume": num("nmTotalTradedQty"),
        # vốn hóa (tỷ đồng) = số CP niêm yết x giá (đồng) / 1e9
        # SSI trả listedShare = 0 với một số mã -> để None, giao diện hiện "—"
        "market_cap": listed * price / 1e9 if listed and price else None,
        "trading_date": _format_date(d.get("tradingDate")),
    }
    return quote, None
