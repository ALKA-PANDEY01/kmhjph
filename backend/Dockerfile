FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATA_PATH=/app/data/wind_forecast_accuracy.parquet

WORKDIR /app

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

RUN useradd --create-home --uid 10001 appuser
COPY --chown=appuser:appuser app ./app
COPY --chown=appuser:appuser data ./data

USER appuser
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
