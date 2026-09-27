FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY services/platform/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY services /app/services
COPY ml /app/ml
COPY generator /app/generator
RUN mkdir -p /app/data
ENV PYTHONPATH=/app/services/platform/src:/app/services/scoring/src:/app/services/ingestion/src:/app/services/casework/src:/app/services/investigator/src:/app/ml/src:/app/generator/src
EXPOSE 8000
CMD ["uvicorn", "aegisflow_platform.main:app", "--host", "0.0.0.0", "--port", "8000"]
