__all__ = ["InferenceOperation"]

from .inference import InferenceOperation

capability_handler_map = {
    "do_inference": InferenceOperation,
}
