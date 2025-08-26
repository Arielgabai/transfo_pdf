FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Ensure runtime directories exist (ephemeral on Render)
RUN mkdir -p uploads output

# Default port for local runs; Render provides $PORT
ENV PORT=8080
EXPOSE 8080

CMD ["sh", "-c", "gunicorn -k gthread -w ${GUNICORN_WORKERS:-3} --threads ${GUNICORN_THREADS:-2} -b 0.0.0.0:${PORT:-8080} wsgi:app"]


