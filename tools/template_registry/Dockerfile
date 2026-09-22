# Minimal image for the template_registry Django toy server.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings

WORKDIR /app

# Install deps first so code changes don't bust the pip layer.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the registry app. The credential/policy-card folders it seeds from live
# outside this build context (at the top of the policy_fabric tree), so they are
# not baked in; run_docker.sh bind-mounts the host folders onto the container
# paths named in CMD below.
COPY . .

# Non-root user + group 0 access so any host uid can read/write mounted
# volumes when launched with `--user $(id -u):0`. New files written at
# runtime inherit gid 0 from the process's egid.
RUN useradd -m -u 1000 app && \
    chgrp -R 0 /app && chmod -R g=u /app
USER 1000:0

# run.sh migrates, seeds the templates + dev admin user, then execs the dev
# server. CMD supplies the bind flags and the container paths where the
# credential/policy-card folders are mounted; override at runtime to change them.
ENTRYPOINT ["bash", "/app/run.sh"]
CMD ["--interface", "0.0.0.0", "--port", "8000", \
     "--credentials-dir", "/templates/credentials", \
     "--policy-cards-dir", "/templates/policy_cards"]
