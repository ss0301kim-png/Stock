#!/usr/bin/env bash
# 기존 OCI Compute 인스턴스에서 실행하는 설치 스크립트.
# 권장 흐름:
#   git clone https://github.com/ss0301kim-png/Stock.git /opt/kis-daytrading-bot
#   cd /opt/kis-daytrading-bot
#   sudo bash scripts/oci/setup.sh
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/kis-daytrading-bot}"
SERVICE_USER="${SERVICE_USER:-kisbot}"

if [[ $EUID -ne 0 ]]; then
  echo "root 권한으로 실행하세요: sudo bash scripts/oci/setup.sh" >&2
  exit 1
fi

echo "==> 필수 패키지 설치"
if command -v dnf >/dev/null 2>&1; then
  dnf install -y python3 python3-pip git rsync
elif command -v apt-get >/dev/null 2>&1; then
  apt-get update -y
  apt-get install -y python3 python3-venv python3-pip git rsync
else
  echo "지원하지 않는 배포판입니다. python3 / venv / pip / git을 수동 설치한 뒤 다시 실행하세요." >&2
  exit 1
fi

echo "==> 서비스 계정 준비 ($SERVICE_USER)"
id -u "$SERVICE_USER" &>/dev/null || useradd --system --create-home --shell /usr/sbin/nologin "$SERVICE_USER"

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

if [[ "$REPO_DIR" != "$APP_DIR" ]]; then
  echo "==> $REPO_DIR -> $APP_DIR 로 배포"
  mkdir -p "$APP_DIR"
  rsync -a --exclude='.venv' --exclude='.git' --exclude='logs' --exclude='__pycache__' --exclude='.env' \
    "$REPO_DIR"/ "$APP_DIR"/
fi

cd "$APP_DIR"

echo "==> 가상환경 및 의존성 설치"
python3 -m venv .venv
./.venv/bin/pip install --upgrade pip
./.venv/bin/pip install -r requirements.txt

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "==> .env 파일을 생성했습니다. 실행 전 반드시 $APP_DIR/.env 를 채워넣으세요."
fi

chown -R "$SERVICE_USER":"$SERVICE_USER" "$APP_DIR"

echo "==> systemd 서비스 등록"
sed "s#__APP_DIR__#$APP_DIR#g; s#__SERVICE_USER__#$SERVICE_USER#g" \
  "$REPO_DIR/scripts/oci/kis-daytrader.service.template" > /etc/systemd/system/kis-daytrader.service
systemctl daemon-reload

cat <<EOF

==> 설치 완료.

다음 단계:
  1. sudo nano $APP_DIR/.env
     KIS_APP_KEY / KIS_APP_SECRET / KIS_ACCOUNT_NO / WATCHLIST 등을 채워넣으세요.
     처음엔 IS_VIRTUAL=true, DRY_RUN=true 로 충분히 검증한 뒤 실전으로 전환하세요.
  2. sudo systemctl enable --now kis-daytrader
  3. 상태 확인:   systemctl status kis-daytrader
     로그 확인:   journalctl -u kis-daytrader -f
                 tail -f $APP_DIR/logs/daytrader.log
  4. .env 수정 후 반영: sudo systemctl restart kis-daytrader

이 봇은 KIS 서버로 나가는 요청만 하므로 OCI 보안 목록에서 별도 인바운드 포트를 열 필요가 없습니다.
EOF
