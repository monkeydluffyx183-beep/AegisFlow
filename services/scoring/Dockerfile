FROM python:3.12-slim
WORKDIR /app
COPY services/platform/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY services/scoring/src /app/src
ENV PYTHONPATH=/app/src
EXPOSE 8010
CMD ["uvicorn", "scoring.main:app", "--host", "0.0.0.0", "--port", "8010"]
