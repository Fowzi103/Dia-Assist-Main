"""Secure file parsing for medical reports."""

import io
import os
import re
from datetime import datetime

from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {"pdf", "txt", "doc", "docx", "jpg", "jpeg", "png"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

# Rough MIME type map (extension -> acceptable mime types)
MIME_MAP = {
    "pdf": ["application/pdf"],
    "txt": ["text/plain"],
    "doc": ["application/msword"],
    "docx": [
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ],
    "jpg": ["image/jpeg"],
    "jpeg": ["image/jpeg"],
    "png": ["image/png"],
}


def allowed_extension(filename):
    if not filename or "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in ALLOWED_EXTENSIONS


def get_extension(filename):
    if filename and "." in filename:
        return filename.rsplit(".", 1)[1].lower()
    return ""


def safe_filename(filename):
    name = secure_filename(filename or "")
    if not name:
        name = f"upload_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    # Ensure the extension survives
    suffix = ""
    if "." in (filename or ""):
        suffix = "." + get_extension(filename)
        base = name.rsplit(".", 1)[0] if "." in name else name
        name = base + suffix
    return name


def validate_file(file_storage):
    """Return (ok, error_message, ext)."""
    if file_storage is None or file_storage.filename == "":
        return False, "No file selected. Please choose a file to upload.", ""

    filename = file_storage.filename
    if not allowed_extension(filename):
        return False, (
            "Unsupported file type. Allowed: PDF, TXT, DOC, DOCX, JPG, JPEG, PNG."
        ), ""

    file_storage.stream.seek(0, os.SEEK_END)
    size = file_storage.stream.tell()
    file_storage.stream.seek(0)
    if size == 0:
        return False, "The uploaded file is empty.", ""
    if size > MAX_FILE_SIZE:
        return False, (
            f"File too large ({size // (1024 * 1024)} MB). Please upload a file under 10 MB."
        ), ""

    # MIME validation where practical
    ext = get_extension(filename)
    mime = (getattr(file_storage, "mimetype", "") or "").lower()
    if mime and MIME_MAP.get(ext):
        acceptable = MIME_MAP[ext]
        if mime not in acceptable and not mime.startswith("application/octet-stream"):
            return False, (
                f"File MIME type ({mime}) does not match its extension (.{ext})."
            ), ""

    return True, "", ext


def _extract_with_fitz(pdf_stream):
    """Extract text from a PDF using PyMuPDF."""
    import fitz

    text_chunks = []
    with fitz.open(stream=pdf_stream, filetype="pdf") as doc:
        for page in doc:
            text_chunks.append(page.get_text())
    return "\n".join(text_chunks)


def _extract_docx(byte_stream):
    """Extract text from a DOCX using python-docx."""
    from docx import Document

    doc = Document(io.BytesIO(byte_stream))
    parts = [p.text for p in doc.paragraphs if p.text.strip()]
    for table in doc.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells]
            row_text = " | ".join([c for c in cells if c])
            if row_text:
                parts.append(row_text)
    return "\n".join(parts)


def _extract_doc(byte_stream):
    """Best-effort plain text extract for old .doc binaries."""
    try:
        text = byte_stream.decode("latin-1")
        text = re.sub(r"[^\x20-\x7E\n\t]", " ", text)
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        return "\n".join(lines)
    except Exception:
        return ""


def _extract_image_ocr(file_storage_content, ext):
    """OCR text from image bytes using Pillow + pytesseract (graceful failure)."""
    from PIL import Image

    image = Image.open(io.BytesIO(file_storage_content)).convert("L")
    try:
        import pytesseract
    except Exception:
        return "", "OCR engine (pytesseract) unavailable. Install Tesseract to read images."

    try:
        text = pytesseract.image_to_string(image)
        return text, ""
    except Exception as exc:
        return "", f"OCR failed on this image: {exc}"


def extract_text(file_storage, ext):
    """Extract raw text from an uploaded file.

    Returns a tuple (text, error_message). If text is empty and error non-empty,
    the caller should surface the error.
    """
    file_storage.stream.seek(0)
    raw = file_storage.read()

    if ext == "txt":
        try:
            return raw.decode("utf-8", errors="replace"), ""
        except Exception as exc:
            return "", f"Could not decode text file: {exc}"

    if ext == "pdf":
        scanned_fallback = False
        try:
            text = _extract_with_fitz(io.BytesIO(raw))
            if text.strip():
                return text, ""
            scanned_fallback = True
        except Exception as exc:
            raise ValueError(f"Could not read PDF file. It may be corrupt: {exc}")

        # Scanned PDF -> try OCR on rendered pages
        if scanned_fallback:
            try:
                import fitz

                ocr_parts = []
                with fitz.open(stream=raw, filetype="pdf") as doc:
                    for page in doc:
                        pix = page.get_pixmap(dpi=180)
                        img_bytes = pix.tobytes("png")
                        text, err = _extract_image_ocr(img_bytes, "png")
                        if text.strip():
                            ocr_parts.append(text)
                if ocr_parts:
                    return "\n".join(ocr_parts), ""
                return "", (
                    "The PDF contains no extractable text and OCR returned no text. "
                    "It may be password-protected or contain only images."
                )
            except Exception as exc:
                return "", f"Scanned-PDF OCR failed: {exc}"

    if ext == "docx":
        try:
            return _extract_docx(raw), ""
        except Exception as exc:
            raise ValueError(f"Could not read DOCX file: it may be corrupt or old format. ({exc})")

    if ext == "doc":
        text = _extract_doc(raw)
        if not text.strip():
            return "", (
                "Could not read the legacy .doc file. Please convert it to .docx and retry."
            )
        return text, ""

    if ext in ("jpg", "jpeg", "png"):
        text, err = _extract_image_ocr(raw, ext)
        return text, err

    return "", "Unsupported file type."


def estimate_confidence(text, analysis, extraction_error=""):
    """Return an explicitly non-validated application estimate for review UX."""
    if not text or not text.strip():
        return 0
    score = 68
    if extraction_error:
        score -= 18
    if len(text.strip()) > 180:
        score += 8
    if analysis:
        score += min(18, len(analysis) * 3)
    return max(25, min(98, score))