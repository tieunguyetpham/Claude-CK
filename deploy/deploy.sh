#!/usr/bin/env bash
# Cài đặt / cập nhật app trên VPS Ubuntu (chạy lại nhiều lần đều an toàn).
# Dùng:  sudo bash deploy/deploy.sh
set -euo pipefail

REPO_URL="https://github.com/tieunguyetpham/Claude-CK.git"
APP_DIR="/opt/Claude-CK"
APP_USER="trading"
DOMAIN="tieunguyetpham.store"

if [[ $EUID -ne 0 ]]; then
    echo "Hãy chạy bằng quyền root: sudo bash deploy/deploy.sh" >&2
    exit 1
fi

echo "==> 1/6 Cài gói hệ thống"
apt-get update -y
apt-get install -y python3 python3-venv git nginx certbot python3-certbot-nginx

if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)'; then
    echo "Cần Python >= 3.11 (hiện tại: $(python3 --version)). Dùng Ubuntu 24.04 hoặc cài python3.12." >&2
    exit 1
fi

echo "==> 2/6 Tạo user chạy app"
id -u "$APP_USER" >/dev/null 2>&1 || useradd --system --create-home --shell /usr/sbin/nologin "$APP_USER"

echo "==> 3/6 Lấy code từ GitHub"
if [[ -d "$APP_DIR/.git" ]]; then
    git -C "$APP_DIR" pull --ff-only
else
    git clone "$REPO_URL" "$APP_DIR"
fi
chown -R "$APP_USER:$APP_USER" "$APP_DIR"

echo "==> 4/6 Cài thư viện Python"
sudo -u "$APP_USER" python3 -m venv "$APP_DIR/venv"
sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install --upgrade pip --quiet
sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt" --quiet

echo "==> 5/6 Cài dịch vụ systemd"
cp "$APP_DIR/deploy/streamlit.service" /etc/systemd/system/trading.service
systemctl daemon-reload
systemctl enable trading.service
systemctl restart trading.service

echo "==> 6/6 Cấu hình Nginx"
cp "$APP_DIR/deploy/nginx-trading.conf" /etc/nginx/snippets/trading.conf
if grep -rqs "server_name.*$DOMAIN" /etc/nginx/sites-enabled/ /etc/nginx/conf.d/; then
    if ! grep -rqs "snippets/trading.conf" /etc/nginx/sites-enabled/ /etc/nginx/conf.d/; then
        echo "!! Đã có cấu hình Nginx cho $DOMAIN. Thêm dòng sau vào server block của nó rồi chạy lại script:"
        echo "     include snippets/trading.conf;"
    fi
else
    cp "$APP_DIR/deploy/nginx-site.conf" /etc/nginx/sites-available/trading
    ln -sf /etc/nginx/sites-available/trading /etc/nginx/sites-enabled/trading
fi
nginx -t
systemctl reload nginx

sleep 3
if curl -fs -o /dev/null "http://127.0.0.1:8501/trading/_stcore/health"; then
    echo "==> App đang chạy."
else
    echo "!! App chưa phản hồi. Xem log: journalctl -u trading -n 50" >&2
    exit 1
fi

echo
echo "Bước cuối (một lần, sau khi tên miền đã trỏ về IP VPS):"
echo "   certbot --nginx -d $DOMAIN -d www.$DOMAIN"
echo "Sau đó truy cập: https://$DOMAIN/trading"
