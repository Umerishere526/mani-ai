# ABOUTME: Container image for the API process. Works on Fly, Railway or Cloud Run.
# ABOUTME: Never Lambda-style - a turn holds a connection across a multi-second model call.

FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .
COPY mani/ mani/
COPY prompts/ prompts/
COPY scripts/ scripts/

# Runs unprivileged. The image holds no secrets; configuration arrives as environment.
RUN useradd --create-home --uid 10001 mani
USER mani

EXPOSE 8000

# The platform's health check should hit /health/ready, which reports the database.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
