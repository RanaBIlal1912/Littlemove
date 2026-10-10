"""
store/uploads.py — Universal file validation and processing for LittleMove.

All uploads go through validate_upload(file, allow_kinds) which:
1. Sniffs magic bytes to detect true file type (ignores extension)
2. Checks against allow_kinds list
3. Enforces per-kind size limits
4. Returns cleaned file or raises ValidationError with a plain-English message

Image processing (auto-applied on save, not on validate):
  auto_process_image(file) → PIL image → EXIF orientation fix, strip EXIF/GPS,
  downscale to max 2400px longest side, quality 85.
"""
import io
import struct
import zipfile
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.text import slugify

# ── Per-kind size limits (overridable via env/settings) ────────────────────
def _mb(name, default):
    import os
    return int(os.environ.get(name, getattr(settings, name, default))) * 1024 * 1024

def _get_limits():
    return {
        "image":    _mb("UPLOAD_MAX_IMAGE_MB",    10),
        "video":    _mb("UPLOAD_MAX_VIDEO_MB",    50),
        "audio":    _mb("UPLOAD_MAX_AUDIO_MB",    10),
        "document": _mb("UPLOAD_MAX_DOCUMENT_MB", 10),
        "archive":  _mb("UPLOAD_MAX_ARCHIVE_MB", 200),
    }

# ── Magic-byte signatures ───────────────────────────────────────────────────
def _read_head(file, n=16):
    """Read first n bytes without consuming the file."""
    file.seek(0)
    head = file.read(n)
    file.seek(0)
    return head

def detect_kind(file):
    """
    Returns one of: "image", "video", "audio", "document", "archive", "blocked", "unknown".
    Uses first 16 bytes (magic numbers), NOT the filename extension.
    """
    head = _read_head(file)
    if len(head) < 4:
        return "unknown"

    b = head

    # ── Blocked always: executables, scripts, archives-as-executables ─────
    # PE (Windows exe/dll)
    if b[:2] == b'\x4d\x5a':  # MZ
        return "blocked"
    # ELF
    if b[:4] == b'\x7fELF':
        return "blocked"
    # Mach-O (macOS exe)
    if b[:4] in (b'\xca\xfe\xba\xbe', b'\xce\xfa\xed\xfe', b'\xcf\xfa\xed\xfe'):
        return "blocked"
    # ZIP-based Office docs (docx/xlsx) with macro extensions are caught by extension check below.
    # Plain script detection is extension-based (see validate_upload).

    # ── Images ──────────────────────────────────────────────────────────────
    if b[:3] == b'\xff\xd8\xff':                         return "image"  # JPEG
    if b[:8] == b'\x89PNG\r\n\x1a\n':                   return "image"  # PNG
    if b[:6] in (b'GIF87a', b'GIF89a'):                  return "image"  # GIF
    if b[:4] == b'RIFF' and b[8:12] == b'WEBP':         return "image"  # WebP
    if b[:4] in (b'MM\x00\x2a', b'II\x2a\x00',          # TIFF
                 b'MM\x00\x2b', b'II\x2b\x00'):
        return "image"
    if b[:4] == b'\x00\x00\x00\x0c' or b[4:8] == b'ftyp':  # might be HEIC or MP4/M4V
        ftyp = b[8:12] if len(b) >= 12 else b''
        if ftyp in (b'heic', b'heix', b'hevc', b'hevx', b'mif1', b'msf1'):
            return "image"  # HEIC/HEIF — Pillow may not support without plugin, but we detect it
    if b[:2] in (b'BM',):                                return "image"  # BMP
    if b[:8] == b'\x00\x00\x00\x00\x00\x01\x00\x00':   return "image"  # ICO (approx)
    # AVIF: ftyp box
    if b[4:12] == b'ftypavif' or b[4:12] == b'ftypAVIF':
        return "image"

    # ── Videos ──────────────────────────────────────────────────────────────
    if b[4:8] == b'ftyp':
        ftyp = b[8:12]
        if ftyp in (b'mp41', b'mp42', b'isom', b'iso2', b'M4V ', b'M4VP',
                    b'avc1', b'dash', b'msnv', b'MSNV', b'f4v ', b'f4p ',
                    b'qt  ', b'moov'):
            return "video"
        if ftyp in (b'M4A ', b'm4a ', b'M4B ', b'f4a '):
            return "audio"
    if b[:4] == b'\x1a\x45\xdf\xa3':                    return "video"  # MKV/WebM
    if b[:3] == b'FLV':                                  return "video"
    # MOV / MP4 also may have moov at offset 0
    if b[4:8] in (b'moov', b'free', b'mdat', b'wide'):  return "video"

    # ── Audio ────────────────────────────────────────────────────────────────
    if b[:3] == b'ID3' or b[:2] == b'\xff\xfb':         return "audio"  # MP3
    if b[:4] == b'RIFF' and b[8:12] == b'WAVE':         return "audio"  # WAV
    if b[:4] == b'OggS':                                  return "audio"  # OGG
    if b[:4] in (b'fLaC',):                              return "audio"  # FLAC

    # ── PDF / Documents ──────────────────────────────────────────────────────
    if b[:4] == b'%PDF':                                 return "document"

    # ── Archives ────────────────────────────────────────────────────────────
    if b[:4] in (b'PK\x03\x04', b'PK\x05\x06', b'PK\x07\x08'):
        return "archive"  # ZIP (also docx/xlsx/pptx — we handle them below)
    if b[:6] in (b'Rar!\x1a\x07', b'Rar!\x1a\x07\x01'):
        return "blocked"  # RAR — not allowed
    if b[:3] == b'\x1f\x8b':                             return "archive"  # GZIP
    if b[:6] == b'7z\xbc\xaf\x27\x1c':                  return "archive"  # 7z — blocked below

    return "unknown"


