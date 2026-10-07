"""Tổng hợp tín hiệu kỹ thuật thành điểm số và nhận định MUA / GIỮ / BÁN (chỉ mang tính tham khảo)."""

import math

import pandas as pd

from symbols import is_bank

BUY_THRESHOLD = 3
SELL_THRESHOLD = -3


def _ok(*values) -> bool:
    return all(v is not None and not (isinstance(v, float) and math.isnan(v)) for v in values)


def _crossed(a: pd.Series, b: pd.Series, lookback: int = 3) -> int:
    """Hướng của lần giao cắt GẦN NHẤT trong `lookback` phiên: +1 cắt lên, -1 cắt xuống, 0 nếu không cắt."""
    diff = (a - b).dropna().tail(lookback + 1)
    signs = [1 if x > 0 else -1 for x in diff]
    # duyệt từ phiên mới nhất về trước: cắt lên rồi cắt xuống thì tín hiệu hiện tại là cắt xuống
    for i in range(len(signs) - 1, 0, -1):
        if signs[i] != signs[i - 1]:
            return signs[i]
    return 0


def analyze(symbol: str, df: pd.DataFrame) -> dict:
    """df phải có các cột chỉ báo từ indicators.add_indicators."""
    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else last
    close = float(last["close"])
    reasons = []  # (điểm, mô tả)

    def add(score: int, text: str):
        reasons.append((score, text))

    # 1. Xu hướng theo đường trung bình
    ma20, ma50, ma200 = last["MA20"], last["MA50"], last["MA200"]
    if _ok(ma50):
        if close > ma50:
            add(1, f"Giá ({close:,.2f}) nằm trên MA50 ({ma50:,.2f}) → xu hướng trung hạn tăng")
        else:
            add(-1, f"Giá ({close:,.2f}) nằm dưới MA50 ({ma50:,.2f}) → xu hướng trung hạn giảm")
    if _ok(ma20, ma50):
        cross = _crossed(df["MA20"], df["MA50"])
        if cross == 1:
            add(1, "MA20 vừa cắt lên MA50 → tín hiệu tăng ngắn hạn")
        elif cross == -1:
            add(-1, "MA20 vừa cắt xuống MA50 → tín hiệu giảm ngắn hạn")
        elif ma20 > ma50:
            add(1, "MA20 trên MA50 → động lượng ngắn hạn tích cực")
        else:
            add(-1, "MA20 dưới MA50 → động lượng ngắn hạn tiêu cực")
    if _ok(ma200):
        if close > ma200:
            add(1, f"Giá trên MA200 ({ma200:,.2f}) → xu hướng dài hạn tăng")
        else:
            add(-1, f"Giá dưới MA200 ({ma200:,.2f}) → xu hướng dài hạn giảm")

    # 2. RSI
    r = last["RSI"]
    if _ok(r):
        if r < 30:
            add(1, f"RSI = {r:.1f} → vùng quá bán, khả năng hồi phục")
        elif r > 70:
            add(-1, f"RSI = {r:.1f} → vùng quá mua, rủi ro điều chỉnh")
        else:
            add(0, f"RSI = {r:.1f} → trung tính")

    # 3. MACD
    if _ok(last["MACD"], last["MACD_signal"]):
        cross = _crossed(df["MACD"], df["MACD_signal"])
        if cross == 1:
            add(1, "MACD vừa cắt lên đường tín hiệu → tín hiệu mua")
        elif cross == -1:
            add(-1, "MACD vừa cắt xuống đường tín hiệu → suy yếu")
        elif last["MACD"] > last["MACD_signal"]:
            add(1, "MACD trên đường tín hiệu → động lượng tăng")
        else:
            add(-1, "MACD dưới đường tín hiệu → động lượng giảm")

    # 4. Bollinger Bands
    if _ok(last["BB_upper"], last["BB_lower"]):
        if close < last["BB_lower"]:
            add(1, "Giá thủng dải Bollinger dưới → quá bán, có thể bật lại")
        elif close > last["BB_upper"]:
            add(-1, "Giá vượt dải Bollinger trên → quá mua, dễ rung lắc")
        else:
            add(0, "Giá nằm trong dải Bollinger → biến động bình thường")

    # 5. Stochastic
    k, d = last["STOCH_K"], last["STOCH_D"]
    if _ok(k, d):
        cross = _crossed(df["STOCH_K"], df["STOCH_D"], lookback=2)  # chỉ tính giao cắt thật, không phải vị trí
        if k < 20 and cross == 1:
            add(1, f"Stochastic %K = {k:.0f} vùng quá bán và vừa cắt lên %D → tín hiệu mua")
        elif k > 80 and cross == -1:
            add(-1, f"Stochastic %K = {k:.0f} vùng quá mua và vừa cắt xuống %D → tín hiệu bán")
        elif k < 20:
            add(0, f"Stochastic %K = {k:.0f} vùng quá bán, chưa có tín hiệu đảo chiều")
        elif k > 80:
            add(0, f"Stochastic %K = {k:.0f} vùng quá mua, chưa có tín hiệu đảo chiều")
        else:
            add(0, f"Stochastic %K = {k:.0f} → trung tính")

    # 6. Khối lượng xác nhận
    vol, vol_ma = last["volume"], last["VOL_MA20"]
    if _ok(vol, vol_ma) and vol_ma > 0 and vol > 1.5 * vol_ma:
        if close >= prev["close"]:
            add(1, f"Khối lượng đột biến ({vol / vol_ma:.1f}x TB20) kèm giá tăng → dòng tiền vào")
        else:
            add(-1, f"Khối lượng đột biến ({vol / vol_ma:.1f}x TB20) kèm giá giảm → áp lực bán")

    score = sum(s for s, _ in reasons)
    if score >= BUY_THRESHOLD:
        rec = "MUA"
    elif score <= SELL_THRESHOLD:
        rec = "BÁN"
    else:
        rec = "GIỮ"

    # ADX: đánh giá độ mạnh xu hướng (không cộng điểm)
    a = last["ADX"]
    if _ok(a):
        if a >= 25:
            trend_note = f"ADX = {a:.0f} → xu hướng hiện tại MẠNH, tín hiệu theo xu hướng đáng tin cậy hơn"
        else:
            trend_note = f"ADX = {a:.0f} → xu hướng YẾU / đi ngang, nên thận trọng với tín hiệu"
    else:
        trend_note = ""

    notes = []
    if is_bank(symbol):
        notes.append(
            "Cổ phiếu ngân hàng thường được định giá theo P/B và ROE; nhạy cảm với lãi suất, "
            "tăng trưởng tín dụng và nợ xấu — nên kết hợp thêm báo cáo tài chính quý."
        )

    return {
        "symbol": symbol,
        "score": score,
        "max_score": len(reasons),
        "recommendation": rec,
        "reasons": reasons,
        "trend_note": trend_note,
        "notes": notes,
    }
