"""
PramaanX — AI module unit tests
----------------------------------
These tests validate the existing AI modules (developed by the AI team)
without requiring the full FastAPI stack or trained model files.

Run:
    cd backend
    pytest test_ai.py -v

If AI dependencies (EasyOCR, PyTorch) are not installed, tests that require
them will be automatically skipped.
"""

import sys
import os
import pytest

# Ensure backend/ is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# ─────────────────────────────────────────────────────────────────────────────
# MRZ module tests (pure Python — no ML dependencies)
# ─────────────────────────────────────────────────────────────────────────────

class TestMrzCheckDigit:
    """Tests for ai/mrz.py — all pure-Python, no EasyOCR."""

    def setup_method(self):
        from ai.mrz import calculate_check_digit, validate_check_digit, clean_mrz_line
        self.calc = calculate_check_digit
        self.validate = validate_check_digit
        self.clean = clean_mrz_line

    def test_check_digit_known_value(self):
        # ICAO Doc 9303 example: "520727" → check digit 3
        assert self.calc("520727") == "3"

    def test_validate_check_digit_pass(self):
        assert self.validate("520727", "3") is True

    def test_validate_check_digit_fail(self):
        assert self.validate("520727", "9") is False

    def test_validate_check_digit_non_digit(self):
        assert self.validate("520727", "X") is False

    def test_clean_mrz_line_strips_spaces(self):
        result = self.clean("A B C")
        assert " " not in result

    def test_clean_mrz_line_uppercase(self):
        result = self.clean("abc123")
        assert result == "ABC123"

    def test_clean_mrz_line_removes_invalid_chars(self):
        result = self.clean("A!B@C#1$2%3")
        assert result == "ABC123"


class TestMrzParser:
    """Tests for parse_td3 function."""

    def setup_method(self):
        from ai.mrz import parse_td3
        self.parse = parse_td3

    def test_parse_td3_short_lines(self):
        result = self.parse("SHORT", "SHORT")
        assert result["valid_format"] is False
        assert "error" in result

    def test_parse_td3_valid_format(self):
        # Synthetic 44-char lines (content not ICAO-valid but correct length)
        line1 = "P<INDTEST<<PERSON<<<<<<<<<<<<<<<<<<<<<<<<<<<".ljust(44, "<")[:44]
        # TD3 line 2 is exactly 44 characters; pad the synthetic fixture to length.
        line2 = "A12345670IND9204154M2504151<<<<<<<<<<<<<<<6".ljust(44, "<")[:44]
        result = self.parse(line1, line2)
        assert result["valid_format"] is True
        assert "surname" in result
        assert "passport_number" in result


# ─────────────────────────────────────────────────────────────────────────────
# Validation module tests (pure Python — no ML dependencies)
# ─────────────────────────────────────────────────────────────────────────────

class TestValidationModule:
    """Tests for ai/validation.py — pure Python."""

    def setup_method(self):
        from ai.validation import normalize, compare_values, validate_date_format
        self.normalize = normalize
        self.compare = compare_values
        self.validate_date = validate_date_format

    def test_normalize_none(self):
        assert self.normalize(None) == ""

    def test_normalize_strips_fillers(self):
        assert self.normalize("ABC<<<") == "ABC"

    def test_normalize_uppercase(self):
        assert self.normalize("abc") == "ABC"

    def test_compare_equal_values(self):
        assert self.compare("IND", "IND") is True

    def test_compare_with_fillers(self):
        assert self.compare("IND<<<", "IND") is True

    def test_compare_different_values(self):
        assert self.compare("IND", "USA") is False

    def test_validate_date_format_valid(self):
        assert self.validate_date("15-04-1990") is True

    def test_validate_date_format_slash(self):
        assert self.validate_date("15/04/1990") is True

    def test_validate_date_format_invalid(self):
        assert self.validate_date("not-a-date") is False

    def test_validate_date_format_none(self):
        assert self.validate_date(None) is False


# ─────────────────────────────────────────────────────────────────────────────
# Preprocessing module tests (requires OpenCV — skipped if not installed)
# ─────────────────────────────────────────────────────────────────────────────

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False


