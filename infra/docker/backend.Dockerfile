FROM python:3.11-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg tesseract-ocr \
  && rm -rf /var/lib/apt/lists/*

COPY backend/pyproject.toml ./pyproject.toml
RUN pip install --no-cache-dir -e . psycopg[binary]

COPY backend/app ./app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
