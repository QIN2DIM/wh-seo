FROM python:3.10 as builder

WORKDIR /app

COPY . ./
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium --with-deps
