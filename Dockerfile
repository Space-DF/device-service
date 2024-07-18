FROM python:3.10-alpine
ENV PYTHONUNBUFFERED 1

ARG ENV
ARG SECRET_KEY
ARG DB_NAME
ARG DB_USERNAME
ARG DB_PASSWORD
ARG DB_HOST
ARG DB_PORT
ARG CORS_ALLOWED_ORIGINS
ARG HOST
ARG DEFAULT_TENANT_HOST
ARG CELERY_BROKER_URL
ARG JWK_URL

# Allows docker to cache installed dependencies between builds
RUN apk add build-base libffi-dev
COPY ./device_service/requirements.txt requirements.txt
RUN pip install -r requirements.txt
COPY ./pkg pkg
RUN pip install ../pkg

# Adds our application code to the image
COPY ./device_service device_service

WORKDIR device_service

EXPOSE 80

ENV DJANGO_SETTINGS_MODULE "device_service.settings.production"

ENV ENV ${ENV}
ENV SECRET_KEY ${SECRET_KEY}
ENV DB_NAME ${DB_NAME}
ENV DB_USERNAME ${DB_USERNAME}
ENV DB_PASSWORD ${DB_PASSWORD}
ENV DB_HOST ${DB_HOST}
ENV DB_PORT ${DB_PORT}
ENV CORS_ALLOWED_ORIGINS ${CORS_ALLOWED_ORIGINS}
ENV HOST ${HOST}
ENV DEFAULT_TENANT_HOST ${DEFAULT_TENANT_HOST}
ENV CELERY_BROKER_URL ${CELERY_BROKER_URL}
ENV JWK_URL ${JWK_URL}

RUN ["chmod", "+x", "./docker-entrypoint.sh"]

# Run the production server
ENTRYPOINT ["./docker-entrypoint.sh"]
