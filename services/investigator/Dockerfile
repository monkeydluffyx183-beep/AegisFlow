FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi uvicorn pydantic
COPY services/investigator/src /app/src
ENV PYTHONPATH=/app/src
EXPOSE 8040
CMD ["uvicorn", "investigator.main:app", "--host", "0.0.0.0", "--port", "8040"]
