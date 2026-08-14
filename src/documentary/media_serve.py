"""Serve project MP4s with HTTP Range so mobile downloads/playback can resume."""
from __future__ import annotations

from pathlib import Path
from typing import Iterator
from urllib.parse import quote

from fastapi import HTTPException, Request
from fastapi.responses import FileResponse, Response, StreamingResponse

from src.video_assembler import mp4_is_complete

_CHUNK = 1024 * 1024  # 1 MiB


def parse_byte_range(header: str | None, size: int) -> tuple[int, int, int]:
    """Return (start, end_inclusive, status). status is 200 (full) or 206 (partial)."""
    size = max(0, int(size))
    if size <= 0:
        return 0, -1, 200
    header = (header or "").strip()
    if not header.lower().startswith("bytes="):
        return 0, size - 1, 200
    spec = header.split("=", 1)[1].split(",")[0].strip()
    if "-" not in spec:
        return 0, size - 1, 200
    left, right = spec.split("-", 1)
    try:
        if left == "" and right != "":
            suffix = int(right)
            if suffix <= 0:
                return 0, size - 1, 200
            start = max(0, size - suffix)
            return start, size - 1, 206
        start = int(left) if left else 0
        end = int(right) if right else size - 1
    except ValueError:
        return 0, size - 1, 200
    start = max(0, min(start, size - 1))
    end = max(start, min(end, size - 1))
    if start == 0 and end == size - 1:
        return start, end, 200
    return start, end, 206


def content_disposition(filename: str, *, download: bool) -> str:
    safe = (filename or "video.mp4").replace('"', "").replace("\n", " ").strip() or "video.mp4"
    encoded = quote(safe)
    kind = "attachment" if download else "inline"
    return f'{kind}; filename="{safe}"; filename*=UTF-8\'\'{encoded}'


def _mp4_headers(
    *,
    filename: str,
    download: bool,
    size: int,
    start: int,
    end: int,
    status: int,
) -> dict[str, str]:
    length = max(0, end - start + 1) if size > 0 else 0
    headers = {
        "Accept-Ranges": "bytes",
        "Cache-Control": "private, max-age=0, must-revalidate",
        "Content-Disposition": content_disposition(filename, download=download),
        "Content-Length": str(length),
        "Content-Type": "video/mp4",
    }
    if status == 206 and size > 0:
        headers["Content-Range"] = f"bytes {start}-{end}/{size}"
    return headers


def _iter_local(path: Path, start: int, length: int) -> Iterator[bytes]:
    with path.open("rb") as fh:
        fh.seek(max(0, start))
        remaining = max(0, length)
        while remaining > 0:
            chunk = fh.read(min(_CHUNK, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk


def serve_project_mp4(
    request: Request,
    *,
    project_id: str,
    rel_path: str,
    download: bool,
    filename: str,
    fallback_rel: str = "",
) -> Response:
    """Serve an MP4 from local disk or stream byte ranges from Supabase.

    Never pull the whole blob into memory/disk before sending the first byte.
    That was hanging mobile downloads at ~0–2% for minutes, then restarting.
    """
    from src.documentary.project import project_dir

    path = project_dir(project_id) / rel_path
    range_header = request.headers.get("range") or request.headers.get("Range")
    method = (request.method or "GET").upper()

    if mp4_is_complete(path):
        size = path.stat().st_size
        start, end, status = parse_byte_range(range_header, size)
        headers = _mp4_headers(
            filename=filename, download=download, size=size, start=start, end=end, status=status
        )
        if method == "HEAD":
            return Response(status_code=status, headers=headers, media_type="video/mp4")
        if status == 200 and not range_header:
            # Let Starlette handle Range on subsequent requests; first hit is a plain file.
            kwargs: dict = {
                "media_type": "video/mp4",
                "headers": {
                    "Accept-Ranges": "bytes",
                    "Cache-Control": "private, max-age=0, must-revalidate",
                    "Content-Disposition": content_disposition(filename, download=download),
                },
            }
            if download:
                kwargs["filename"] = filename
            return FileResponse(path, **kwargs)
        return StreamingResponse(
            _iter_local(path, start, end - start + 1),
            status_code=status,
            media_type="video/mp4",
            headers=headers,
        )

    from src.documentary import cloud_sync

    if not cloud_sync.configured():
        raise HTTPException(404, "No hay video todavía")

    size = cloud_sync.blob_size(project_id, rel_path)
    use_rel = rel_path
    if not size and fallback_rel:
        size = cloud_sync.blob_size(project_id, fallback_rel)
        use_rel = fallback_rel
    if not size:
        raise HTTPException(404, "No hay video todavía")

    start, end, status = parse_byte_range(range_header, size)
    headers = _mp4_headers(
        filename=filename, download=download, size=size, start=start, end=end, status=status
    )
    if method == "HEAD":
        return Response(status_code=status, headers=headers, media_type="video/mp4")
    return StreamingResponse(
        cloud_sync.iter_blob(project_id, use_rel, start=start, length=end - start + 1),
        status_code=status,
        media_type="video/mp4",
        headers=headers,
    )
