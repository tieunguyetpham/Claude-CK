#!/usr/bin/env bash
# Cài / cập nhật app trading trên VPS (chạy cạnh ppmeeting, không đụng tới ppmeeting).
# Dùng (trên VPS):  bash /opt/Claude-CK/deploy/deploy.sh
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$APP_DIR"

if [[ "${TRADING_DEPLOY_PULLED:-}" != 1 ]]; then
    echo "==> 1/3 Lấy code mới nhất"
    git pull --ff-only
    # Chạy lại bản deploy.sh vừa kéo về (bash vẫn đang chạy nội dung cũ của file này)
    TRADING_DEPLOY_PULLED=1 exec bash "$APP_DIR/deploy/deploy.sh" "$@"
fi
echo "    phiên bản code: $(git log -1 --format='%h %s')"

echo "==> 2/3 Build và chạy container trading-app"
sudo docker compose -f deploy/docker-compose.yml up -d --build

echo "==> 3/3 Chờ app sẵn sàng"
status="none"
for _ in $(seq 1 30); do
    status=$(sudo docker inspect -f '{{.State.Health.Status}}' trading-app 2>/dev/null || echo none)
    [[ "$status" == "healthy" ]] && break
    sleep 2
done
if [[ "$status" != "healthy" ]]; then
    echo "!! trading-app chưa sẵn sàng (trạng thái: $status). Log gần nhất:" >&2
    sudo docker logs --tail 50 trading-app >&2
    exit 1
fi

# Chỉ dọn image cũ của project trading, không đụng image của ppmeeting
sudo docker image prune -f --filter "label=app=trading-app" >/dev/null

# Build cache của Docker dùng chung toàn VPS (cả ppmeeting) nên không tự dọn, chỉ cảnh báo khi đĩa gần đầy
disk_used=$(df --output=pcent / | tail -1 | tr -dc '0-9')
if (( disk_used >= 85 )); then
    echo "!! Ổ đĩa đã dùng ${disk_used}%. Dọn build cache cũ hơn 7 ngày (chỉ là cache, không xóa image/dữ liệu):"
    echo "     sudo docker builder prune -f --filter until=168h"
fi
echo "==> Xong: https://trading.tieunguyetpham.store (ổ đĩa: ${disk_used}%)"
