# ИРБИС-Веб — производственный образ: сборка фронта (node) + рантайм бэкенда (python/aiohttp).
# Build context = irbis-web/.   docker build -t irbis-web .

# ---- stage 1: build the React/TS frontend ----
FROM node:22-alpine AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build                      # -> /web/dist (self-hosted, без CDN)

# ---- stage 2: python runtime ----
FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir "aiohttp>=3.9,<4" "asyncpg>=0.29,<1"
COPY backend/ /app/backend/
COPY --from=web /web/dist /app/frontend/dist
# дефолты прод-окружения (реальные значения — через docker-compose/.env)
ENV APP_HOST=0.0.0.0 \
    APP_PORT=8080 \
    APP_ENV=prod \
    ACCESS_DB=/app/data/access.db
RUN mkdir -p /app/data
EXPOSE 8080
# health: GET / отдаёт собранный SPA; /api/health — статус подключения к ИРБИС
CMD ["python", "/app/backend/app_aiohttp.py"]
