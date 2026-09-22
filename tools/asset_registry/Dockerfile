# Minimal image for the asset_registry Django toy server.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings

WORKDIR /app

# Install deps first so code changes don't bust the pip layer.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the app. db.sqlite3 and caches are excluded via .dockerignore.
COPY . .

# Non-root user + group 0 access so any host uid can read/write mounted
# volumes when launched with `--user $(id -u):0`. New files written at
# runtime inherit gid 0 from the process's egid.
RUN useradd -m -u 1000 app && \
    chgrp -R 0 /app && chmod -R g=u /app
USER 1000:0

# run.sh migrates, seeds the dev admin user, then execs the dev server.
# CMD holds the bind flag; override at runtime to change it.
ENTRYPOINT ["bash", "/app/run.sh"]
CMD ["--interface", "0.0.0.0", "--port", "8000"]
