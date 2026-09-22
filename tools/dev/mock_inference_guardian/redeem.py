#!/usr/bin/env python3

import argparse
import json
import sys
import urllib.error
import urllib.request


def read_capability(path):
    with open(path) as f:
        return f.read().replace("\n", "").strip()


def post(url, body):
    request = urllib.request.Request(
        f"{url.rstrip('/')}/process_capability",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request) as response:
            return response.status, response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as e:
        raise SystemExit(f"could not reach {url}: {e.reason}")


def main():
    parser = argparse.ArgumentParser(
        description="Redeem a capability file at a mock inference guardian."
    )
    parser.add_argument(
        "-f",
        "--capability-file",
        required=True,
        help="base64 capability file from capability_generator.sh",
    )
    parser.add_argument(
        "-c",
        "--calculated-hash",
        required=True,
        help="the digest to report as measured over the script being run",
    )
    parser.add_argument(
        "-u", "--url", default="http://localhost:7900", help="guardian base URL"
    )
    args = parser.parse_args()

    try:
        capability_b64 = read_capability(args.capability_file)
    except OSError as e:
        raise SystemExit(str(e))

    status, body = post(
        args.url,
        {
            "capability_b64": capability_b64,
            "request_context": {"calculated_script_digest": args.calculated_hash},
        },
    )

    print(f"reported digest: {args.calculated_hash}")
    print(f"HTTP {status}")
    print(body.rstrip("\n"))

    return 0 if 200 <= status < 300 else 1


if __name__ == "__main__":
    sys.exit(main())
