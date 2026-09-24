"""
This file defines the InferenceOperation class, the capability handler that tells
an FL client whether it may run a script over the data it holds.
"""

from pdo.contracts.guardian.common.utility import ValidateJSON
import logging

logger = logging.getLogger(__name__)


# XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
class InferenceOperation:
    """Answer yes or no: may the caller run the script it holds?

    The guardian core has no dataset. The data is mounted into the FL client,
    which asks this operation before running a job over it. The policy decides
    which script may touch the data and records its digest in the capability; the
    caller separately reports the digest it computed over the script it actually
    holds, and the answer is yes only when the two agree -- so a capability
    issued for one script cannot authorize running another. The reported digest
    arrives in the request context, outside the capability package and therefore
    unauthenticated, which is exactly why it is only ever compared against the
    authorized value and never trusted on its own.

    Yes is ``{"allowed": true, ...}``. No is the framework's failed-operation
    response (HTTP 422, ``operation failed``), returned by handing back ``None``
    -- the same response as parameters that do not validate. (A capability that
    does not decrypt never reaches this operation; the framework refuses it with
    a 400.) The answer has the same shape as
    ``tools/dev/mock_inference_guardian``'s, so a client built against the mock
    works against this unchanged.
    """

    # -----------------------------------------------------------------
    # Only the digest is required. The channel key is optional because this
    # operation does not read it (see __call__) and because a policy is entitled
    # not to produce one: the FL policies stand on their own, and one that only
    # governs the code -- FL-DS -- says nothing about the requester and so has no
    # channel key to carry. Requiring it here would make such a policy
    # unsatisfiable for a reason that has nothing to do with what it decides.
    __schema__ = {
        "type": "object",
        "properties": {
            "channel_key": {"type": "string"},
            "script_digest": {"type": "string"},
        },
        "required": ["script_digest"],
    }

    __request_context_schema__ = {
        "type": "object",
        "properties": {
            "calculated_script_digest": {"type": "string"},
        },
        "required": ["calculated_script_digest"],
    }

    # -----------------------------------------------------------------
    def __init__(self, config):
        pass

    # -----------------------------------------------------------------
    def __call__(self, params, request_context):
        if not ValidateJSON(params, self.__schema__):
            return None
        if not ValidateJSON(request_context, self.__request_context_schema__):
            return None

        authorized_digest = params["script_digest"]
        calculated_digest = request_context["calculated_script_digest"]
        if calculated_digest != authorized_digest:
            logger.warning(
                "denied: capability authorizes %s, caller computed %s",
                authorized_digest,
                calculated_digest,
            )
            return None

        # The channel key, when a policy carried one, is not used. Nothing leaves
        # this guardian but the answer, so there is nothing to encrypt to it.
        logger.info("allowed: script %s", authorized_digest)
        return {
            "allowed": True,
            "script_digest": authorized_digest,
            "method_name": "do_inference",
        }
