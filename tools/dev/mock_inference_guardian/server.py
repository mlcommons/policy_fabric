import argparse
import base64
import binascii
import json
import logging
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

logger = logging.getLogger(__name__)

SERVICE_NAME = "mock_inference_guardian"
METHOD_NAME = "do_inference"

CAPABILITY_KEYS = ("minted_identity", "operation")
SECRET_KEYS = ("encrypted_session_key", "session_key_iv", "encrypted_message")
OPERATION_KEYS = ("nonce", "method_name", "parameters")


class MockGuardianError(Exception):
    def __init__(self, message, status=HTTPStatus.BAD_REQUEST):
        super().__init__(message)
        self.message = message
        self.status = status


def _b64_json(text, what):
    try:
        raw = base64.b64decode(text, validate=True)
    except (binascii.Error, ValueError, TypeError) as e:
        raise MockGuardianError(f"{what} is not valid base64: {e}")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise MockGuardianError(f"{what} does not decode to JSON: {e}")
    if not isinstance(value, dict):
        raise MockGuardianError(f"{what} is not a JSON object")
    return value


def _require(obj, keys, what):
    missing = [k for k in keys if k not in obj]
    if missing:
        raise MockGuardianError(f"malformed {what}: missing {', '.join(missing)}")


def parse_request(body):
    text = body.decode("utf-8", errors="replace").strip()
    if not text:
        raise MockGuardianError("empty request body")

    if text.startswith("{"):
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as e:
            raise MockGuardianError(f"invalid JSON, malformed request: {e}")
        if not isinstance(parsed, dict):
            raise MockGuardianError("invalid JSON, malformed request")

        if "capability_b64" in parsed:
            capability = _b64_json(parsed["capability_b64"], "capability_b64")
        else:
            capability = {k: v for k, v in parsed.items() if k != "request_context"}

        if "request_context" not in parsed:
            raise MockGuardianError("invalid JSON, malformed request")
        request_context = parsed["request_context"]
        if not isinstance(request_context, dict):
            raise MockGuardianError("invalid JSON, malformed request")
    else:
        _b64_json(text, "capability")
        raise MockGuardianError("invalid JSON, malformed request")

    _require(capability, CAPABILITY_KEYS, "capability package")
    if not isinstance(capability["operation"], dict):
        raise MockGuardianError("malformed capability package: 'operation' is not an object")
    _require(capability["operation"], SECRET_KEYS, "operation secret")

    return capability, request_context


def read_operation(capability):
    operation = _b64_json(capability["operation"]["encrypted_message"], "encrypted_message")
    _require(operation, OPERATION_KEYS, "operation")
    if not isinstance(operation["parameters"], dict):
        raise MockGuardianError("malformed operation: 'parameters' is not an object")
    return operation


class MockGuardianHandler(BaseHTTPRequestHandler):
    server_version = f"{SERVICE_NAME}/0.1"

    def do_GET(self):
        path = self.path.split("?", 1)[0].rstrip("/") or "/"

        if path == "/info":
            self._respond_json(
                {
                    "service": SERVICE_NAME,
                    "guardian_type": "inference",
                    "mock": True,
                    "method_name": METHOD_NAME,
                }
            )
        else:
            self._error(f"unknown path: {path}", HTTPStatus.NOT_FOUND)

    def do_POST(self):
        path = self.path.split("?", 1)[0].rstrip("/") or "/"
        if path != "/process_capability":
            self._error(f"unknown path: {path}", HTTPStatus.NOT_FOUND)
            return

        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            self._error("invalid Content-Length")
            return
        body = self.rfile.read(length) if length > 0 else b""

        try:
            capability, request_context = parse_request(body)
            operation = read_operation(capability)
        except MockGuardianError as e:
            self._error(e.message, e.status)
            return

        method_name = operation["method_name"]
        if method_name != METHOD_NAME:
            self._error(f"unknown operation '{method_name}'", HTTPStatus.NOT_FOUND)
            return

        parameters = operation["parameters"]
        logger.info(
            "process capability operation %s with parameters %s (request context %s)",
            method_name,
            parameters,
            request_context,
        )

        authorized_digest = parameters.get("script_digest")
        calculated_digest = request_context.get("calculated_script_digest")
        if not authorized_digest or not calculated_digest:
            logger.warning(
                "operation failed: capability authorizes %r, caller computed %r",
                authorized_digest,
                calculated_digest,
            )
            self._error("operation failed", HTTPStatus.UNPROCESSABLE_ENTITY)
            return

        if calculated_digest != authorized_digest:
            logger.warning(
                "script digest mismatch: capability authorizes %s, caller computed %s",
                authorized_digest,
                calculated_digest,
            )
            self._error("operation failed", HTTPStatus.UNPROCESSABLE_ENTITY)
            return

        logger.info("releasing data for authorized script %s", authorized_digest)
        self._respond_result(
            {
                "allowed": True,
                "script_digest": authorized_digest,
                "method_name": method_name,
                "mock": True,
            }
        )

    def _respond(self, payload, content_type, status, extra_headers=()):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        for header, value in extra_headers:
            self.send_header(header, value)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _respond_json(self, body, status=HTTPStatus.OK):
        self._respond(json.dumps(body).encode("utf-8"), "application/json", status)

    def _respond_result(self, body):
        self._respond(
            json.dumps(body).encode("utf-8"),
            "application/octet-stream",
            HTTPStatus.OK,
            [("Content-Transfer-Encoding", "utf-8")],
        )

    def _error(self, message, status=HTTPStatus.BAD_REQUEST):
        logger.info("error response: %s", message)
        self._respond((message + "\n").encode("utf-8"), "text/plain", status)

    def log_message(self, format, *args):
        logger.info("%s - %s", self.address_string(), format % args)


def serve(interface, port):
    httpd = ThreadingHTTPServer((interface, port), MockGuardianHandler)
    logger.info("%s listening on %s:%d", SERVICE_NAME, interface, port)
    httpd.serve_forever()


def main():
    parser = argparse.ArgumentParser(description="Run the mock inference guardian.")
    parser.add_argument(
        "-n",
        "--interface",
        default=os.environ.get("INTERFACE", "0.0.0.0"),
        help="interface to bind (default: $INTERFACE or 0.0.0.0)",
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=int(os.environ.get("PORT", "7900")),
        help="port to bind (default: $PORT or 7900)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    serve(args.interface, args.port)


if __name__ == "__main__":
    main()
