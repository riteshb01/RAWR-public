"""
Tests for the Document Parser — TXT extraction, text cleaning, file routing.
PDF/DOCX parsing are not tested here since they require binary fixtures.
"""
import os
import pytest
import tempfile

from core.date_parser.document_parser import (
    DocumentParser,
    clean_extracted_text,
    extract_txt_text,
)


# ─────────────────────────────────────────────────────
# clean_extracted_text()
# ─────────────────────────────────────────────────────

class TestCleanExtractedText:
    """Tests for text normalization and cleanup."""

    def test_removes_page_numbers(self):
        text = "Some content\n42\nMore content"
        result = clean_extracted_text(text)
        assert "42" not in result.split('\n')

    def test_removes_page_x_of_y(self):
        text = "Some content\nPage 3 of 10\nMore content"
        result = clean_extracted_text(text)
        assert "Page 3 of 10" not in result

    def test_normalizes_line_endings(self):
        text = "Line 1\r\nLine 2\rLine 3"
        result = clean_extracted_text(text)
        assert '\r' not in result

    def test_collapses_blank_lines(self):
        text = "Line 1\n\n\n\n\nLine 2"
        result = clean_extracted_text(text)
        assert "\n\n\n" not in result

    def test_removes_decorative_lines(self):
        text = "Title\n============\nContent"
        result = clean_extracted_text(text)
        assert "============" not in result

    def test_strips_line_whitespace(self):
        text = "   indented line   \n  another   "
        result = clean_extracted_text(text)
        lines = result.split('\n')
        for line in lines:
            assert line == line.strip()

    def test_empty_input(self):
        assert clean_extracted_text("") == ""
        assert clean_extracted_text(None) == ""


# ─────────────────────────────────────────────────────
# extract_txt_text()
# ─────────────────────────────────────────────────────

class TestExtractTxtText:
    """Tests for plain text file extraction."""

    def test_reads_utf8_file(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write("CS 101 Syllabus\nMidterm: March 15, 2026\nFinal: May 8, 2026")
            f.flush()
            result = extract_txt_text(f.name)
        os.unlink(f.name)
        assert "CS 101 Syllabus" in result
        assert "Midterm" in result

    def test_reads_latin1_file(self):
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.txt', delete=False) as f:
            f.write("Café résumé naïve".encode('latin-1'))
            f.flush()
            result = extract_txt_text(f.name)
        os.unlink(f.name)
        assert "Caf" in result  # Should decode without crashing


# ─────────────────────────────────────────────────────
# DocumentParser class
# ─────────────────────────────────────────────────────

class TestDocumentParser:
    """Tests for the unified parser routing."""

    def setup_method(self):
        self.parser = DocumentParser()

    def test_supported_extensions(self):
        assert '.pdf' in self.parser.SUPPORTED_EXTENSIONS
        assert '.txt' in self.parser.SUPPORTED_EXTENSIONS
        assert '.docx' in self.parser.SUPPORTED_EXTENSIONS

    def test_rejects_unsupported_extension(self):
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            f.write(b"fake content")
            f.flush()
        with pytest.raises(ValueError, match="Unsupported file type"):
            self.parser.parse(f.name)
        os.unlink(f.name)

    def test_rejects_nonexistent_file(self):
        with pytest.raises(FileNotFoundError):
            self.parser.parse("/nonexistent/path/file.pdf")

    def test_parses_txt_file(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write("Homework 1 due March 12\nQuiz February 20")
            f.flush()
            result = self.parser.parse(f.name)
        os.unlink(f.name)
        assert "Homework" in result
        assert "Quiz" in result

    def test_get_file_metadata(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write("test content here")
            f.flush()
            meta = self.parser.get_file_metadata(f.name)
        os.unlink(f.name)
        assert meta['extension'] == '.txt'
        assert meta['size_bytes'] > 0
        assert meta['size_kb'] > 0
