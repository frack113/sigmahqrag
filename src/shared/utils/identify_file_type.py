from __future__ import annotations

import csv
import io
import json
from collections.abc import Callable
from enum import Enum
from pathlib import Path

import puremagic
import yaml

from src.core.sigma.models import is_sigma_rule_candidate

UTF8_BOM = b"\xef\xbb\xbf"
MAX_FILE_SIZE = 100 * 1024 * 1024
MAGIC_HEADER_SIZE = 4096


class FileType(Enum):
    PDF = "pdf"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    ARCHIVE = "archive"
    OFFICE_DOCUMENT = "office_document"
    EXECUTABLE = "executable"
    SIGMA_RULE = "sigma_rule"
    YAML = "yaml"
    JSON = "json"
    CSV = "csv"
    MARKDOWN = "markdown"
    HTML = "html"
    PLAIN_TEXT = "plain_text"
    UNKNOWN = "unknown"


SIGMA_RULE_EXTENSIONS: frozenset[str] = frozenset({".yml", ".yaml"})

SUPPORTED_DOC_EXTENSION_MAP: dict[str, FileType] = {
    ".md": FileType.MARKDOWN,
    ".markdown": FileType.MARKDOWN,
    ".pdf": FileType.PDF,
    ".txt": FileType.PLAIN_TEXT,
    ".text": FileType.PLAIN_TEXT,
    ".rst": FileType.PLAIN_TEXT,
    ".adoc": FileType.PLAIN_TEXT,
    ".asciidoc": FileType.PLAIN_TEXT,
    ".html": FileType.HTML,
    ".htm": FileType.HTML,
    ".docx": FileType.OFFICE_DOCUMENT,
    ".pptx": FileType.OFFICE_DOCUMENT,
    ".xlsx": FileType.OFFICE_DOCUMENT,
    ".odt": FileType.OFFICE_DOCUMENT,
    ".ods": FileType.OFFICE_DOCUMENT,
    ".odp": FileType.OFFICE_DOCUMENT,
}

SUPPORTED_REFERENCE_DOC_TYPES: set[str] = {
    FileType.MARKDOWN.value,
    FileType.PDF.value,
    FileType.PLAIN_TEXT.value,
    FileType.HTML.value,
    FileType.OFFICE_DOCUMENT.value,
}

PUREMAGIC_TYPE_MAP: dict[str, FileType] = {
    ".pdf": FileType.PDF,
    ".png": FileType.IMAGE,
    ".jpg": FileType.IMAGE,
    ".jpeg": FileType.IMAGE,
    ".gif": FileType.IMAGE,
    ".webp": FileType.IMAGE,
    ".bmp": FileType.IMAGE,
    ".tiff": FileType.IMAGE,
    ".tif": FileType.IMAGE,
    ".svg": FileType.IMAGE,
    ".ico": FileType.IMAGE,
    ".mp3": FileType.AUDIO,
    ".wav": FileType.AUDIO,
    ".flac": FileType.AUDIO,
    ".ogg": FileType.AUDIO,
    ".oga": FileType.AUDIO,
    ".m4a": FileType.AUDIO,
    ".aac": FileType.AUDIO,
    ".mp4": FileType.VIDEO,
    ".avi": FileType.VIDEO,
    ".mkv": FileType.VIDEO,
    ".mov": FileType.VIDEO,
    ".webm": FileType.VIDEO,
    ".zip": FileType.ARCHIVE,
    ".tar": FileType.ARCHIVE,
    ".gz": FileType.ARCHIVE,
    ".bz2": FileType.ARCHIVE,
    ".xz": FileType.ARCHIVE,
    ".rar": FileType.ARCHIVE,
    ".7z": FileType.ARCHIVE,
    ".docx": FileType.OFFICE_DOCUMENT,
    ".xlsx": FileType.OFFICE_DOCUMENT,
    ".pptx": FileType.OFFICE_DOCUMENT,
    ".odt": FileType.OFFICE_DOCUMENT,
    ".ods": FileType.OFFICE_DOCUMENT,
    ".odp": FileType.OFFICE_DOCUMENT,
    ".exe": FileType.EXECUTABLE,
    ".dll": FileType.EXECUTABLE,
    ".elf": FileType.EXECUTABLE,
    ".wasm": FileType.EXECUTABLE,
}


