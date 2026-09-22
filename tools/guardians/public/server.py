"""An open asset server: the no-policy end of the guardian spectrum.

This stands in front of an asset that is published in the clear. It answers any
caller with the file it was started on -- no capability, no credentials, no
policy object behind it -- so a demo can put an open asset and a policy-gated
asset side by side and show what the difference buys.

It answers ``/info`` like the real guardians do, so the same health check works
across every guardian type, and serves the data on ``/`` and ``/data``.
"""

import argparse
import json
import logging
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

logger = logging.getLogger(__name__)

SERVICE_NAME = "public_guardian"


class PublicGuardianHandler(BaseHTTPRequestHandler):
    """Serve the data file on ``/`` and ``/data``, service metadata on ``/info``.

    ``data`` is read once at startup and held on the server object, mirroring the
    PDO guardian operations, which also load the file when the service comes up.
    """

    server_version = f"{SERVICE_NAME}/0.1"

    def do_GET(self):
        path = self.path.split("?", 1)[0].rstrip("/") or "/"

        if path == "/info":
            self._respond_json(
                {
                    "service": SERVICE_NAME,
                    "guardian_type": "public",
                    "data_length": len(self.server.data),
                }
            )
        elif path in ("/", "/data"):
            self._respond_text(self.server.data)
        else:
            self._respond_json({"error": f"unknown path: {path}"}, HTTPStatus.NOT_FOUND)

    def _respond(self, body, content_type, status):
        payload = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _respond_json(self, body, status=HTTPStatus.OK):
        self._respond(json.dumps(body), "application/json", status)

    def _respond_text(self, body, status=HTTPStatus.OK):
        self._respond(body, "text/plain; charset=utf-8", status)

    def log_message(self, format, *args):
        logger.info("%s - %s", self.address_string(), format % args)


def serve(interface, port, data_path):
    with open(data_path) as f:
        data = f.read()

    httpd = ThreadingHTTPServer((interface, port), PublicGuardianHandler)
    httpd.data = data
    logger.info(
        "%s serving %s (%d bytes) on %s:%d", SERVICE_NAME, data_path, len(data), interface, port
    )
    httpd.serve_forever()


def main():
    parser = argparse.ArgumentParser(description="Run the public (unguarded) asset server.")
    parser.add_argument(
        "-n", "--interface", default="127.0.0.1", help="interface to bind (default: 127.0.0.1)"
    )
    parser.add_argument("-p", "--port", type=int, default=7900, help="port to bind (default: 7900)")
    parser.add_argument(
        "-d",
        "--data-path",
        default=os.environ.get("GUARDIAN_DATA_PATH"),
        help="data file to serve (default: $GUARDIAN_DATA_PATH)",
    )
    args = parser.parse_args()

    if not args.data_path:
        parser.error("a data file is required: pass --data-path or set GUARDIAN_DATA_PATH")

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    serve(args.interface, args.port, args.data_path)


if __name__ == "__main__":
    main()
