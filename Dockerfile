# Imagen de AhorraPues. Producción por defecto.
# Desarrollo (docker-compose.yml): --build-arg REQUIREMENTS=dev
FROM python:3.12-slim

ARG REQUIREMENTS=prod
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements/ requirements/
RUN pip install --no-cache-dir -r requirements/${REQUIREMENTS}.txt

COPY . .

# Estáticos con hash para WhiteNoise (solo producción). Las variables son ficticias y viven
# únicamente durante este paso; en ejecución las aporta el entorno.
RUN if [ "$REQUIREMENTS" = "prod" ]; then \
      DJANGO_SETTINGS_MODULE=config.settings.prod SECRET_KEY=solo-para-collectstatic \
      REDIS_URL=redis://localhost:6379/0 DATABASE_URL=sqlite:///:memory: \
      python manage.py collectstatic --noinput; \
    fi

RUN useradd --create-home app && chown -R app /app
USER app

# Cloud Run y App Runner inyectan PORT; WEB_CONCURRENCY ajusta los procesos de gunicorn.
ENV PORT=8000 WEB_CONCURRENCY=3
EXPOSE 8000
CMD ["sh", "-c", "exec gunicorn config.wsgi:application --bind 0.0.0.0:${PORT} --workers ${WEB_CONCURRENCY} --access-logfile -"]
