# File Type Identifier

Located in `src/back/utils/identify_file_type.py`. Detects file types using magic bytes (`puremagic`) and content heuristics — zero OS dependencies.

## Supported Types

### Binary Formats (detected via puremagic)

| FileType | Extensions | Magic Bytes |
|----------|-----------|-------------|
| `PDF` | `.pdf` | `%PDF` |
| `IMAGE` | `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, `.bmp`, `.tiff`, `.tif`, `.svg`, `.ico` | PNG, JPEG, GIF, BMP, TIFF, ICO signatures |
| `AUDIO` | `.mp3`, `.wav`, `.flac`, `.ogg`, `.oga`, `.m4a`, `.aac` | ID3, RIFF/WAVE, fLaC, OggS |
| `VIDEO` | `.mp4`, `.avi`, `.mkv`, `.mov`, `.webm` | ftyp, AVI, MKV/WebM, MOV |
| `ARCHIVE` | `.zip`, `.tar`, `.gz`, `.bz2`, `.xz`, `.rar`, `.7z` | PK, gzip, bzip2, Rar, 7z |
| `OFFICE_DOCUMENT` | `.docx`, `.xlsx`, `.pptx`, `.odt`, `.ods`, `.odp` | PK (ZIP-based OOXML/ODF) |
| `EXECUTABLE` | `.exe`, `.dll`, `.elf`, `.wasm` | MZ, ELF |

**Note:** `.docx`/`.xlsx`/`.pptx` and `.zip` share the same PK magic bytes. The identifier uses the file extension as a tiebreaker: if both `.docx` and `.zip` match, the actual file extension wins.

### Text Formats (detected via DETECTION_REGISTRY)

| FileType | Extensions | Detection Logic |
|----------|-----------|-----------------|
| `SIGMA_RULE` | `.yml`, `.yaml` | YAML with `title`, `detection`, `condition` keys |
| `YAML` | `.yml`, `.yaml` | Valid YAML → dict |
| `JSON` | `.json` | Valid JSON parse |
| `CSV` | `.csv` | Header row + 2+ rows (via `csv.Sniffer`) |
| `MARKDOWN` | `.md` | Extension check (content validated upstream by UTF-8 decode) |
| `PLAIN_TEXT` | any | Fallback: any valid UTF-8 without null bytes |

### Other

| FileType | Description |
|----------|-------------|
| `UNKNOWN` | Binary without known magic, over 100MB, or empty |

## Detection Flow

1. **Guard checks:** empty path, file size (max 100MB), stat errors
2. **Header read:** 4KB, strip UTF-8 BOM if present
3. **Binary detection:** `puremagic.magic_string(header)` → `PUREMAGIC_TYPE_MAP`
4. **Null byte check:** reject binary content unknown to puremagic
5. **Full read + UTF-8 decode**
6. **Text detection:** iterate `DETECTION_REGISTRY` in order (Sigma → YAML → JSON → CSV → Markdown → Plain Text)

## Usage

```python
from src.back.utils import FileType, identify

result = identify("path/to/file.pdf")  # FileType.PDF
result = identify("path/to/rule.yml")  # FileType.SIGMA_RULE or FileType.YAML
```

## Dependencies

- `puremagic>=2.2.0` — pure Python magic byte detection (no libmagic)
- `pyyaml>=6.0` — YAML parsing for Sigma/YAML detection
- Standard library: `csv`, `io`, `json`
