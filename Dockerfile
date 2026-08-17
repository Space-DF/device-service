FROM python:3.10-alpine AS builder

ENV PYTHONUNBUFFERED=1

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
RUN --mount=type=secret,id=github_token \
    pip install --no-cache-dir --prefix=/install \
    git+https://$(cat /run/secrets/github_token)@github.com/Space-DF/django-common-utils.git@${COMMON_UTILS_REF}

# install python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.10-alpine

ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE="device_service.settings"

RUN apk add --no-cache \
    curl \
    libffi \
    postgresql-client

WORKDIR /app

COPY --from=builder /install /usr/local
COPY . .

RUN ["chmod", "+x", "./docker-entrypoint.sh"]

ENTRYPOINT ["./docker-entrypoint.sh"]
