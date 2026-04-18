FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p logs

EXPOSE 8000

# ✅ Shell form — $PORT will be expanded at runtime
CMD sh -c "python manage.py migrate && \
           python manage.py collectstatic --noinput && \
           gunicorn freight_project.wsgi:application \
             --bind 0.0.0.0:${PORT:-8000} \
             --workers 4 \
             --timeout 120 \
             --access-logfile -"