from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path


class BaseTranslationProvider(ABC):
    """Abstract Base Class for Translation Providers."""

    @abstractmethod
    def translate_batch(
        self,
        texts: List[str],
        source_lang: str,
        target_lang: str,
        context: Optional[str] = None
    ) -> List[str]:
        """Translate a batch of texts from source_lang to target_lang."""
        raise NotImplementedError

    @abstractmethod
    def test_connection(self) -> Tuple[bool, str]:
        """Test API connectivity or model availability."""
        raise NotImplementedError


class BaseTTSProvider(ABC):
    """Abstract Base Class for Text-to-Speech Providers."""

    @abstractmethod
    def get_voices(self) -> List[Dict[str, Any]]:
        """Return list of available voices. Each item: {id, name, gender, lang}"""
        raise NotImplementedError

    @abstractmethod
    def synthesize(
        self,
        text: str,
        voice_id: str,
        output_path: str | Path,
        options: Optional[Dict[str, Any]] = None
    ) -> float:
        """Synthesize text to audio file. Returns actual audio duration in seconds."""
        raise NotImplementedError

    @abstractmethod
    def get_capabilities(self) -> Dict[str, Any]:
        """Return capabilities: supports_pitch, supports_rate, supports_volume, is_offline."""
        raise NotImplementedError
