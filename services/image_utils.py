import io
from typing import Tuple
from PIL import Image

MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB

JPEG_MAGIC = b"\xff\xd8\xff"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


class ImageValidationError(ValueError):
    pass


def validate_and_sanitize_image(raw_bytes: bytes, filename: str = "") -> Tuple[bytes, str, str]:
    """
    Validates uploaded image against strict DPDP and security criteria:
    - Max size 5 MB
    - Validates magic bytes (detects spoofed extensions)
    - Verifies valid image integrity via Pillow
    - Re-encodes to strip all EXIF metadata and hidden payloads
    
    Returns:
        Tuple of (clean_bytes, file_extension, mime_type)
    """
    if len(raw_bytes) > MAX_FILE_SIZE_BYTES:
        raise ImageValidationError(f"File exceeds maximum allowed size of 5 MB ({len(raw_bytes)} bytes)")

    if len(raw_bytes) < 8:
        raise ImageValidationError("File is too small or empty to be a valid image")

    # Magic byte validation
    is_jpeg = raw_bytes.startswith(JPEG_MAGIC)
    is_png = raw_bytes.startswith(PNG_MAGIC)

    if not (is_jpeg or is_png):
        raise ImageValidationError("Invalid image format. Only authentic JPEG and PNG files are accepted (magic bytes failed)")

    try:
        with Image.open(io.BytesIO(raw_bytes)) as img:
            img.verify()
    except Exception as exc:
        raise ImageValidationError(f"Image integrity check failed: {str(exc)}") from exc

    # Re-open for re-encoding (verify closes file pointers in PIL)
    try:
        with Image.open(io.BytesIO(raw_bytes)) as img:
            fmt = img.format
            if fmt not in ("JPEG", "PNG"):
                raise ImageValidationError(f"Unsupported image format: {fmt}. Only JPEG and PNG are allowed.")

            out_io = io.BytesIO()
            if fmt == "PNG":
                # Preserve transparency if RGBA/LA, otherwise convert to RGB
                if img.mode in ("RGBA", "LA", "P"):
                    clean_img = img.convert("RGBA")
                else:
                    clean_img = img.convert("RGB")
                clean_img.save(out_io, format="PNG", optimize=True)
                ext = "png"
                mime = "image/png"
            else:
                clean_img = img.convert("RGB")
                clean_img.save(out_io, format="JPEG", quality=90, optimize=True)
                ext = "jpg"
                mime = "image/jpeg"

            clean_bytes = out_io.getvalue()
            return clean_bytes, ext, mime
    except Exception as exc:
        if isinstance(exc, ImageValidationError):
            raise
        raise ImageValidationError(f"Failed to sanitize and re-encode image: {str(exc)}") from exc
