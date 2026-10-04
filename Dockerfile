# おしごと production image. Runs next to MyGenba on the same VM, behind MyGenba's
# Caddy, with its data in MyGenba's Postgres (see docker-compose.yml, README).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=Asia/Tokyo \
    OSHIGOTO_DATA=/data \
    OSHIGOTO_ENV=/data/.env

# slim images ship no zoneinfo; tzdata makes TZ resolve (the "days since" count uses today)
RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app

EXPOSE 8710
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8710", \
     "--workers", "1", "--no-access-log", "--proxy-headers", "--forwarded-allow-ips", "*"]
