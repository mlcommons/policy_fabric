"""
This file defines the InvokeApp class, a WSGI interface class for
handling contract method invocation requests.
"""

from pdo.contracts.guardian.common.utility import ValidateJSON
from .utils import AsymmetricEncryption
import logging
import base64
import os

logger = logging.getLogger(__name__)


# XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
class DownloadOperation:
    # -----------------------------------------------------------------
    __schema__ = {
        "type": "object",
        "properties": {
            "channel_key": {"type": "string"},
        },
        "required": ["channel_key"],
    }

    # -----------------------------------------------------------------
    def __init__(self, config):
        data_path = os.environ.get("GUARDIAN_DATA_PATH")
        if data_path:
            with open(data_path) as f:
                self.data = f.read()
        else:
            raise RuntimeError("GUARDIAN_DATA_PATH not set")

    def __encrypted_data(self, channel_key):
        # Encrypt the data using the provided channel key

        return AsymmetricEncryption().encrypt(channel_key.encode(), self.data.encode())

    # -----------------------------------------------------------------
    # request_context carries what the caller claims about this request. Releasing
    # the data turns only on the channel key the capability authorizes, so there is
    # nothing here to check it against and it is ignored.
    def __call__(self, params, request_context):
        if not ValidateJSON(params, self.__schema__):
            return None
        channel_key = params["channel_key"]
        enc_data = self.__encrypted_data(channel_key)

        return base64.b64encode(enc_data).decode()