@pytest.mark.skipif(not CV2_AVAILABLE, reason="OpenCV not installed")
class TestPreprocessingModule:

    def test_load_nonexistent_image_raises(self):
        from ai.preprocessing import load_image
        with pytest.raises(FileNotFoundError):
            load_image("/nonexistent/path/document.jpg")

    def test_resize_image_no_change_when_small(self):
        from ai.preprocessing import resize_image
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        result = resize_image(img, width=1600)
        assert result.shape == img.shape

    def test_resize_image_reduces_width(self):
        from ai.preprocessing import resize_image
        img = np.zeros((800, 3200, 3), dtype=np.uint8)
        result = resize_image(img, width=1600)
        assert result.shape[1] == 1600

    def test_enhance_image_returns_2d_array(self):
        from ai.preprocessing import enhance_image
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        result = enhance_image(img)
        assert len(result.shape) == 2  # Grayscale

    def test_preprocess_pipeline(self, tmp_path):
        from ai.preprocessing import preprocess_image
        # Write a small test image
        img = np.full((50, 50, 3), 128, dtype=np.uint8)
        p = str(tmp_path / "test.png")
        cv2.imwrite(p, img)
        result = preprocess_image(p)
        assert result is not None
        assert len(result.shape) == 2


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline module tests (mocked AI, pure Python)
# ─────────────────────────────────────────────────────────────────────────────

class TestPipelineOrchestrator:
    """Tests for ai/pipeline.py using mocked sub-modules."""

    def test_pipeline_returns_expected_keys(self, tmp_path):
        """The pipeline should always return the four top-level sections."""
        from unittest.mock import patch, MagicMock
        import numpy as np

        # Write a real tiny PNG for the pipeline to load
        try:
            import cv2
            img = np.full((10, 10, 3), 200, dtype=np.uint8)
            p = str(tmp_path / "doc.png")
            cv2.imwrite(p, img)
        except ImportError:
            pytest.skip("OpenCV not installed")

        with patch("ai.pipeline._try_import") as mock_import:
            mock_preprocessing = MagicMock()
            mock_preprocessing.preprocess_image.return_value = \
                __import__("numpy").zeros((10, 10), dtype=__import__("numpy").uint8)
            mock_ocr = MagicMock()
            mock_ocr.run_ocr.return_value = {
                "passport_number": None, "dob": None, "expiry": None,
                "nationality": None, "raw_text": ""
            }
            mock_mrz = MagicMock()
            mock_mrz.run_mrz.return_value = {"error": "MRZ not detected"}
            mock_tampering = MagicMock()
            mock_tampering.run_tampering.side_effect = FileNotFoundError("no model")

            def side_effect(name):
                if name == "ai.preprocessing": return mock_preprocessing
                if name == "ai.ocr": return mock_ocr
                if name == "ai.mrz": return mock_mrz
                if name == "ai.tampering": return mock_tampering
                return None

            mock_import.side_effect = side_effect

            from ai.pipeline import run_pipeline
            result = run_pipeline(p)

        assert "preprocessing" in result
        assert "ocr" in result
        assert "mrz" in result
        assert "tampering" in result

    def test_tampering_not_available_when_model_missing(self, tmp_path):
        """If tampering model is missing, status should be 'not_available'."""
        from unittest.mock import patch, MagicMock
        import numpy as np

        try:
            import cv2
            img = np.full((10, 10, 3), 200, dtype=np.uint8)
            p = str(tmp_path / "doc.png")
            cv2.imwrite(p, img)
        except ImportError:
            pytest.skip("OpenCV not installed")

        with patch("ai.pipeline._try_import") as mock_import:
            mock_preprocessing = MagicMock()
            mock_preprocessing.preprocess_image.return_value = \
                np.zeros((10, 10), dtype=np.uint8)
            mock_tampering = MagicMock()
            mock_tampering.run_tampering.side_effect = FileNotFoundError("model missing")

            def side_effect(name):
                if name == "ai.preprocessing": return mock_preprocessing
                if name == "ai.ocr": return MagicMock(run_ocr=MagicMock(
                    return_value={"passport_number": None, "dob": None,
                                  "expiry": None, "nationality": None, "raw_text": ""}))
                if name == "ai.mrz": return MagicMock(
                    run_mrz=MagicMock(return_value={"error": "MRZ not detected"}))
                if name == "ai.tampering": return mock_tampering
                return None

            mock_import.side_effect = side_effect

            from ai.pipeline import run_pipeline
            result = run_pipeline(p)

        assert result["tampering"]["status"] == "not_available"
