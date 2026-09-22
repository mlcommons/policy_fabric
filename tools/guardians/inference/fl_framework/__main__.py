"""Entry point for the FL client: ``python -m fl_framework``."""

import argparse
import logging
import os
import socket

from .client import FLClient


def main():
    parser = argparse.ArgumentParser(description="Run the mock FL client.")
    parser.add_argument(
        "-s",
        "--server-url",
        default=os.environ.get("FL_SERVER_URL"),
        help="FL server to poll for jobs (default: $FL_SERVER_URL)",
    )
    parser.add_argument(
        "-g",
        "--guardian-url",
        default=os.environ.get("GUARDIAN_CORE_URL", "http://localhost:7900"),
        help="guardian core to redeem capabilities at (default: $GUARDIAN_CORE_URL)",
    )
    parser.add_argument(
        "-c",
        "--client-id",
        default=os.environ.get("FL_CLIENT_ID") or socket.gethostname(),
        help="identifies this client to the FL server (default: $FL_CLIENT_ID or hostname)",
    )
    parser.add_argument(
        "-d",
        "--asset-did",
        default=os.environ.get("ASSET_DID"),
        help="DID of the asset this client holds (default: $ASSET_DID)",
    )
    parser.add_argument(
        "-N",
        "--asset-name",
        default=os.environ.get("ASSET_NAME"),
        help="display name for that asset (default: $ASSET_NAME)",
    )
    parser.add_argument(
        "-i",
        "--poll-interval",
        type=float,
        default=float(os.environ.get("FL_POLL_INTERVAL", "3")),
        help="seconds between polls (default: $FL_POLL_INTERVAL or 3)",
    )
    args = parser.parse_args()

    if not args.server_url:
        parser.error("an FL server is required: pass --server-url or set FL_SERVER_URL")
    # Without it the server cannot list this site for a requester to pick, and
    # cannot tell which capability was minted for this guardian -- so a client
    # that does not say what it holds is not a participant, it is noise.
    if not args.asset_did:
        parser.error("an asset DID is required: pass --asset-did or set ASSET_DID")

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    FLClient(
        server_url=args.server_url,
        guardian_url=args.guardian_url,
        client_id=args.client_id,
        asset_did=args.asset_did,
        asset_name=args.asset_name,
        poll_interval=args.poll_interval,
    ).run_forever()


if __name__ == "__main__":
    main()
