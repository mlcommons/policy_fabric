__all__ = ["DownloadOperation"]

from .download import DownloadOperation

capability_handler_map = {
    "do_download": DownloadOperation,
}
