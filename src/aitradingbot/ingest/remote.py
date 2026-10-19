"""Read a remote file (or several remote parts concatenated) via HTTP range requests.

``zipfile.ZipFile`` only needs a seekable, readable file object. Wrapping Kraken's multi-part
archive in ``RangeFile`` lets us read the few CSVs we need out of a ~10 GB download while fetching
only a few tens of MB. ZipFile still verifies each member's CRC32 as it is read.
"""

from __future__ import annotations

import io
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Sequence

from aitradingbot.ingest.common import RETRY_STATUS, USER_AGENT

GetRange = Callable[[str, int, int], bytes]  # (url, first_byte, last_byte_inclusive) -> bytes

MIN_FETCH = 1 << 20  # fetch at least 1 MiB per request to avoid thousands of tiny requests


def http_get_range(
    url: str, first: int, last: int, *, timeout: float = 60.0, retries: int = 4
) -> bytes:
    headers = {"User-Agent": USER_AGENT, "Range": f"bytes={first}-{last}"}
    request = urllib.request.Request(url, headers=headers)
    expected = last - first + 1
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                if response.status != 206:
                    raise OSError(
                        f"server ignored the Range header for {url} (HTTP {response.status})"
                    )
                body: bytes = response.read()
            if len(body) != expected:
                raise OSError(f"short range read from {url}: {len(body)} of {expected} bytes")
            return body
        except urllib.error.HTTPError as exc:
            if exc.code not in RETRY_STATUS or attempt == retries:
                raise
        except (urllib.error.URLError, TimeoutError, OSError):
            if attempt == retries:
                raise
        time.sleep(2**attempt)
    raise AssertionError("unreachable")


def remote_size(url: str) -> int:
    """Total size of a remote file, read from the Content-Range header of a 1-byte range request."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Range": "bytes=0-0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        content_range = response.headers.get("Content-Range", "")
    _, _, total = content_range.rpartition("/")
    if not total.isdigit():
        raise OSError(f"no usable Content-Range header from {url}: {content_range!r}")
    return int(total)


class RangeFile(io.RawIOBase):
    """Seekable read-only view over remote parts that together form one file."""

    def __init__(
        self, urls: Sequence[str], sizes: Sequence[int], get_range: GetRange = http_get_range
    ):
        if len(urls) != len(sizes) or not urls:
            raise ValueError("need one size per URL")
        self._urls = list(urls)
        self._sizes = list(sizes)
        self._starts = [sum(self._sizes[:i]) for i in range(len(self._sizes))]
        self._size = sum(self._sizes)
        self._get_range = get_range
        self._pos = 0
        self._buffer = b""
        self._buffer_start = 0
        self.requests = 0
        self.bytes_fetched = 0

    @property
    def size(self) -> int:
        return self._size

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def tell(self) -> int:
        return self._pos

    def seek(self, offset: int, whence: int = io.SEEK_SET) -> int:
        base = {io.SEEK_SET: 0, io.SEEK_CUR: self._pos, io.SEEK_END: self._size}[whence]
        self._pos = max(0, base + offset)
        return self._pos

    def readinto(self, buffer: memoryview | bytearray) -> int:  # type: ignore[override]
        wanted = min(len(buffer), self._size - self._pos)
        if wanted <= 0:
            return 0
        end = self._pos + wanted
        buffer_end = self._buffer_start + len(self._buffer)
        if not (self._buffer_start <= self._pos and end <= buffer_end):
            fetch_end = min(self._size, self._pos + max(wanted, MIN_FETCH))
            self._buffer = self._fetch(self._pos, fetch_end)
            self._buffer_start = self._pos
        offset = self._pos - self._buffer_start
        buffer[:wanted] = self._buffer[offset : offset + wanted]
        self._pos = end
        return wanted

    def _fetch(self, start: int, end: int) -> bytes:
        """Fetch bytes [start, end) of the virtual file, splitting the range across parts."""
        chunks = []
        for url, part_start, part_size in zip(self._urls, self._starts, self._sizes, strict=True):
            part_end = part_start + part_size
            lo, hi = max(start, part_start), min(end, part_end)
            if lo < hi:
                chunks.append(self._get_range(url, lo - part_start, hi - part_start - 1))
                self.requests += 1
                self.bytes_fetched += hi - lo
        return b"".join(chunks)
