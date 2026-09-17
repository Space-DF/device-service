# syntax=docker/dockerfile:1.7

FROM python:3.10-alpine AS builder

ENV PYTHONUNBUFFERED=1

COPY --from=ghcr.io/astral-sh/uv:0.6.5 /uv /uvx /bin/

RUN apk add --no-cache \
    build-base \
    libffi-dev \
    git \
    postgresql-dev

WORKDIR /install

# install private repo
# Pinned by CI to the commit image-plan.py hashed into this image's content
# key. Defaults to dev so a hand build still works.
ARG COMMON_UTILS_REF=dev
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

RUN --mount=type=secret,id=github_token \
    uv pip install --no-cache --python /install/.venv/bin/python \
    git+https://$(cat /run/secrets/github_token)@github.com/Space-DF/django-common-utils.git@${COMMON_UTILS_REF}

FROM python:3.10-alpine

ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE="device_service.settings"
ENV PATH="/install/.venv/bin:$PATH"

RUN apk add --no-cache \
    curl \
    libffi \
    libstdc++ \
    postgresql-client

WORKDIR /app

COPY --from=builder /install/.venv /install/.venv
COPY . .

RUN adduser --disabled-password --gecos "" appuser \
    && chown -R appuser:appuser /app

RUN ["chmod", "+x", "./docker-entrypoint.sh"]

USER appuser

ENTRYPOINT ["./docker-entrypoint.sh"]
