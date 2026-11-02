import os
import tempfile
from pathlib import Path
import pytest
from PySide6.QtWidgets import QApplication, QLineEdit

from app.config import AppConfig, apply_hf_token, app_config
from app.ui.dialogs import SettingsDialog


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_apply_hf_token():
    test_token = "hf_test_token_1234567890abcdef"
    apply_hf_token(test_token)
    assert os.environ.get("HF_TOKEN") == test_token
    assert os.environ.get("HUGGING_FACE_HUB_TOKEN") == test_token


def test_app_config_hf_token():
    with tempfile.TemporaryDirectory() as tmp_dir:
        cfg_file = Path(tmp_dir) / "test_config.json"
        cfg = AppConfig(config_path=cfg_file)
        assert "hf_token" in cfg.data
        assert cfg.get("hf_token") == ""

        cfg.set("hf_token", "hf_mock_saved_token")
        assert cfg.get("hf_token") == "hf_mock_saved_token"

        # Reload from disk
        cfg2 = AppConfig(config_path=cfg_file)
        assert cfg2.get("hf_token") == "hf_mock_saved_token"


def test_settings_dialog_hf_token(qapp, monkeypatch):
    dlg = SettingsDialog()
    assert hasattr(dlg, "input_hf_token")
    assert hasattr(dlg, "btn_toggle_hf")
    assert hasattr(dlg, "btn_test_hf")

    # Test toggle visibility
    assert dlg.input_hf_token.echoMode() == QLineEdit.Password
    dlg._toggle_hf_visibility()
    assert dlg.input_hf_token.echoMode() == QLineEdit.Normal
    dlg._toggle_hf_visibility()
    assert dlg.input_hf_token.echoMode() == QLineEdit.Password

    # Test saving settings
    dlg.input_hf_token.setText("hf_unit_test_token_abc")
    monkeypatch.setattr(dlg, "accept", lambda: None)
    monkeypatch.setattr("app.ui.dialogs.set_custom_ffmpeg_paths", lambda *args: None)
    dlg._save_settings()

    assert app_config.get("hf_token") == "hf_unit_test_token_abc"
    assert os.environ.get("HF_TOKEN") == "hf_unit_test_token_abc"
