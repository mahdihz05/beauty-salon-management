#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_ROOT="$PROJECT_ROOT/backend"
FRONTEND_ROOT="$PROJECT_ROOT/frontend"

if [ ! -f "$BACKEND_ROOT/.env" ]; then
  echo "Create backend/.env from backend/.env.production.example and set your domain first." >&2
  exit 1
fi

set -a
# shellcheck disable=SC1091
source "$BACKEND_ROOT/.env"
set +a

python -m pip install --disable-pip-version-check -r "$BACKEND_ROOT/requirements-production.txt"

if [ "${REBUILD_FRONTEND:-false}" = "true" ] || [ ! -f "$FRONTEND_ROOT/dist/index.html" ]; then
  if ! command -v npm >/dev/null 2>&1; then
    echo "Node.js is required because a frontend rebuild was requested." >&2
    exit 1
  fi
  npm --prefix "$FRONTEND_ROOT" ci
  npm --prefix "$FRONTEND_ROOT" run build
fi

mkdir -p "$BACKEND_ROOT/media" "$(dirname "${SQLITE_PATH:-$BACKEND_ROOT/db.sqlite3}")"
python "$BACKEND_ROOT/manage.py" migrate --noinput
python "$BACKEND_ROOT/manage.py" collectstatic --noinput
python "$BACKEND_ROOT/manage.py" check --deploy

mkdir -p "$PROJECT_ROOT/tmp"
touch "$PROJECT_ROOT/tmp/restart.txt"
echo "Shared-host deployment steps completed successfully."