def _detect_via_puremagic(header: bytes, file_path: str = "") -> FileType | None:
    try:
        results = puremagic.magic_string(header)
    except Exception:
        return None
    if not results:
        return None
    matched: list[tuple[str, FileType]] = []
    for r in results:
        ext = r.extension.lower()
        if ext in PUREMAGIC_TYPE_MAP:
            matched.append((ext, PUREMAGIC_TYPE_MAP[ext]))
    if not matched:
        for r in results:
            if not r.extension and "elf" in r.name.lower():
                matched.append((".elf", FileType.EXECUTABLE))
                break
    if not matched:
        return None
    file_ext = Path(file_path).suffix.lower() if file_path else ""
    for ext, ft in matched:
        if ext == file_ext:
            return ft
    return matched[0][1]


def _is_sigma_rule(file_path: str, content: str) -> bool:
    ext = Path(file_path).suffix.lower()
    if ext not in (".yml", ".yaml"):
        return False
    return is_sigma_rule_candidate(yaml.safe_load(content))


def _is_yaml(file_path: str, content: str) -> bool:
    try:
        ext = Path(file_path).suffix.lower()
        if ext not in (".yml", ".yaml"):
            return False
        data = yaml.safe_load(content)
        return isinstance(data, dict)
    except Exception:
        return False


def _is_json(file_path: str, content: str) -> bool:
    try:
        ext = Path(file_path).suffix.lower()
        if ext != ".json":
            return False
        json.loads(content)
        return True
    except Exception:
        return False


def _is_csv(file_path: str, content: str) -> bool:
    try:
        ext = Path(file_path).suffix.lower()
        if ext != ".csv":
            return False
        sniffer = csv.Sniffer()
        if not sniffer.has_header(content):
            return False
        reader = csv.reader(io.StringIO(content))
        rows = [r for r in reader if any(cell.strip() for cell in r)]
        return len(rows) >= 2
    except Exception:
        return False


def _is_markdown(file_path: str, content: str) -> bool:
    return Path(file_path).suffix.lower() == ".md"


def _is_html(file_path: str, content: str) -> bool:
    return Path(file_path).suffix.lower() in (".html", ".htm")


def _is_plain_text(file_path: str, content: str) -> bool:
    return True


DETECTION_REGISTRY: tuple[tuple[FileType, Callable[[str, str], bool]], ...] = (
    (FileType.SIGMA_RULE, _is_sigma_rule),
    (FileType.YAML, _is_yaml),
    (FileType.JSON, _is_json),
    (FileType.CSV, _is_csv),
    (FileType.MARKDOWN, _is_markdown),
    (FileType.HTML, _is_html),
    (FileType.PLAIN_TEXT, _is_plain_text),
)


def identify(file_path: str | Path) -> FileType:
    if not file_path:
        raise ValueError("file_path must not be empty")

    path = Path(file_path)

    if not str(path).strip():
        raise ValueError("file_path must not be empty")

    try:
        size = path.stat().st_size
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {file_path}") from None

    if size > MAX_FILE_SIZE:
        return FileType.UNKNOWN

    if size == 0:
        return FileType.UNKNOWN

    try:
        with open(path, "rb") as f:
            header = f.read(MAGIC_HEADER_SIZE)
    except OSError:
        raise

    if not header:
        return FileType.UNKNOWN

    if header.startswith(UTF8_BOM):
        header = header[len(UTF8_BOM) :]
        if not header:
            return FileType.UNKNOWN

    result = _detect_via_puremagic(header, str(path))
    if result is not None:
        return result

    if b"\x00" in header:
        return FileType.UNKNOWN

    try:
        with open(path, "rb") as f:
            raw = f.read()
    except OSError:
        raise

    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError:
        return FileType.UNKNOWN

    for ftype, detector in DETECTION_REGISTRY:
        try:
            if detector(str(path), content):
                return ftype
        except Exception:
            continue

    return FileType.UNKNOWN
