FROM python:3.11-slim

COPY server.py /project/server.py

RUN useradd -m -u 1000 mock_user
USER 1000:0

EXPOSE 7900

ENTRYPOINT ["python", "-u", "/project/server.py"]
CMD ["--interface", "0.0.0.0", "--port", "7900"]
