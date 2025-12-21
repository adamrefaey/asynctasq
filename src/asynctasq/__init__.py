"""AsyncTasQ - Modern async-first task queue for Python."""

import importlib.metadata

try:
    __version__ = importlib.metadata.version("asynctasq")
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.0.0"
