FROM node:24-bookworm-slim AS frontend
WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
ENV VITE_API_URL=/api
RUN npm run build

FROM python:3.12-slim-bookworm
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY backend/requirements-production.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY backend/ /app/backend/
COPY --from=frontend /build/dist /app/frontend/dist
WORKDIR /app/backend
RUN DJANGO_DEBUG=true python manage.py collectstatic --noinput
CMD ["sh", "-ec", "mkdir -p /data/media; python manage.py migrate --noinput; if [ ! -f /data/.demo-seeded ]; then python manage.py seed_demo; python manage.py seed_showcase; touch /data/.demo-seeded; fi; exec gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2 --timeout 120 --access-logfile -"]
