"""Bulk import + replace stills for Flow (FF100-P0-003/004)."""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

from src.documentary.flow_pack import load_shot_list
from src.documentary.project import append_log, project_dir, save_project, set_checkpoint

_NUM_RE = re.compile(r"^(\d{1,4})\.(png|jpg|jpeg|webp)$", re.I)
_STILL_EXTS = (".jpg", ".jpeg", ".png", ".webp")


def still_file(images_dir: Path, number: int) -> Path | None:
    n = int(number)
    for ext in _STILL_EXTS:
        path = images_dir / f"{n:03d}{ext}"
        if path.is_file() and path.stat().st_size > 0:
            return path
    return None


def ensure_still_thumb(images_dir: Path, number: int) -> Path | None:
    """Small JPEG for the UI so we never ship 7MB PNGs to the browser."""
    n = int(number)
    thumb = images_dir / f"{n:03d}.thumb.jpg"
    src = still_file(images_dir, n)
    if src is not None:
        stale = (
            not thumb.is_file()
            or thumb.stat().st_size <= 0
            or thumb.stat().st_mtime + 0.5 < src.stat().st_mtime
        )
        if stale:
            try:
                from PIL import Image

                with Image.open(src) as im:
                    rgb = im.convert("RGB")
                    rgb.thumbnail((960, 540), Image.LANCZOS)
                    rgb.save(thumb, format="JPEG", quality=70)
            except Exception:
                return src
        if thumb.is_file() and thumb.stat().st_size > 0:
            return thumb
        return src
    if thumb.is_file() and thumb.stat().st_size > 0:
        return thumb
    return None


def write_compressed_still(dest_root: Path, num: int, data: bytes, filename: str = "") -> Path:
    """Store a YouTube-sized JPEG so uploads stay small and fast."""
    return write_compressed_named(dest_root, f"{int(num):03d}", data, filename)


def write_compressed_named(dest_root: Path, stem: str, data: bytes, filename: str = "") -> Path:
    dest_root.mkdir(parents=True, exist_ok=True)
    stem = Path(str(stem)).stem
    dest = dest_root / f"{stem}.jpg"
    suffix = Path(filename or "").suffix.lower()
    if suffix in {".jpg", ".jpeg"} and len(data) <= 850_000:
        dest.write_bytes(data)
    else:
        import io

        from PIL import Image

        with Image.open(io.BytesIO(data)) as im:
            rgb = im.convert("RGB")
            rgb.thumbnail((1920, 1080), Image.LANCZOS)
            rgb.save(dest, format="JPEG", quality=82)
    for ext in _STILL_EXTS:
        extra = dest_root / f"{stem}{ext}"
        if extra != dest and extra.exists():
            extra.unlink()
    old_thumb = dest_root / f"{stem}.thumb.jpg"
    if old_thumb.is_file():
        old_thumb.unlink()
    return dest


_MASTER_ID_RE = re.compile(r"^[A-Za-z]{2,8}_\d{3}$")


def normalize_master_id(ref_id: str) -> str:
    eid = str(ref_id or "").strip().upper().replace(".PNG", "").replace(".JPG", "").replace(".JPEG", "").replace(".WEBP", "")
    eid = Path(eid).stem
    if not _MASTER_ID_RE.match(eid):
        raise ValueError(f"Referencia inválida: {ref_id}")
    return eid


def masters_dir(project_id: str) -> Path:
    d = project_dir(project_id) / "flow-pack" / "references" / "masters"
    d.mkdir(parents=True, exist_ok=True)
    return d


def master_file(project_id: str, ref_id: str) -> Path | None:
    eid = normalize_master_id(ref_id)
    root = masters_dir(project_id)
    for ext in _STILL_EXTS:
        path = root / f"{eid}{ext}"
        if path.is_file() and path.stat().st_size > 0:
            return path
    return None


def ensure_master_thumb(project_id: str, ref_id: str) -> Path | None:
    eid = normalize_master_id(ref_id)
    root = masters_dir(project_id)
    thumb = root / f"{eid}.thumb.jpg"
    src = master_file(project_id, eid)
    if src is not None:
        stale = (
            not thumb.is_file()
            or thumb.stat().st_size <= 0
            or thumb.stat().st_mtime + 0.5 < src.stat().st_mtime
        )
        if stale:
            try:
                from PIL import Image

                with Image.open(src) as im:
                    rgb = im.convert("RGB")
                    rgb.thumbnail((960, 540), Image.LANCZOS)
                    rgb.save(thumb, format="JPEG", quality=70)
            except Exception:
                return src
        if thumb.is_file() and thumb.stat().st_size > 0:
            return thumb
        return src
    if thumb.is_file() and thumb.stat().st_size > 0:
        return thumb
    return None


