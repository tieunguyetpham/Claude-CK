# 📈 Phân tích cổ phiếu VN50 & Ngân hàng

Dashboard web phân tích kỹ thuật cổ phiếu Việt Nam, viết bằng Python + Streamlit.
Dữ liệu lấy trực tiếp từ API công khai của **SSI iBoard** (lịch sử giá + báo giá realtime).

- Repo: https://github.com/tieunguyetpham/Claude-CK
- Địa chỉ triển khai: https://trading.tieunguyetpham.store

> ⚠️ Thông tin chỉ mang tính tham khảo, không phải khuyến nghị đầu tư. Ứng dụng **không** đặt lệnh và **không** kết nối tài khoản giao dịch.

## Tính năng

- Chọn nhanh mã trong **rổ VN50** (chỉ số **VNX50** — 50 mã lớn nhất HOSE + HNX, thành phần lấy trực tiếp từ SSI
  nên tự cập nhật khi rổ cơ cấu lại; có danh sách dự phòng khi API lỗi) và **27 ngân hàng niêm yết**, hoặc gõ mã bất kỳ (tối đa 10 mã/lần).
- Giá realtime, % thay đổi, khối lượng, cao/thấp phiên, vốn hóa (khi nguồn có số liệu).
- Phân tích dùng giá realtime trong phiên (ghép vào nến cuối), khớp với giá đang hiển thị.
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
| `symbols.py` | Rổ VNX50 dự phòng, danh sách ngân hàng; kiểm tra mã người dùng nhập |
| `tools/make_prompt_docx.py` | Tạo lại `prompt.docx` (`python tools/make_prompt_docx.py`) |
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
4. **Chứng chỉ HTTPS**: bổ sung `trading` vào chứng chỉ có sẵn của ppmeeting. Nginx ppmeeting dừng vài giây để certbot dùng cổng 80.
   Chạy hook của ppmeeting **thủ công** (không truyền `--pre-hook/--post-hook`, nếu không certbot sẽ lưu thêm hook trùng vào cấu hình gia hạn):
   ```bash
   H=/etc/letsencrypt/renewal-hooks
   sudo $H/pre/ppmeeting.sh
   sudo certbot certonly --standalone --cert-name tieunguyetpham.store --expand --non-interactive \
     -d tieunguyetpham.store -d www.tieunguyetpham.store -d trading.tieunguyetpham.store \
     && sudo $H/deploy/ppmeeting.sh
   sudo $H/post/ppmeeting.sh   # luôn chạy để bật lại Nginx, kể cả khi certbot lỗi
   ```
   Các lần gia hạn sau dùng lại cơ chế tự động có sẵn của ppmeeting.
5. **Nginx**: `nginx.conf` được gắn vào container dạng **một file đơn** → phải sửa **giữ nguyên file** (ghi đè nội dung bằng `cat >`/`tee`),
   không dùng `sed -i`, `mv` hay trình soạn thảo tạo file mới (container sẽ vẫn đọc bản cũ).
   ```bash
   C=/opt/ppmeeting/infra/nginx/nginx.conf
   sudo cp -p $C $C.bak-$(date +%Y%m%d-%H%M%S)            # sao lưu
   # Chèn deploy/nginx-trading.conf ngay trước dấu } cuối cùng (đóng khối http)
   sudo python3 - "$C" /opt/Claude-CK/deploy/nginx-trading.conf <<'PY' | sudo tee "$C.new" >/dev/null
   import sys
   conf, block = open(sys.argv[1]).read(), open(sys.argv[2]).read()
   i = conf.rstrip().rfind("}")
   sys.stdout.write(conf[:i] + block + conf[i:])
   PY
   sudo sh -c "cat $C.new > $C" && sudo rm $C.new             # ghi đè nội dung, giữ nguyên inode
   sudo docker exec ppmeeting-nginx-1 nginx -t && sudo docker exec ppmeeting-nginx-1 nginx -s reload
   ```
   Nếu `nginx -t` báo lỗi: khôi phục bằng `sudo sh -c "cat $C.bak-... > $C"`.
   Nếu sau này deploy lại ppmeeting từ mã nguồn gốc, nhớ thêm khối trading vào `infra/nginx/nginx.conf` của ppmeeting để không bị mất.
6. Truy cập https://trading.tieunguyetpham.store

### Vận hành

- **Cập nhật phiên bản mới**: `bash /opt/Claude-CK/deploy/deploy.sh` (tự `git pull`, build lại, chờ app sẵn sàng).
- **Xem log**: `sudo docker logs -f --tail 100 trading-app` · **Khởi động lại**: `sudo docker restart trading-app`
- **Dung lượng**: app chiếm khoảng 1.7 GB (image + build cache), tăng thêm khoảng 0.7 GB mỗi lần đổi phiên bản thư viện.
  `deploy.sh` cảnh báo khi ổ đĩa ≥ 85%; khi đó dọn build cache cũ: `sudo docker builder prune -f --filter until=168h`
  (áp dụng cho cả cache build của ppmeeting — chỉ là cache, không ảnh hưởng image hay dữ liệu).
- Tự phục hồi: Docker bật cùng VPS, container `restart: unless-stopped`, giới hạn 512 MB RAM, log xoay vòng 3 × 10 MB.
- Container trading dừng không ảnh hưởng ppmeeting (Nginx phân giải tên container lúc có request).
- Lưu ý: khi chạy `docker compose down` cho ppmeeting, hãy dừng trading trước
  (`sudo docker compose -f /opt/Claude-CK/deploy/docker-compose.yml down`) vì hai bên dùng chung mạng `ppmeeting_default`.

## Giới hạn dữ liệu

- API công khai của SSI không cung cấp P/E, P/B, EPS, ROE nên ứng dụng không hiển thị các chỉ số này.
- Một số mã SSI không trả số cổ phiếu niêm yết → ô vốn hóa hiện "—".
- API công khai có thể thay đổi không báo trước; khi đó cần cập nhật `data.py`.
