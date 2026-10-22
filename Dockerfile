FROM node:22-bookworm-slim AS frontend-build
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/index.html frontend/vite.config.js ./
COPY frontend/src ./src
COPY frontend/public ./public
RUN npm run build

FROM python:3.11-slim-bookworm AS python-build
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /build
COPY requirements.txt requirements-docker.txt ./
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements-docker.txt \
    && /opt/venv/bin/pip check

FROM python:3.11-slim-bookworm AS runtime
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends libstdc++6 libgomp1 tzdata \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 appuser
WORKDIR /app
COPY --from=python-build /opt/venv /opt/venv
COPY --chown=appuser:appuser backend ./backend
COPY --chown=appuser:appuser deploy ./deploy
COPY --from=frontend-build --chown=appuser:appuser /build/frontend/dist ./frontend/dist
RUN mkdir -p /app/backend/chroma_db /app/instance \
    && chown appuser:appuser /app/backend/chroma_db /app/instance
USER appuser
EXPOSE 5000
CMD ["python", "-m", "deploy.start"]
