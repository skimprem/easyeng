FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    EASYENG_VAR_DIR=/data \
    DJANGO_STATIC_ROOT=/app/staticfiles \
    DJANGO_DEBUG=0

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN DJANGO_SECRET_KEY=collectstatic-only python manage.py collectstatic --noinput \
    && useradd --create-home --uid 1000 app \
    && mkdir -p /data && chown app /data

USER app
VOLUME /data
EXPOSE 8000
ENTRYPOINT ["/app/docker/entrypoint.sh"]
# timeout побольше: установка словаря FreeDict из интерфейса идёт прямо в запросе
CMD ["gunicorn", "config.wsgi", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "180", "--access-logfile", "-"]
