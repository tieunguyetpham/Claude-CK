"""Dashboard phân tích kỹ thuật cổ phiếu VN100 & Ngân hàng. Chạy: streamlit run app.py"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from analysis import analyze
from data import NETWORK_ERROR, fetch_group, fetch_history, fetch_quote, merge_quote
from indicators import add_indicators, support_resistance
from symbols import (BANKS, BASKET_FALLBACK, BASKET_GROUP, BASKET_MIN_SIZE, DEFAULT_SYMBOLS, is_bank,
                     parse_symbols)

APP_NAME = f"{BASKET_GROUP} & Ngân hàng"
st.set_page_config(page_title=f"Phân tích CK {APP_NAME}", page_icon="📈", layout="wide")

VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
CACHE_TTL = 300  # giây: dữ liệu tự làm mới sau 5 phút
BASKET_TTL = 6 * 3600  # thành phần rổ ít thay đổi
MAX_CACHE_ENTRIES = 64  # giới hạn RAM: mỗi mục (≤10 mã) khoảng 1–2 MB
MAX_SYMBOLS = 10
PERIODS = {"3 tháng": 90, "6 tháng": 180, "1 năm": 365, "2 năm": 730}
DISCLAIMER = (
    "⚠️ Thông tin chỉ mang tính tham khảo, không phải khuyến nghị đầu tư. "
    "Nhà đầu tư tự chịu trách nhiệm với quyết định của mình."
)
UP, DOWN = "#16a34a", "#dc2626"
# Cỡ chữ ô chỉ số co theo độ rộng chính ô đó (container query) -> không tràn chữ trên màn hình hẹp
METRIC_CSS = """<style>
[data-testid="stMetric"] { container-type: inline-size; }
[data-testid="stMetricValue"], [data-testid="stMetricValue"] > div {
  font-size: 1.6rem;
  font-size: clamp(1.05rem, 14cqi, 2.25rem);
}
</style>"""


# ---------------------------------------------------------------- dữ liệu
def _load_one(symbol: str) -> dict:
    df, err = fetch_history(symbol)
    if err:
        return {"error": err}
    quote, _ = fetch_quote(symbol)  # báo giá là phần bổ sung, lỗi thì vẫn phân tích được
    try:
        ind = add_indicators(merge_quote(df, quote))
        return {
            "df": ind,
            "quote": quote,
            "analysis": analyze(symbol, ind),
            "levels": support_resistance(ind),
        }
    except Exception as e:  # không để một mã lỗi làm sập cả trang
        return {"error": f"Lỗi khi phân tích {symbol}: {e}"}


@st.cache_data(ttl=BASKET_TTL, show_spinner=False)
def _load_basket_cached() -> tuple[list, bool]:
    symbols, err = fetch_group(BASKET_GROUP, min_size=BASKET_MIN_SIZE)
    return (symbols, True) if symbols else (BASKET_FALLBACK, False)


def load_basket() -> tuple[list, bool]:
    """Thành phần rổ chỉ số từ SSI; lỗi thì dùng danh sách dự phòng và thử lại ở lần sau."""
    symbols, live = _load_basket_cached()
    if not live:
        _load_basket_cached.clear()
    return symbols, live


@st.cache_data(ttl=CACHE_TTL, max_entries=MAX_CACHE_ENTRIES, show_spinner=False)
def _load_many_cached(symbols: tuple) -> tuple[dict, datetime]:
    with ThreadPoolExecutor(max_workers=min(8, len(symbols))) as pool:
        results = list(pool.map(_load_one, symbols))
    return dict(zip(symbols, results)), datetime.now(VN_TZ)


def load_many(symbols: tuple) -> tuple[dict, datetime]:
    results, fetched_at = _load_many_cached(symbols)
    # Lỗi mạng là tạm thời: bỏ khỏi cache để lần tải sau thử lại ngay
    if any(r.get("error", "").startswith(NETWORK_ERROR) for r in results.values()):
        _load_many_cached.clear(symbols)
    return results, fetched_at


# ---------------------------------------------------------------- hiển thị
def fmt(v, digits=2) -> str:
    return "—" if v is None or pd.isna(v) else f"{v:,.{digits}f}"


def fmt_volume(v) -> str:
    """Khối lượng dạng gọn để không tràn ô trên màn hình hẹp: 13,395,100 -> '13.40 tr'."""
    if v is None or pd.isna(v):
        return "—"
    return f"{v / 1e6:,.2f} tr" if v >= 1e6 else f"{v:,.0f}"


def price_info(r: dict) -> tuple[float, float]:
    """Giá & % thay đổi: ưu tiên báo giá realtime, dự phòng bằng nến gần nhất."""
    df, q = r["df"], r["quote"] or {}
    if q.get("price") and q.get("change_pct") is not None:
        return q["price"], q["change_pct"]
    close = float(df["close"].iloc[-1])
    prev = float(df["close"].iloc[-2]) if len(df) > 1 else close
    return close, (close / prev - 1) * 100 if prev else 0.0


def build_chart(view: pd.DataFrame, levels: dict) -> go.Figure:
    fig = make_subplots(
        rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.03,
        row_heights=[0.55, 0.15, 0.15, 0.15],
        subplot_titles=("Giá (nghìn đồng)", "Khối lượng", "RSI (14)", "MACD (12, 26, 9)"),
    )
    x = view.index
    fig.add_trace(go.Candlestick(
        x=x, open=view["open"], high=view["high"], low=view["low"], close=view["close"],
        name="Giá", increasing_line_color=UP, decreasing_line_color=DOWN,
    ), row=1, col=1)
    for col, color in (("MA20", "#f59e0b"), ("MA50", "#3b82f6"), ("MA200", "#a855f7")):
        fig.add_trace(go.Scatter(x=x, y=view[col], name=col, line=dict(width=1.3, color=color)), row=1, col=1)
    for col in ("BB_upper", "BB_lower"):
        fig.add_trace(go.Scatter(
            x=x, y=view[col], name="Bollinger", legendgroup="bb", showlegend=col == "BB_upper",
            line=dict(width=1, color="#94a3b8", dash="dot"),
        ), row=1, col=1)
    if 20 in levels:
        support, resistance = levels[20]
        fig.add_hline(y=support, line=dict(color=UP, width=1, dash="dash"), row=1, col=1,
                      annotation_text=f"Hỗ trợ {support:,.2f}", annotation_position="bottom left")
        fig.add_hline(y=resistance, line=dict(color=DOWN, width=1, dash="dash"), row=1, col=1,
                      annotation_text=f"Kháng cự {resistance:,.2f}", annotation_position="top left")

    vol_colors = [UP if c >= o else DOWN for o, c in zip(view["open"], view["close"])]
    fig.add_trace(go.Bar(x=x, y=view["volume"], marker_color=vol_colors, name="KL", showlegend=False), row=2, col=1)
    fig.add_trace(go.Scatter(x=x, y=view["VOL_MA20"], name="KL TB20", showlegend=False,
                             line=dict(width=1, color="#f59e0b")), row=2, col=1)

    fig.add_trace(go.Scatter(x=x, y=view["RSI"], name="RSI", showlegend=False,
                             line=dict(width=1.3, color="#8b5cf6")), row=3, col=1)
    for lvl in (30, 70):
        fig.add_hline(y=lvl, line=dict(color="#94a3b8", width=1, dash="dot"), row=3, col=1)

    hist_colors = [UP if v >= 0 else DOWN for v in view["MACD_hist"].fillna(0)]
    fig.add_trace(go.Bar(x=x, y=view["MACD_hist"], marker_color=hist_colors, name="Histogram", showlegend=False), row=4, col=1)
    fig.add_trace(go.Scatter(x=x, y=view["MACD"], name="MACD", showlegend=False,
                             line=dict(width=1.2, color="#3b82f6")), row=4, col=1)
    fig.add_trace(go.Scatter(x=x, y=view["MACD_signal"], name="Signal", showlegend=False,
                             line=dict(width=1.2, color="#f59e0b")), row=4, col=1)

    # Ẩn các ngày không giao dịch (cuối tuần, lễ) để nến liền mạch
    missing = pd.date_range(x[0], x[-1]).difference(x)
    fig.update_xaxes(rangebreaks=[dict(values=missing.strftime("%Y-%m-%d").tolist())])
    fig.update_layout(
        height=760, margin=dict(l=10, r=10, t=40, b=10), hovermode="x unified",
        xaxis_rangeslider_visible=False,
        # chú thích đặt bên trái để không đè thanh công cụ của biểu đồ (góc phải)
        legend=dict(orientation="h", yanchor="bottom", y=1.04, xanchor="left", x=0),
    )
    fig.update_xaxes(hoverformat="%d/%m/%Y")
    fig.update_yaxes(hoverformat=",.2f")
    fig.update_yaxes(hoverformat=",.0f", row=2, col=1)
    fig.update_yaxes(range=[0, 100], row=3, col=1)
    return fig


def indicator_table(last: pd.Series) -> pd.DataFrame:
    rows = [
        ("MA20 / MA50 / MA200", f"{fmt(last['MA20'])} / {fmt(last['MA50'])} / {fmt(last['MA200'])}"),
        ("EMA20", fmt(last["EMA20"])),
        ("RSI (14)", fmt(last["RSI"], 1)),
        ("MACD / Signal / Histogram", f"{fmt(last['MACD'], 3)} / {fmt(last['MACD_signal'], 3)} / {fmt(last['MACD_hist'], 3)}"),
        ("Bollinger trên / giữa / dưới", f"{fmt(last['BB_upper'])} / {fmt(last['BB_mid'])} / {fmt(last['BB_lower'])}"),
        ("Stochastic %K / %D", f"{fmt(last['STOCH_K'], 1)} / {fmt(last['STOCH_D'], 1)}"),
        ("ADX / +DI / -DI", f"{fmt(last['ADX'], 1)} / {fmt(last['DI_plus'], 1)} / {fmt(last['DI_minus'], 1)}"),
        ("Khối lượng / TB 20 phiên", f"{fmt(last['volume'], 0)} / {fmt(last['VOL_MA20'], 0)}"),
    ]
    return pd.DataFrame(rows, columns=["Chỉ báo", "Giá trị"])


def render_symbol(symbol: str, r: dict, days: int):
    df, q, a = r["df"], r["quote"] or {}, r["analysis"]
    last = df.iloc[-1]
    price, change_pct = price_info(r)

    tag = " · Ngân hàng" if is_bank(symbol) else ""
    st.markdown(f"#### {symbol} — {q.get('name', symbol)}")
    st.caption(f"Sàn {q.get('exchange') or '—'}{tag} · Phiên {q.get('trading_date') or last.name.strftime('%d/%m/%Y')}")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Giá (nghìn đồng)", fmt(price), f"{change_pct:+.2f}%")
    volume = q.get("volume") or last["volume"]
    c2.metric("Khối lượng", fmt_volume(volume), help=f"{fmt(volume, 0)} cổ phiếu")
    high = q.get("high") or last["high"]
    low = q.get("low") or last["low"]
    # giá thấp đặt ở dòng phụ để giá trị ngắn, không bị cắt chữ trên màn hình hẹp
    c3.metric("Cao / Thấp phiên", fmt(high), f"Thấp {fmt(low)}", delta_color="off", delta_arrow="off")
    c4.metric("Vốn hóa (tỷ đồng)", fmt(q.get("market_cap"), 0))

    rec = a["recommendation"]
    box = {"MUA": st.success, "GIỮ": st.warning, "BÁN": st.error}[rec]
    box(f"**Nhận định kỹ thuật: {rec}** · Điểm tín hiệu {a['score']:+d} (thang −{a['max_score']} đến +{a['max_score']})")
    with st.expander("Lý do nhận định", expanded=True):
        for score, text in a["reasons"]:
            icon = "🟢" if score > 0 else "🔴" if score < 0 else "⚪"
            st.markdown(f"{icon} {text}")
        if a["trend_note"]:
            st.markdown(f"📊 {a['trend_note']}")
        for note in a["notes"]:
            st.info(note)

    view = df[df.index >= df.index[-1] - pd.Timedelta(days=days)]
    st.plotly_chart(build_chart(view, r["levels"]), key=f"chart_{symbol}", config={"displaylogo": False})

    left, right = st.columns([3, 2])
    with left:
        st.markdown("**Chỉ báo mới nhất**")
        st.dataframe(indicator_table(last), hide_index=True)
    with right:
        st.markdown("**Hỗ trợ / Kháng cự**")
        for n, (sup, res) in r["levels"].items():
            st.markdown(f"- {n} phiên: hỗ trợ **{sup:,.2f}** · kháng cự **{res:,.2f}**")
        csv = view.round(4).to_csv().encode("utf-8-sig")  # utf-8-sig để Excel đọc đúng tiếng Việt
        st.download_button("⬇️ Tải dữ liệu CSV", csv, file_name=f"{symbol}_phan_tich.csv",
                           mime="text/csv", key=f"dl_{symbol}")


def comparison_table(ok: dict) -> pd.DataFrame:
    rows = []
    for s, r in ok.items():
        price, change_pct = price_info(r)
        a = r["analysis"]
        # cột quan trọng đặt trước để không bị khuất trên điện thoại
        rows.append({
            "Mã": s,
            "Nhận định": a["recommendation"],
            "Giá": price,
            "Thay đổi (%)": change_pct,
            "Điểm": a["score"],
            "RSI": r["df"]["RSI"].iloc[-1],
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- giao diện
basket, basket_live = load_basket()
all_symbols = sorted(set(basket) | set(BANKS))

with st.sidebar:
    st.header("Chọn cổ phiếu")
    selected = st.multiselect(
        f"Rổ {APP_NAME}",
        all_symbols,
        # mã mặc định phải nằm trong danh sách, nếu không Streamlit báo lỗi
        default=[s for s in DEFAULT_SYMBOLS if s in all_symbols],
        format_func=lambda s: f"{s} · NH" if is_bank(s) else s,
        placeholder="Chọn mã...",
    )
    st.caption(
        f"Rổ chỉ số {BASKET_GROUP}: {len(basket)} mã, "
        + ("cập nhật từ SSI." if basket_live else "dùng danh sách lưu sẵn (chưa kết nối được SSI).")
    )
    typed = st.text_input("Hoặc nhập mã khác", placeholder="VD: TCB, MWG")
    period = st.radio("Khoảng thời gian", list(PERIODS), index=2, horizontal=True)
    if st.button("🔄 Làm mới dữ liệu", width="stretch"):
        _load_many_cached.clear()
    st.caption(f"Tối đa {MAX_SYMBOLS} mã mỗi lần. Dữ liệu tự làm mới sau {CACHE_TTL // 60} phút.")

st.html(METRIC_CSS)
st.title(f"📈 Phân tích cổ phiếu {APP_NAME}")
st.caption(DISCLAIMER)

symbols, invalid = parse_symbols(selected, typed)
if invalid:
    st.warning(f"Mã không hợp lệ, đã bỏ qua: {', '.join(invalid)}")
if not symbols:
    st.info("👈 Chọn hoặc nhập ít nhất một mã cổ phiếu ở thanh bên.")
    st.stop()
if len(symbols) > MAX_SYMBOLS:
    st.warning(f"Chỉ phân tích {MAX_SYMBOLS} mã đầu tiên.")
    symbols = symbols[:MAX_SYMBOLS]

with st.spinner("Đang tải dữ liệu từ sàn..."):
    results, fetched_at = load_many(tuple(symbols))

st.caption(f"🕒 Dữ liệu lấy lúc {fetched_at:%H:%M:%S %d/%m/%Y} · Nguồn: SSI iBoard")

ok = {s: r for s, r in results.items() if "error" not in r}
for s, r in results.items():
    if "error" in r:
        st.error(r["error"])
if not ok:
    st.stop()

if len(ok) > 1:
    st.markdown("##### So sánh nhanh")
    st.dataframe(
        comparison_table(ok),
        hide_index=True,
        column_config={
            "Giá": st.column_config.NumberColumn(format="%.2f"),
            "Thay đổi (%)": st.column_config.NumberColumn(format="%+.2f"),
            "RSI": st.column_config.NumberColumn(format="%.1f"),
            "Điểm": st.column_config.NumberColumn(format="%+d"),
        },
    )

for tab, (symbol, r) in zip(st.tabs(list(ok)), ok.items()):
    with tab:
        render_symbol(symbol, r, PERIODS[period])
