# Built with the REPO ROOT as build context (not ./backend) - see
# render.yaml and docker-compose.yml, both of which pass `backend/...` paths
# below for exactly this reason. This matches Render's proven pattern for a
# Docker-runtime service in a monorepo (dockerContext at repo root,
# dockerfilePath reaching into the subdirectory) rather than pointing
# dockerContext directly at the subdirectory, which failed to build.
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app

EXPOSE 8000

# Shell form (not exec-array) so $PORT is expanded at container start. Falls
# back to 8000 for local docker-compose, which doesn't set PORT; platforms
# like Render inject their own PORT (commonly 10000) that the app must bind
# to, so this must stay dynamic rather than a hardcoded --port 8000.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
