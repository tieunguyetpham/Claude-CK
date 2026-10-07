# 📈 Phân tích cổ phiếu VN50 & Ngân hàng

Dashboard web phân tích kỹ thuật cổ phiếu Việt Nam, viết bằng Python + Streamlit.
Dữ liệu lấy trực tiếp từ API công khai của **SSI iBoard** (lịch sử giá + báo giá realtime).

- Repo: https://github.com/tieunguyetpham/Claude-CK
- Địa chỉ triển khai: https://trading.tieunguyetpham.store

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
| `Dockerfile`, `deploy/` | Đóng gói Docker, cấu hình Nginx & script triển khai VPS |
| `prompt.docx` | Prompt mô tả yêu cầu phần mềm |

## Chạy trên máy (Windows)

Yêu cầu Python **3.11 trở lên**.

```bash
python -m venv venv
venv\Scripts\python -m pip install -r requirements.txt
venv\Scripts\python -m streamlit run app.py
```

Mở http://localhost:8501. Chạy kiểm thử: `venv\Scripts\python -m pip install -r requirements-dev.txt` rồi `venv\Scripts\python -m pytest -q`.

## Triển khai trên VPS

VPS `116.118.6.222` (Ubuntu 24.04) đang chạy **ppmeeting** bằng Docker; container `ppmeeting-nginx-1` giữ cổng 80/443.
App trading chạy trong **container riêng** `trading-app` (giới hạn 512 MB RAM), cùng mạng Docker `ppmeeting_default`.
Nginx của ppmeeting chuyển tiếp tên miền con `trading.tieunguyetpham.store` tới container này. Không cài Nginx riêng.

### Cài lần đầu (một lần)

1. **DNS**: bản ghi `A` của `trading.tieunguyetpham.store` trỏ về `116.118.6.222` (đã có).
2. **Tải code** (repo Public, không cần đăng nhập):
   ```bash
   sudo mkdir -p /opt/Claude-CK && sudo chown $USER: /opt/Claude-CK
   git clone https://github.com/tieunguyetpham/Claude-CK.git /opt/Claude-CK
   ```
3. **Chạy app**: `bash /opt/Claude-CK/deploy/deploy.sh`
4. **Chứng chỉ HTTPS**: bổ sung `trading` vào chứng chỉ có sẵn của ppmeeting (Nginx ppmeeting dừng vài giây để certbot dùng cổng 80):
   ```bash
   sudo certbot certonly --standalone --cert-name tieunguyetpham.store --expand \
     -d tieunguyetpham.store -d www.tieunguyetpham.store -d trading.tieunguyetpham.store \
     --pre-hook  /etc/letsencrypt/renewal-hooks/pre/ppmeeting.sh \
     --deploy-hook /etc/letsencrypt/renewal-hooks/deploy/ppmeeting.sh \
     --post-hook /etc/letsencrypt/renewal-hooks/post/ppmeeting.sh
   ```
   Các lần gia hạn sau dùng lại cơ chế tự động có sẵn của ppmeeting.
5. **Nginx**: sao lưu `/opt/ppmeeting/infra/nginx/nginx.conf`, chèn nội dung `deploy/nginx-trading.conf` vào trong khối `http { }`, rồi:
   ```bash
   sudo docker exec ppmeeting-nginx-1 nginx -t && sudo docker exec ppmeeting-nginx-1 nginx -s reload
   ```
6. Truy cập https://trading.tieunguyetpham.store

### Vận hành

- **Cập nhật phiên bản mới**: `bash /opt/Claude-CK/deploy/deploy.sh` (tự `git pull`, build lại, chờ app sẵn sàng).
- **Xem log**: `sudo docker logs -f --tail 100 trading-app` · **Khởi động lại**: `sudo docker restart trading-app`
- Container trading dừng không ảnh hưởng ppmeeting (Nginx phân giải tên container lúc có request).
- Lưu ý: khi chạy `docker compose down` cho ppmeeting, hãy dừng trading trước
  (`sudo docker compose -f /opt/Claude-CK/deploy/docker-compose.yml down`) vì hai bên dùng chung mạng `ppmeeting_default`.

## Giới hạn dữ liệu

- API công khai của SSI không cung cấp P/E, P/B, EPS, ROE nên ứng dụng không hiển thị các chỉ số này.
- Một số mã SSI không trả số cổ phiếu niêm yết → ô vốn hóa hiện "—".
- API công khai có thể thay đổi không báo trước; khi đó cần cập nhật `data.py`.
