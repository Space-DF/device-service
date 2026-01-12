# SpaceDF Device Service

## Prerequisites
- Python 3.10
- PostgreSQL

## Clone source code

```
git clone -b dev git@github.com:Space-DF/device-service.git
git clone -b dev git@github.com:Space-DF/django-common-utils.git
```

## Setup

- Install requirements

  ```
  pip install -r requirements.txt
  ```

- Run RabbitMQ broker
  ```
  docker run -d --name some-rabbit -p 5672:5672 -p 5673:5673 -p 15672:15672 rabbitmq:3-management
  ```

- Init .env
  ```
  cp .env.example .env
  ```

- Migrate
  ```
  python manage.py migrate
  ```

- Create testing organization
  ```
  python manage.py create_organization
  ```

- Create testing space
  ```
  python manage.py create_space
  ```

## Run source code
- Run server
  ```
  python manage.py runserver 8000
  ```

- The API documentation will be served on http://<testing organization slug name>.localhost:8000.

## Migration
When you make the change for the database model
- Make migration file
  ```
  python manage.py makemigrations
  ```
- Migrate
  ```
  python manage.py migrate_schemas
  ```
[![SpaceDF - A project from Digital Fortress](https://df.technology/images/SpaceDF.png)](https://df.technology/)