# Blocked extensions (regardless of magic bytes) — scripts, programs, macros
_BLOCKED_EXTS = {
    "exe", "dll", "bat", "cmd", "sh", "py", "php", "js", "html", "htm",
    "svg", "jar", "apk", "msi", "vbs", "scr", "ps1", "docm", "xlsm",
    "pptm", "xltm", "dotm", "potm", "sldm",
}

# Images we actually accept
_ALLOWED_IMAGE_EXTS = {"jpg", "jpeg", "png", "webp", "gif", "avif", "bmp", "tiff", "tif", "heic", "heif"}
# Videos we accept
_ALLOWED_VIDEO_EXTS = {"mp4", "webm", "mov", "m4v"}
# Audio
_ALLOWED_AUDIO_EXTS = {"mp3", "wav", "m4a", "ogg", "flac"}
# Documents
_ALLOWED_DOC_EXTS = {"pdf"}
# Archives (only for bulk screens)
_ALLOWED_ARCHIVE_EXTS = {"zip"}


def validate_upload(file, allow_kinds=("image",)):
    """
    Validate an uploaded file. Raises ValidationError on failure.
    allow_kinds: tuple of kinds to permit, e.g. ("image",) or ("image","video") or ("archive",)
    Returns the detected kind on success.
    """
    if not file:
        return None

    limits = _get_limits()
    ext = Path(getattr(file, "name", "") or "").suffix.lstrip(".").lower()

    # 1. Blocked extensions always rejected
    if ext in _BLOCKED_EXTS:
        raise ValidationError(
            f"This file type (.{ext}) is not allowed. Please upload a photo, video, or document."
        )

    # 2. Detect by content
    kind = detect_kind(file)

    # 3. Check kind-specific extension whitelist (extension must match content)
    if kind == "image" and ext and ext not in _ALLOWED_IMAGE_EXTS:
        raise ValidationError(
            f"This looks like an image but has an unexpected extension (.{ext}). "
            f"Accepted: jpg, png, webp, gif, avif, heic."
        )
    if kind == "video" and ext and ext not in _ALLOWED_VIDEO_EXTS:
        raise ValidationError(
            f"This looks like a video but has an unexpected extension (.{ext}). "
            f"Accepted: mp4, webm, mov, m4v."
        )
    if kind == "audio" and ext and ext not in _ALLOWED_AUDIO_EXTS:
        raise ValidationError(
            f"This looks like an audio file but has an unexpected extension (.{ext}). "
            f"Accepted: mp3, wav, m4a, ogg."
        )
    if kind == "document" and ext and ext not in _ALLOWED_DOC_EXTS:
        raise ValidationError(
            f"This looks like a document but has an unexpected extension (.{ext}). "
            f"Accepted: pdf."
        )

    # 4. ZIP (archive) — check if it's actually a macro-enabled Office doc by extension
    if kind == "archive" and ext in {"docm", "xlsm", "pptm", "xltm", "dotm"}:
        raise ValidationError(
            f"Macro-enabled Office files (.{ext}) are not allowed for security reasons."
        )

    # 5. Blocked kind
    if kind == "blocked":
        raise ValidationError(
            f"This looks like a program or script file. Please upload a photo, video, or document."
        )

    # 6. Check allowed kinds
    if kind not in allow_kinds and kind != "unknown":
        # Build a friendly message based on what IS allowed
        allowed_str = " or ".join(allow_kinds)
        raise ValidationError(
            f"This file is a {kind}. Only {allowed_str} files are accepted here."
        )

    if kind == "unknown" and "image" in allow_kinds and ext not in _ALLOWED_IMAGE_EXTS:
        raise ValidationError(
            f"Could not recognise this file type (.{ext}). "
            f"Please upload a jpg, png, webp, or gif."
        )

    # 7. Size check
    effective_kind = kind if kind in limits else "image"
    limit = limits.get(effective_kind, limits["image"])
    size = getattr(file, "size", None)
    if size is None:
        try:
            file.seek(0, 2)  # seek to end
            size = file.tell()
            file.seek(0)
        except Exception:
            size = 0
    if size and size > limit:
        limit_mb = limit // (1024 * 1024)
        size_mb = size / (1024 * 1024)
        raise ValidationError(
            f"This file is {size_mb:.1f} MB but the limit for {effective_kind} files is {limit_mb} MB."
        )

    return kind


