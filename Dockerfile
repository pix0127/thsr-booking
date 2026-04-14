FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    busybox dumb-init \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /etc/crontabs /var/log/supervisor /run

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

WORKDIR /app/src

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

RUN pip install --no-cache-dir supervisor \
    && cp /app/src/crontab.txt /etc/crontabs/root \
    && chmod 0644 /etc/crontabs/root \
    && touch /var/log/cron_booking.log \
        /var/log/supervisor/supervisord.log \
        /var/log/supervisor/supervisord.error.log \
        /var/log/supervisor/streamlit.log \
        /var/log/supervisor/streamlit.error.log \
        /var/log/supervisor/cron.log \
        /var/log/supervisor/cron.error.log

EXPOSE 8501

CMD ["/usr/bin/dumb-init", "--", "/usr/local/bin/supervisord", "-c", "/app/src/supervisord.conf"]
