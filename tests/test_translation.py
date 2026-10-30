import pytest
from unittest.mock import MagicMock
from app.models import DialogueSegment
from app.services.translation import TranslationService
from app.providers.base import BaseTranslationProvider


class MockTranslationProvider(BaseTranslationProvider):
    def test_connection(self):
        return True, "OK"

    def translate_batch(self, texts, source_lang, target_lang, context=None):
        # Mock translations
        return [f"Dịch: {t}" for t in texts]


def test_translation_batch_mapping():
    dlgs = [
        DialogueSegment(id="seg_1", start=0.0, end=2.0, source_text="Good morning"),
        DialogueSegment(id="seg_2", start=2.5, end=4.5, source_text="How are you?"),
        DialogueSegment(id="seg_3", start=5.0, end=7.0, source_text="Thank you very much"),
    ]

    mock_provider = MockTranslationProvider()
    service = TranslationService(provider=mock_provider, batch_size=2)

    translated = service.translate_dialogues(dlgs, source_lang="en", target_lang="vi")

    assert len(translated) == 3
    assert translated[0].id == "seg_1"
    assert translated[0].target_text == "Dịch: Good morning"
    assert translated[1].id == "seg_2"
    assert translated[1].target_text == "Dịch: How are you?"
    assert translated[2].id == "seg_3"
    assert translated[2].target_text == "Dịch: Thank you very much"


def test_google_free_translation_provider():
    from app.providers.translation_api import GoogleFreeTranslationProvider
    prov = GoogleFreeTranslationProvider()
    # Test single translation
    res = prov._translate_single("Hello", "en", "vi")
    assert isinstance(res, str)
    assert len(res) > 0


def test_local_llm_provider_initialization():
    from app.providers.translation_api import LocalLLMTranslationProvider
    prov = LocalLLMTranslationProvider(base_url="http://localhost:11434/v1", model="qwen2.5:latest")
    assert prov.base_url == "http://localhost:11434/v1"
    assert prov.model == "qwen2.5:latest"
    assert prov.api_key == "ollama"


def test_multilingual_target_languages():
    from app.constants import SUPPORTED_TARGET_LANGUAGES, EDGE_TTS_VOICES_BY_LANG
    from app.providers.edge_tts_provider import EdgeTTSProvider
    from app.providers.translation_api import get_target_lang_prompt_name

    assert len(SUPPORTED_TARGET_LANGUAGES) >= 10
    provider = EdgeTTSProvider()

    for lang_item in SUPPORTED_TARGET_LANGUAGES:
        code = lang_item["code"]
        prompt_name = get_target_lang_prompt_name(code)
        assert len(prompt_name) > 0

        # Check that EdgeTTS provides voices for this target language
        voices = provider.get_voices(target_lang=code)
        assert len(voices) > 0
        assert all("id" in v and "name" in v for v in voices)



