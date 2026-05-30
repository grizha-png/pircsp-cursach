FROM python:3.12-slim

WORKDIR /app

COPY src/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY src /app/src

ENV PYTHONPATH=/app/src
ENV DB_PATH=/app/data/app.db

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
