FROM python:3.12-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir poetry==1.8.3

# pipeline 의존성
COPY pipeline/pyproject.toml pipeline/poetry.lock* ./
RUN poetry config virtualenvs.create false \
    && poetry install --no-root --only main

# backend/app 모델을 공유 패키지로 사용
COPY pipeline/ .
COPY backend/ /backend
ENV PYTHONPATH="/app:/backend"

FROM base AS development
COPY pipeline/pyproject.toml ./
RUN poetry install --no-root

FROM base AS production
CMD ["celery", "-A", "pipeline.celery_app", "worker", "--loglevel=info", "--max-tasks-per-child=50"]