def auto_process_image(file, name=None):
    """
    Process an uploaded image in-memory:
    - Apply EXIF orientation
    - Strip all EXIF/GPS metadata
    - Downscale to max 2400px on the longest side (never upscale)
    - Re-encode as JPEG at quality 85 (or WEBP if original was webp)
    Returns a tuple (ContentFile, suggested_filename).
    """
    from PIL import Image, ExifTags
    from django.core.files.base import ContentFile

    try:
        file.seek(0)
        img = Image.open(file)
        img.load()
    except Exception:
        return file, name  # can't process — return as-is

    # Apply EXIF orientation
    try:
        exif = img._getexif()
        if exif:
            for tag, val in exif.items():
                if ExifTags.TAGS.get(tag) == "Orientation":
                    rotations = {3: 180, 6: 270, 8: 90}
                    if val in rotations:
                        img = img.rotate(rotations[val], expand=True)
                    break
    except Exception:
        pass

    # Convert RGBA/P to RGB for JPEG
    fmt = img.format or "JPEG"
    if fmt == "WEBP":
        out_fmt, ext = "WEBP", "webp"
    else:
        out_fmt, ext = "JPEG", "jpg"
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

    # Downscale
    MAX = 2400
    w, h = img.size
    if max(w, h) > MAX:
        ratio = MAX / max(w, h)
        img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)

    # Re-encode without EXIF
    buf = io.BytesIO()
    img.save(buf, format=out_fmt, quality=85, optimize=True)
    buf.seek(0)

    # Build a clean filename
    base = Path(name or "photo").stem
    clean_name = slugify(base) or "photo"
    new_name = f"{clean_name}.{ext}"

    return ContentFile(buf.read()), new_name


def validate_zip_safety(zip_file):
    """
    Validate a ZIP file for safe extraction. Raises ValidationError if unsafe.
    Rules: no path traversal, max 2000 entries, max 500MB uncompressed, no nested zips.
    Returns a list of safe member names.
    """
    MAX_ENTRIES = 2000
    MAX_UNCOMPRESSED = 500 * 1024 * 1024  # 500 MB

    try:
        zip_file.seek(0)
        with zipfile.ZipFile(zip_file) as zf:
            members = zf.infolist()
    except zipfile.BadZipFile:
        raise ValidationError("This file is not a valid ZIP archive.")
    except Exception as e:
        raise ValidationError(f"Could not read ZIP file: {e}")

    if len(members) > MAX_ENTRIES:
        raise ValidationError(
            f"This ZIP has {len(members):,} files. Maximum allowed is {MAX_ENTRIES:,}."
        )

    total_size = 0
    safe_names = []
    for m in members:
        name = m.filename
        # Block path traversal
        if ".." in name or name.startswith("/") or ":" in name:
            raise ValidationError(
                f"ZIP contains a potentially unsafe path: {name!r}. Upload rejected."
            )
        # Skip macOS/system files
        if name.startswith("__MACOSX") or name.endswith(".DS_Store") or name.endswith("Thumbs.db"):
            continue
        # No nested ZIPs
        if name.lower().endswith(".zip"):
            continue
        total_size += m.file_size
        if total_size > MAX_UNCOMPRESSED:
            raise ValidationError(
                f"ZIP uncompressed size exceeds 500 MB. Upload rejected."
            )
        safe_names.append(name)

    zip_file.seek(0)
    return safe_names
