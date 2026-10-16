FROM python:3.12-slim
WORKDIR /app
COPY generator /app/generator
ENV PYTHONPATH=/app/generator/src
ENTRYPOINT ["python", "-m", "txgen.main"]
