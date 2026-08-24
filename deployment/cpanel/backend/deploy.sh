#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_ROOT="$PROJECT_ROOT/backend"
DATA_ROOT="$HOME/salovina-data"

if [ -z "${VIRTUAL_ENV:-}" ]; then
  ACTIVATE_PATH="$(find "$HOME/virtualenv/apps/salovina-backend" -path '*/bin/activate' -print -quit 2>/dev/null || true)"
  if [ -z "$ACTIVATE_PATH" ]; then
    echo "Create the Python App with root apps/salovina-backend first." >&2
    exit 1
  fi
  # shellcheck disable=SC1090
  source "$ACTIVATE_PATH"
fi

mkdir -p "$DATA_ROOT/media" "$DATA_ROOT/cache"
chmod 700 "$DATA_ROOT"

if [ ! -f "$BACKEND_ROOT/.env" ]; then
  SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(64))')"
  umask 077
  cat > "$BACKEND_ROOT/.env" <<EOF
DJANGO_SECRET_KEY=$SECRET_KEY
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS=api.saloniva.ir,saloniva.ir,www.saloniva.ir
CSRF_TRUSTED_ORIGINS=https://api.saloniva.ir,https://saloniva.ir,https://www.saloniva.ir
CORS_ALLOWED_ORIGINS=https://saloniva.ir,https://www.saloniva.ir
DJANGO_SECURE_SSL_REDIRECT=true
SQLITE_PATH=$DATA_ROOT/db.sqlite3
MEDIA_ROOT=$DATA_ROOT/media
DJANGO_CACHE_LOCATION=$DATA_ROOT/cache
SERVE_MEDIA_FILES=true
OTP_PROVIDER=mock
OTP_EXPOSE_MOCK_CODE=true
OTP_CODE_TTL_SECONDS=120
OTP_REQUEST_LIMIT_PER_HOUR=5
PAYMENT_PROVIDER=mock
PLATFORM_COMMISSION_PERCENT=10
CANCELLATION_FREE_HOURS=24
MAX_IMAGE_UPLOAD_BYTES=5242880
EOF
fi

set -a
# shellcheck disable=SC1091
source "$BACKEND_ROOT/.env"
set +a

python -m pip install --disable-pip-version-check --no-cache-dir -r "$BACKEND_ROOT/requirements-shared-host.txt"
python "$BACKEND_ROOT/manage.py" migrate --noinput
python "$BACKEND_ROOT/manage.py" collectstatic --noinput
python "$BACKEND_ROOT/manage.py" check --deploy

mkdir -p "$PROJECT_ROOT/tmp"
touch "$PROJECT_ROOT/tmp/restart.txt"
echo "Salovina backend deployment completed."
echo "Open https://api.saloniva.ir/api/health/."
