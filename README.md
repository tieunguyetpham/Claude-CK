# 📈 Phân tích cổ phiếu VN50 & Ngân hàng

Dashboard web phân tích kỹ thuật cổ phiếu Việt Nam, viết bằng Python + Streamlit.
Dữ liệu lấy trực tiếp từ API công khai của **SSI iBoard** (lịch sử giá + báo giá realtime).

- Repo: https://github.com/tieunguyetpham/Claude-CK
- Địa chỉ triển khai: https://tieunguyetpham.store/trading

> ⚠️ Thông tin chỉ mang tính tham khảo, không phải khuyến nghị đầu tư. Ứng dụng **không** đặt lệnh và **không** kết nối tài khoản giao dịch.

## Tính năng

- Chọn nhanh mã trong **rổ VN50** và **nhóm ngân hàng**, hoặc gõ mã bất kỳ (tối đa 10 mã/lần).
- Giá realtime, % thay đổi, khối lượng, cao/thấp phiên, vốn hóa (khi nguồn có số liệu).
- Biểu đồ nến + MA20/50/200 + Bollinger + hỗ trợ/kháng cự, khối lượng, RSI, MACD.
- Chỉ báo: MA, EMA, RSI(14), MACD(12,26,9), Bollinger(20,2), Stochastic(14,3), ADX(14), khối lượng TB20.
- **Nhận định MUA / GIỮ / BÁN** theo điểm tín hiệu, kèm lý do từng chỉ báo; ghi chú riêng cho cổ phiếu ngân hàng.
- Bảng so sánh nhiều mã, tải dữ liệu CSV, tự làm mới dữ liệu sau 5 phút (hoặc bấm "Làm mới").

## Cấu trúc

| File | Vai trò |
|---|---|
| `app.py` | Giao diện Streamlit |
| `data.py` | Gọi API SSI (thử lại khi lỗi mạng, chuẩn hóa đơn vị nghìn đồng) |
| `indicators.py` | Tính chỉ báo kỹ thuật bằng pandas thuần |
| `analysis.py` | Chấm điểm tín hiệu, sinh nhận định |
| `symbols.py` | Danh sách VN50, ngân hàng; kiểm tra mã người dùng nhập |
| `tests/` | Kiểm thử đầu vào (`python -m pytest -q`) |
| `deploy/` | File cấu hình & script triển khai VPS |
| `prompt.docx` | Prompt mô tả yêu cầu phần mềm |

## Chạy trên máy (Windows)

Yêu cầu Python **3.11 trở lên**.

```bash
python -m venv venv
venv\Scripts\python -m pip install -r requirements.txt
venv\Scripts\python -m streamlit run app.py
```

Mở http://localhost:8501. Chạy kiểm thử: `venv\Scripts\python -m pip install -r requirements-dev.txt` rồi `venv\Scripts\python -m pytest -q`.

## Triển khai trên VPS (Ubuntu 24.04)

1. **Trỏ tên miền**: tại nhà cung cấp tên miền, tạo bản ghi `A` cho `tieunguyetpham.store` và `www` trỏ về IP của VPS. Kiểm tra: `ping tieunguyetpham.store` ra đúng IP.
2. **Cài app** (SSH vào VPS):
   ```bash
   git clone https://github.com/tieunguyetpham/Claude-CK.git /opt/Claude-CK
   sudo bash /opt/Claude-CK/deploy/deploy.sh
   ```
   Script tự cài Python/Nginx/Certbot, tạo user `trading`, cài thư viện, chạy app bằng systemd (cổng nội bộ 8501, sub-path `/trading`) và cấu hình Nginx reverse proxy có WebSocket.
3. **Bật HTTPS** (một lần, sau khi DNS đã trỏ đúng):
   ```bash
   sudo certbot --nginx -d tieunguyetpham.store -d www.tieunguyetpham.store
   ```
4. Truy cập https://tieunguyetpham.store/trading

**Cập nhật phiên bản mới**: `sudo bash /opt/Claude-CK/deploy/deploy.sh` (tự `git pull` và khởi động lại).

**Xem log / khởi động lại**: `journalctl -u trading -n 100 -f` · `sudo systemctl restart trading`

Nếu VPS đã có cấu hình Nginx cho tên miền, script sẽ không ghi đè mà nhắc thêm dòng `include snippets/trading.conf;` vào server block hiện có.

## Giới hạn dữ liệu

- API công khai của SSI không cung cấp P/E, P/B, EPS, ROE nên ứng dụng không hiển thị các chỉ số này.
- Một số mã SSI không trả số cổ phiếu niêm yết → ô vốn hóa hiện "—".
- API công khai có thể thay đổi không báo trước; khi đó cần cập nhật `data.py`.
