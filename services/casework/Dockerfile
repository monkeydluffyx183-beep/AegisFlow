FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi uvicorn pydantic
COPY services/casework/src /app/src
ENV PYTHONPATH=/app/src
EXPOSE 8030
CMD ["uvicorn", "casework.main:app", "--host", "0.0.0.0", "--port", "8030"]
