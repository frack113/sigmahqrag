from pathlib import Path
from unittest.mock import patch

import pytest

from src.shared.utils.identify_file_type import (
    DETECTION_REGISTRY,
    SUPPORTED_DOC_EXTENSION_MAP,
    SUPPORTED_REFERENCE_DOC_TYPES,
    FileType,
    identify,
)


class TestIdentify:
    def test_markdown_detected(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("# Title\ncontent", encoding="utf-8")
        assert identify(str(f)) == FileType.MARKDOWN

    def test_markdown_with_bom(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_bytes(b"\xef\xbb\xbf# Title\ncontent")
        assert identify(str(f)) == FileType.MARKDOWN

    def test_bom_only_file(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_bytes(b"\xef\xbb\xbf")
        assert identify(str(f)) == FileType.UNKNOWN

    def test_plain_text_file(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.txt"
        f.write_text("hello", encoding="utf-8")
        assert identify(str(f)) == FileType.PLAIN_TEXT

    def test_binary_content_in_md(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.md"
        f.write_bytes(b"text\x00with null")
        assert identify(str(f)) == FileType.UNKNOWN

    def test_null_byte_in_content(self, tmp_path: Path) -> None:
        f = tmp_path / "big.md"
        f.write_bytes(b"a" * 600 + b"\x00")
        assert identify(str(f)) == FileType.UNKNOWN

    def test_empty_file(self, tmp_path: Path) -> None:
        f = tmp_path / "empty.md"
        f.write_text("", encoding="utf-8")
        assert identify(str(f)) == FileType.UNKNOWN

    def test_binary_file(self, tmp_path: Path) -> None:
        f = tmp_path / "data.bin"
        f.write_bytes(b"\x00\x01\x02")
        assert identify(str(f)) == FileType.UNKNOWN

    def test_non_existent_file(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            identify(str(tmp_path / "nope.md"))

    def test_empty_path(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            identify("")

    def test_whitespace_path(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            identify("   ")

    def test_yaml_file_detected(self, tmp_path: Path) -> None:
        f = tmp_path / "config.yml"
        f.write_text("key: value", encoding="utf-8")
        assert identify(str(f)) == FileType.YAML

    def test_file_too_large(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("src.shared.utils.identify_file_type.MAX_FILE_SIZE", 10)
        f = tmp_path / "huge.md"
        f.write_bytes(b"x" * 11)
        assert identify(str(f)) == FileType.UNKNOWN


class TestBinaryDetection:
    def test_pdf_detected(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.pdf"
        f.write_bytes(b"%PDF-1.4\n%\x00\x00\x00\x00\x00\x00\x00\x00")
        assert identify(f) == FileType.PDF

    def test_png_detected(self, tmp_path: Path) -> None:
        f = tmp_path / "img.png"
        f.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\x00\x00\x00\x00\x00")
        assert identify(f) == FileType.IMAGE

    def test_jpeg_detected(self, tmp_path: Path) -> None:
        f = tmp_path / "photo.jpg"
        f.write_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x00\x00\x00\x00")
        assert identify(f) == FileType.IMAGE

    def test_gif_detected(self, tmp_path: Path) -> None:
        f = tmp_path / "anim.gif"
        f.write_bytes(b"GIF89a\x00\x00\x00\x00\x00\x00\x00\x00")
        assert identify(f) == FileType.IMAGE

    def test_bmp_detected(self, tmp_path: Path) -> None:
        f = tmp_path / "img.bmp"
        f.write_bytes(b"BM\x00\x00\x00\x00\x00\x00\x00\x00")
        assert identify(f) == FileType.IMAGE

    def test_tiff_detected(self, tmp_path: Path) -> None:
        f = tmp_path / "img.tiff"
        f.write_bytes(b"MM\x00\x2a\x00\x00\x00\x00\x00\x00")
        assert identify(f) == FileType.IMAGE

    def test_zip_detected(self, tmp_path: Path) -> None:
        f = tmp_path / "archive.zip"
        f.write_bytes(b"PK\x03\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00")
        assert identify(f) == FileType.ARCHIVE

    def test_docx_detected(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.docx"
        f.write_bytes(b"PK\x03\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00")
        assert identify(f) == FileType.OFFICE_DOCUMENT

    def test_gz_detected(self, tmp_path: Path) -> None:
        f = tmp_path / "data.gz"
        f.write_bytes(b"\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\x00\x00\x00")
        assert identify(f) == FileType.ARCHIVE

    def test_rar_detected(self, tmp_path: Path) -> None:
        f = tmp_path / "data.rar"
        f.write_bytes(b"Rar!\x1a\x07\x00\x00\x00\x00\x00\x00\x00\x00\x00")
        assert identify(f) == FileType.ARCHIVE

    def test_7z_detected(self, tmp_path: Path) -> None:
        f = tmp_path / "data.7z"
        f.write_bytes(b"7z\xbc\xaf\x27\x1c\x00\x00\x00\x00\x00\x00\x00")
        assert identify(f) == FileType.ARCHIVE

    def test_exe_detected(self, tmp_path: Path) -> None:
        f = tmp_path / "app.exe"
        f.write_bytes(b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00")
        assert identify(f) == FileType.EXECUTABLE

    def test_elf_detected(self, tmp_path: Path) -> None:
        f = tmp_path / "binary.elf"
        f.write_bytes(b"\x7fELF\x02\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00")
        assert identify(f) == FileType.EXECUTABLE

    def test_mp3_detected(self, tmp_path: Path) -> None:
        f = tmp_path / "song.mp3"
        f.write_bytes(b"ID3\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00")
        assert identify(f) == FileType.AUDIO

    def test_wav_detected(self, tmp_path: Path) -> None:
        f = tmp_path / "audio.wav"
        f.write_bytes(b"RIFF\x00\x00\x00\x00WAVE\x00\x00\x00\x00")
        assert identify(f) == FileType.AUDIO

    def test_webm_detected(self, tmp_path: Path) -> None:
        f = tmp_path / "video.webm"
        f.write_bytes(b"\x1aE\xdf\xa3\x93\x42\x82\x00\x00\x00\x00")
        assert identify(f) == FileType.VIDEO

    def test_mkv_detected(self, tmp_path: Path) -> None:
        f = tmp_path / "video.mkv"
        f.write_bytes(b"\x1aE\xdf\xa3\x93\x42\x82\x00\x00\x00\x00")
        assert identify(f) == FileType.VIDEO


class TestTextDetection:
    def test_sigma_rule_detected(self, tmp_path: Path) -> None:
        f = tmp_path / "rule.yml"
        f.write_text(
            "title: Test Rule\ndetection:\n  keywords: []\ncondition: any\n",
            encoding="utf-8",
        )
        assert identify(f) == FileType.SIGMA_RULE

    def test_sigma_rule_without_condition(self, tmp_path: Path) -> None:
        f = tmp_path / "partial.yml"
        f.write_text("title: Partial\ndetection: {}\n", encoding="utf-8")
        assert identify(f) == FileType.YAML

    def test_json_detected(self, tmp_path: Path) -> None:
        f = tmp_path / "data.json"
        f.write_text('{"key": "value"}', encoding="utf-8")
        assert identify(f) == FileType.JSON

    def test_json_with_yaml_keys(self, tmp_path: Path) -> None:
        f = tmp_path / "rule.json"
        f.write_text(
            '{"title": "Rule", "detection": {}, "condition": "any"}',
            encoding="utf-8",
        )
        assert identify(f) == FileType.JSON

    def test_csv_detected(self, tmp_path: Path) -> None:
        f = tmp_path / "data.csv"
        f.write_text("name,age\nAlice,30\nBob,25\n", encoding="utf-8")
        assert identify(f) == FileType.CSV

    def test_csv_without_header(self, tmp_path: Path) -> None:
        f = tmp_path / "data.csv"
        f.write_text("Alice,30\nBob,25\n", encoding="utf-8")
        assert identify(f) == FileType.PLAIN_TEXT

    def test_plain_text_fallback(self, tmp_path: Path) -> None:
        f = tmp_path / "readme.txt"
        f.write_text("hello world", encoding="utf-8")
        assert identify(f) == FileType.PLAIN_TEXT


class TestEdgeCases:
    def test_path_object_accepted(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("hello", encoding="utf-8")
        assert identify(f) == FileType.MARKDOWN

    def test_puremagic_exception(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("hello", encoding="utf-8")
        with patch(
            "src.shared.utils.identify_file_type.puremagic.magic_string",
            side_effect=Exception("boom"),
        ):
            assert identify(str(f)) == FileType.MARKDOWN

    def test_yaml_list_not_dict(self, tmp_path: Path) -> None:
        f = tmp_path / "rule.yml"
        f.write_text("- item1\n- item2\n", encoding="utf-8")
        assert identify(str(f)) == FileType.PLAIN_TEXT

    def test_yaml_parse_error(self, tmp_path: Path) -> None:
        f = tmp_path / "rule.yml"
        f.write_text("invalid: [yaml", encoding="utf-8")
        assert identify(str(f)) == FileType.PLAIN_TEXT

    def test_json_parse_error(self, tmp_path: Path) -> None:
        f = tmp_path / "data.json"
        f.write_text("not json", encoding="utf-8")
        assert identify(str(f)) == FileType.PLAIN_TEXT

    def test_oserror_reading_header(self, tmp_path: Path) -> None:
        with pytest.raises(OSError):
            identify(str(tmp_path / "somedir"))

    def test_unicode_decode_error(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.txt"
        f.write_bytes(b"\xff\xfe\x00\xff")
        assert identify(str(f)) == FileType.UNKNOWN

    def test_detector_exception_continues(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        f = tmp_path / "doc.csv"
        f.write_text("a,b\n1,2\n", encoding="utf-8")

        def broken_has_header(*args: object) -> bool:
            raise RuntimeError("boom")

        monkeypatch.setattr(
            "src.shared.utils.identify_file_type.csv.Sniffer.has_header", broken_has_header
        )
        assert identify(str(f)) == FileType.PLAIN_TEXT


class TestSupportedDocExtensionMap:
    def test_contains_markdown(self) -> None:
        assert SUPPORTED_DOC_EXTENSION_MAP[".md"] == FileType.MARKDOWN

    def test_contains_markdown_alt(self) -> None:
        assert SUPPORTED_DOC_EXTENSION_MAP[".markdown"] == FileType.MARKDOWN

    def test_contains_pdf(self) -> None:
        assert SUPPORTED_DOC_EXTENSION_MAP[".pdf"] == FileType.PDF

    def test_contains_plain_text(self) -> None:
        assert SUPPORTED_DOC_EXTENSION_MAP[".txt"] == FileType.PLAIN_TEXT
        assert SUPPORTED_DOC_EXTENSION_MAP[".rst"] == FileType.PLAIN_TEXT
        assert SUPPORTED_DOC_EXTENSION_MAP[".adoc"] == FileType.PLAIN_TEXT

    def test_contains_office_documents(self) -> None:
        assert SUPPORTED_DOC_EXTENSION_MAP[".docx"] == FileType.OFFICE_DOCUMENT
        assert SUPPORTED_DOC_EXTENSION_MAP[".pptx"] == FileType.OFFICE_DOCUMENT
        assert SUPPORTED_DOC_EXTENSION_MAP[".xlsx"] == FileType.OFFICE_DOCUMENT
        assert SUPPORTED_DOC_EXTENSION_MAP[".odt"] == FileType.OFFICE_DOCUMENT

    def test_excludes_binary_and_media(self) -> None:
        skipped = {".png", ".jpg", ".mp3", ".mp4", ".zip", ".exe"}
        for ext in skipped:
            assert ext not in SUPPORTED_DOC_EXTENSION_MAP

    def test_values_are_filetype(self) -> None:
        for ft in SUPPORTED_DOC_EXTENSION_MAP.values():
            assert isinstance(ft, FileType)


class TestSupportedReferenceDocTypes:
    def test_contains_relevant_types(self) -> None:
        assert "markdown" in SUPPORTED_REFERENCE_DOC_TYPES
        assert "html" in SUPPORTED_REFERENCE_DOC_TYPES
        assert "yaml" in SUPPORTED_REFERENCE_DOC_TYPES
        assert "pdf" in SUPPORTED_REFERENCE_DOC_TYPES
        assert "plain_text" in SUPPORTED_REFERENCE_DOC_TYPES
        assert "office_document" not in SUPPORTED_REFERENCE_DOC_TYPES

    def test_excludes_media_types(self) -> None:
        excluded = {"image", "audio", "video", "archive", "executable"}
        for ft in excluded:
            assert ft not in SUPPORTED_REFERENCE_DOC_TYPES


class TestRegistry:
    def test_registry_order_sigma_first(self) -> None:
        assert len(DETECTION_REGISTRY) >= 1
        assert DETECTION_REGISTRY[0][0] == FileType.SIGMA_RULE
