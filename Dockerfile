FROM python:3.10-alpine AS builder

ENV PYTHONUNBUFFERED=1

RUN apk add --no-cache \
    build-base \
    libffi-dev \
    git \
    postgresql-dev \
    geos-dev \
    proj-dev \
    proj-util \
    gdal-dev

WORKDIR /install

# install private repo
RUN --mount=type=secret,id=github_token \
    pip install --no-cache-dir --prefix=/install \
    git+https://$(cat /run/secrets/github_token)@github.com/Space-DF/django-common-utils.git@dev

# install python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.10-alpine

ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE="device_service.settings"

RUN apk add --no-cache \
    curl \
    libffi \
    postgresql-client \
    geos \
    proj \
    proj-data \
    gdal \
        && ln -sf /usr/lib/libgdal.so.* /usr/lib/libgdal.so \
        && ln -sf /usr/lib/libgeos_c.so.* /usr/lib/libgeos_c.so

WORKDIR /app

COPY --from=builder /install /usr/local
COPY . .

RUN ["chmod", "+x", "./docker-entrypoint.sh"]

ENV PROJ_LIB=/usr/share/proj
ENV GEOS_LIBRARY_PATH=/usr/lib/libgeos_c.so
ENV GDAL_LIBRARY_PATH=/usr/lib/libgdal.so

ENTRYPOINT ["./docker-entrypoint.sh"]
