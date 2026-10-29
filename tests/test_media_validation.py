import pytest
from app.services.media_validator import MediaValidatorService


def test_media_validation_non_existent():
    ok, report = MediaValidatorService.validate_rendered_output("non_existent_file.mp4", 10.0)
    assert ok is False
    assert "Tệp video không tồn tại." in report["errors"]

