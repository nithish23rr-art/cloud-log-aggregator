FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# project layout: app/ (python + templates + company_logs) and static/ (script.js)
COPY app ./app
COPY static ./static

# app.py lives in /app/app, so run from there
WORKDIR /app/app

EXPOSE 5000
ENV PYTHONUNBUFFERED=1

CMD ["python", "app.py"]