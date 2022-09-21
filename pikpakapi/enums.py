from enum import Enum


class DownloadStatus(Enum):
    not_downloading = "not_downloading"
    downloading = "downloading"
    done = "done"
    error = "error"
    not_found = "not_found"
