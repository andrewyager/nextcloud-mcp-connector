"""Office and PDF documents as Markdown (TOOL-14).

One entry point, :func:`convert`, and four converters behind it. Two rules hold the whole
package together:

* **The parser libraries are optional.** Every converter imports its library inside the
  function, so this package imports without the ``documents`` extra, and a missing library
  becomes one refusal that names the install command instead of an import error at start.
* **No parser exception reaches a client.** Whatever a library raises on a damaged or
  hostile file is mapped to one refusal that names the file and the format. The class and
  message are logged at DEBUG only: they describe the file, and the file is the user's.

Conversion is CPU work on sync libraries, so :func:`convert` runs it in a worker thread with
``asyncio.to_thread``, the pattern of ``oauth/store.py``. A thread cannot be cancelled; the
guards in ``zipguard`` and in the converters are the protection against a long conversion.
"""

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass

from ..errors import ToolError
from . import detect, zipguard

__all__ = ["INSTALL_HINT", "MAX_SOURCE_BYTES", "Converted", "convert", "convert_sync"]

logger = logging.getLogger(__name__)

MAX_SOURCE_BYTES = 25 * 1024 * 1024

INSTALL_HINT = (
    'Install the documents extra: pip install "nextcloud-mcp-connector[documents]", '
    "or use the ExApp image, which carries it."
)

_OFFICE = frozenset({"docx", "xlsx", "pptx"})


@dataclass(frozen=True)
class Converted:
    markdown: str
    format: str


def _converter(fmt: str) -> Callable[[bytes], str]:
    # Imported here and not at module level for the same reason the libraries are: the
    # converter modules are cheap, but keeping the lookup next to the ImportError handling
    # makes the one place where a missing library surfaces easy to find.
    if fmt == "docx":
        from .docx import to_markdown
    elif fmt == "xlsx":
        from .xlsx import to_markdown
    elif fmt == "pptx":
        from .pptx import to_markdown
    else:
        from .pdf import to_markdown
    return to_markdown


def convert_sync(data: bytes, content_type: str, name: str) -> Converted:
    """Convert in the calling thread. :func:`convert` is the async door."""
    fmt = detect.detect(content_type, name)
    try:
        # The guard is inside the try: a malformed archive header can raise more than
        # BadZipFile, and all of it is one refusal. A ToolError passes through.
        if fmt in _OFFICE:
            zipguard.check(data, name)
        markdown = _converter(fmt)(data)
    except ToolError:
        raise
    except ImportError:
        raise ToolError(
            message=f"Reading {fmt} files needs the documents extra, which is not installed.",
            hint=INSTALL_HINT,
        ) from None
    except Exception as exc:  # every parser failure is one refusal by design
        logger.debug("%s conversion of %s failed: %s", fmt, name, type(exc).__name__)
        raise ToolError(
            message=f"{name} could not be read as {fmt}.",
            hint="Open the file in Nextcloud to check it; it may be damaged or mislabelled.",
        ) from None
    return Converted(markdown=markdown, format=fmt)


async def convert(data: bytes, content_type: str, name: str) -> Converted:
    """Convert in a worker thread so the event loop keeps serving other calls."""
    return await asyncio.to_thread(convert_sync, data, content_type, name)