def save_master_upload(project_id: str, ref_id: str, data: bytes, filename: str = "") -> dict[str, Any]:
    eid = normalize_master_id(ref_id)
    dest = write_compressed_named(masters_dir(project_id), eid, data, filename)
    thumb = ensure_master_thumb(project_id, eid)
    stored = [f"flow-pack/references/masters/{dest.name}"]
    if thumb is not None and thumb.name != dest.name:
        stored.append(f"flow-pack/references/masters/{thumb.name}")
    append_log(project_id, f"master {eid} uploaded")
    return {"id": eid, "stored": stored}


def delete_master_image(project_id: str, ref_id: str) -> dict[str, Any]:
    eid = normalize_master_id(ref_id)
    root = masters_dir(project_id)
    removed = False
    for ext in _STILL_EXTS:
        path = root / f"{eid}{ext}"
        if path.is_file():
            path.unlink()
            removed = True
    thumb = root / f"{eid}.thumb.jpg"
    if thumb.is_file():
        thumb.unlink()
        removed = True
    append_log(project_id, f"master {eid} deleted")
    return {"ok": True, "removed": removed, "id": eid}


def attach_master_status(project_id: str, masters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    from src.documentary import cloud_sync

    remote = cloud_sync.configured()
    for m in masters:
        try:
            eid = normalize_master_id(str(m.get("id") or m.get("master_filename") or ""))
        except ValueError:
            m["status"] = "MISSING"
            continue
        if master_file(project_id, eid) is None and remote:
            for name in (f"{eid}.jpg", f"{eid}.thumb.jpg", f"{eid}.png"):
                if cloud_sync.pull_one(project_id, f"flow-pack/references/masters/{name}"):
                    break
        m["status"] = "READY" if master_file(project_id, eid) else "MISSING"
    return masters


def import_images(
    project: dict[str, Any],
    source_dir: str | Path,
    *,
    min_width: int = 640,
) -> dict[str, Any]:
    """Copy numbered stills into project/images/NNN.png and validate vs shot list."""
    src = Path(source_dir).expanduser().resolve()
    if not src.is_dir():
        raise FileNotFoundError(f"Import folder not found: {src}")

    shot_list = load_shot_list(str(project["id"]))
    expected_n = int(shot_list.get("shot_count") or len(shot_list.get("shots") or []))
    expected_nums = {int(s["number"]) for s in (shot_list.get("shots") or [])}

    found: dict[int, Path] = {}
    duplicates: list[str] = []
    invalid: list[str] = []
    unknown: list[str] = []

    for p in sorted(src.iterdir()):
        if not p.is_file():
            continue
        m = _NUM_RE.match(p.name)
        if not m:
            if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
                invalid.append(p.name)
            continue
        num = int(m.group(1))
        if num in found:
            duplicates.append(p.name)
            continue
        if expected_nums and num not in expected_nums:
            unknown.append(p.name)
        found[num] = p

    dest_root = project_dir(str(project["id"])) / "images"
    dest_root.mkdir(parents=True, exist_ok=True)

    dim_issues: list[str] = []
    imported = 0
    for num, path in sorted(found.items()):
        if expected_nums and num not in expected_nums:
            continue
        dest = dest_root / f"{num:03d}.png"
        shutil.copy2(path, dest)
        imported += 1
        issue = _dim_issue(dest, min_width)
        if issue:
            dim_issues.append(f"{num:03d}: {issue}")

    missing = sorted(expected_nums - set(found.keys())) if expected_nums else []
    ready = len(expected_nums - set(missing)) if expected_nums else imported

    report = {
        "expected": expected_n,
        "ready": ready,
        "imported_files": imported,
        "missing": [f"{n:03d}" for n in missing],
        "duplicates": duplicates,
        "unknown_numbers": unknown,
        "invalid_files": invalid,
        "dimension_issues": dim_issues,
        "source_dir": str(src),
    }
    project["import_report"] = report
    set_checkpoint(project, "images_imported", ready > 0)
    if ready == expected_n and expected_n > 0:
        set_checkpoint(project, "images_imported", True)
        project["ui_step"] = "voice"
    else:
        project["ui_step"] = "images"
    save_project(project)
    sync_shot_statuses_from_images(str(project["id"]))
    append_log(str(project["id"]), f"import ready={ready}/{expected_n} missing={len(missing)}")
    return report


def sync_shot_statuses_from_images(project_id: str) -> dict[str, Any]:
    """Filesystem is source of truth: images/NNN.png → READY else MISSING."""
    from src.documentary.visual_plan import sync_ready_from_disk

    sync_ready_from_disk(project_id)
    path = project_dir(project_id) / "flow-pack" / "shot-list.json"
    if not path.exists():
        return {}
    data = load_shot_list(project_id)
    append_log(project_id, f"sync READY from images ready={data.get('ready_count')}")
    return data


def import_uploaded_images(
    project: dict[str, Any],
    files: list[tuple[str, bytes]],
    *,
    force_number: int | None = None,
    min_width: int = 640,
) -> dict[str, Any]:
    """Import images uploaded from the Studio UI.

    Filename must be like 001.png / 14.jpg unless force_number is set (single file).
    """
    shot_list = load_shot_list(str(project["id"]))
    expected_n = int(shot_list.get("shot_count") or len(shot_list.get("shots") or []))
    expected_nums = {int(s["number"]) for s in (shot_list.get("shots") or [])}

    dest_root = project_dir(str(project["id"])) / "images"
    dest_root.mkdir(parents=True, exist_ok=True)

    imported_nums: list[int] = []
    stored_rels: list[str] = []
    invalid: list[str] = []
    unknown: list[str] = []
    dim_issues: list[str] = []
    duplicates: list[str] = []
    seen: set[int] = set()

    for filename, data in files:
        name = Path(filename).name
        num: int | None = None
        if force_number is not None and len(files) == 1:
            num = int(force_number)
        else:
            m = _NUM_RE.match(name)
            if not m:
                # Also accept Flow-ish names like image_001.png / 001_something.png
                m2 = re.search(r"(?:^|[_-])(\d{1,4})(?:[_-]|\.)", name, re.I)
                if m2 and Path(name).suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
                    num = int(m2.group(1))
                else:
                    invalid.append(name)
                    continue
            else:
                num = int(m.group(1))

        assert num is not None
        if num in seen:
            duplicates.append(name)
            continue
        if expected_nums and num not in expected_nums and force_number is None:
            unknown.append(name)
            continue
        seen.add(num)

        dest = write_compressed_still(dest_root, num, data, name)
        imported_nums.append(num)
        stored_rels.append(f"images/{dest.name}")
        thumb = ensure_still_thumb(dest_root, num)
        if thumb is not None and thumb.name != dest.name:
            stored_rels.append(f"images/{thumb.name}")

    if not imported_nums:
        bits = []
        if invalid:
            bits.append(f"nombre inválido: {', '.join(invalid[:3])}")
        if unknown:
            bits.append(f"número que no existe en el plan: {', '.join(unknown[:3])}")
        if duplicates:
            bits.append("duplicadas")
        raise ValueError("No se importó ninguna imagen. " + ("; ".join(bits) or "Archivo vacío o ilegible."))

    # Ready = existing files on disk after upload
    img_root = dest_root
    ready_set = {n for n in expected_nums if still_file(img_root, n)}
    missing = sorted(expected_nums - ready_set) if expected_nums else []
    ready = len(ready_set)

    report = {
        "expected": expected_n,
        "ready": ready,
        "imported_files": len(imported_nums),
        "imported_numbers": [f"{n:03d}" for n in sorted(imported_nums)],
        "stored": stored_rels,
        "missing": [f"{n:03d}" for n in missing],
        "duplicates": duplicates,
        "unknown_numbers": unknown,
        "invalid_files": invalid,
        "dimension_issues": dim_issues,
        "source_dir": "studio_upload",
    }
    project["import_report"] = report
    set_checkpoint(project, "images_imported", ready > 0)
    if ready == expected_n and expected_n > 0:
        set_checkpoint(project, "images_imported", True)
        project["ui_step"] = "voice"
    else:
        project["ui_step"] = "images"
    save_project(project)
    return report


def replace_shot_image(project: dict[str, Any], shot_number: int, image_path: str | Path) -> Path:
    src = Path(image_path).expanduser().resolve()
    if not src.is_file():
        raise FileNotFoundError("Image file not found.")
    dest = project_dir(str(project["id"])) / "images" / f"{int(shot_number):03d}.png"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    try:
        report = dict(project.get("import_report") or {})
        miss = [m for m in (report.get("missing") or []) if m != f"{int(shot_number):03d}"]
        report["missing"] = miss
        report["ready"] = (
            int(report.get("expected") or 0) - len(miss) if report.get("expected") else report.get("ready")
        )
        project["import_report"] = report
        set_checkpoint(project, "images_imported", True)
        set_checkpoint(project, "render_ready", False)
        set_checkpoint(project, "assembly_ready", False)
        save_project(project)
    except Exception:
        pass
    sync_shot_statuses_from_images(str(project["id"]))
    append_log(str(project["id"]), f"replaced shot {int(shot_number):03d}")
    return dest


def delete_project_image(project_id: str, number: int) -> dict[str, Any]:
    """Remove one still from disk (and caller should drop the Supabase blob)."""
    n = int(number)
    root = project_dir(project_id)
    img = root / "images"
    removed = False
    for ext in _STILL_EXTS:
        dest = img / f"{n:03d}{ext}"
        if dest.is_file():
            dest.unlink()
            removed = True
    thumb = img / f"{n:03d}.thumb.jpg"
    if thumb.is_file():
        thumb.unlink()
        removed = True
    drop = root / "flow-import"
    if drop.is_dir():
        for extra in drop.glob(f"{n:03d}.*"):
            if extra.is_file():
                extra.unlink()
    append_log(project_id, f"deleted still {n:03d}")
    return {"ok": True, "removed": removed, "number": f"{n:03d}"}


def delete_all_project_images(project_id: str) -> dict[str, Any]:
    root = project_dir(project_id)
    removed = 0
    img = root / "images"
    if img.is_dir():
        for path in img.iterdir():
            if path.is_file() and (
                path.suffix.lower() in _STILL_EXTS or path.name.endswith(".thumb.jpg")
            ):
                path.unlink()
                removed += 1
    drop = root / "flow-import"
    if drop.is_dir():
        for extra in drop.iterdir():
            if extra.is_file():
                extra.unlink()
    append_log(project_id, f"deleted all stills n={removed}")
    return {"ok": True, "removed": removed}


def _refresh_after_image_delete(project: dict[str, Any]) -> dict[str, Any]:
    from src.documentary.visual_plan import sync_ready_from_disk

    pid = str(project["id"])
    sync = sync_ready_from_disk(pid)
    ready = int(sync.get("ready") or 0)
    set_checkpoint(project, "images_imported", ready > 0)
    set_checkpoint(project, "render_ready", False)
    set_checkpoint(project, "assembly_ready", False)
    if ready == 0:
        project["ui_step"] = "images"
    save_project(project)
    return sync


def list_project_images(project_id: str) -> list[Path]:
    root = project_dir(project_id) / "images"
    if not root.exists():
        return []
    return sorted(p for p in root.iterdir() if p.is_file() and p.suffix.lower() in _STILL_EXTS)


def ordered_images_for_render(project_id: str) -> tuple[list[Path], list[str]]:
    """Timeline follows the narration. Inside a moment, stills are a pool (order does not matter)."""
    shots = load_shot_list(project_id).get("shots") or []
    img_root = project_dir(project_id) / "images"
    pools: dict[str, list[Path]] = {}
    for s in shots:
        if str(s.get("visual_type") or "FLOW_REENACTMENT") not in ("FLOW_REENACTMENT", ""):
            p = still_file(img_root, int(s["number"]))
            if p is not None:
                pools.setdefault("_real", []).append(p)
            continue
        mid = str(s.get("moment_id") or "rise")
        p = still_file(img_root, int(s["number"]))
        if p is not None:
            pools.setdefault(mid, []).append(p)
    paths: list[Path] = []
    missing: list[str] = []
    seen_empty: set[str] = set()
    cursor: dict[str, int] = {}
    for s in shots:
        n = int(s["number"])
        own = still_file(img_root, n)
        vt = str(s.get("visual_type") or "FLOW_REENACTMENT")
        if vt not in ("FLOW_REENACTMENT", ""):
            if own is not None:
                paths.append(own)
            else:
                missing.append(f"{n:03d}")
            continue
        mid = str(s.get("moment_id") or "rise")
        pool = pools.get(mid) or []
        if own is not None:
            paths.append(own)
            continue
        if pool:
            i = cursor.get(mid, 0)
            paths.append(pool[i % len(pool)])
            cursor[mid] = i + 1
            continue
        label = str(s.get("moment_label") or mid)
        if label not in seen_empty:
            seen_empty.add(label)
            missing.append(label)
    return paths, missing


def _dim_issue(path: Path, min_width: int) -> str | None:
    try:
        from PIL import Image

        with Image.open(path) as im:
            w, h = im.size
        if w < min_width:
            return f"width {w} < {min_width}"
        if w < h:
            return f"portrait {w}x{h} (expected landscape 16:9)"
    except Exception:
        return None
    return None
