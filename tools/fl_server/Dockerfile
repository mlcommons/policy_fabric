FROM python:3.11-slim

# The server is stdlib-only on purpose: an aggregator that needed a PDO client to
# hand out opaque blobs would be claiming a relationship with PDO that it does
# not have.
COPY server.py /project/server.py

RUN useradd -m -u 1000 fl_user
USER 1000:0

EXPOSE 7920

ENTRYPOINT ["python", "-u", "/project/server.py"]
CMD ["--interface", "0.0.0.0", "--port", "7920"]
