import json
import logging
import re
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
import requests
from typing import List, Tuple, Optional

from app.providers.base import BaseTranslationProvider
from app.exceptions import TranslationError
from app.utils.retry import retry_call
from app.constants import SUPPORTED_TARGET_LANGUAGES

logger = logging.getLogger("AIDubbingStudio.TranslationAPI")


def get_target_lang_prompt_name(target_lang: str) -> str:
    """Return friendly language name for LLM system prompts."""
    code_clean = (target_lang or "vi").strip()
    for item in SUPPORTED_TARGET_LANGUAGES:
        if item["code"].lower() == code_clean.lower():
            return item["prompt_name"]
    return code_clean


class GoogleFreeTranslationProvider(BaseTranslationProvider):
    """Free, direct Google Translate provider via web RPC (no API key required)."""

    def __init__(self, timeout: int = 15, max_workers: int = 5):
        self.timeout = timeout
        self.max_workers = max_workers

    def test_connection(self) -> Tuple[bool, str]:
        """Verify network connectivity to Google Translate web endpoint."""
        try:
            sample = self._translate_single("Hello world, this is a test.", "auto", "vi")
            if sample:
                return True, f"Kết nối Google Translate thành công! Mẫu: '{sample}'"
            return False, "Không nhận được phản hồi từ dịch vụ Google Translate."
        except Exception as e:
            return False, f"Lỗi kết nối Google Translate: {e}"

    def _translate_single(self, text: str, source_lang: str = "auto", target_lang: str = "vi") -> str:
        text_clean = text.strip()
        if not text_clean:
            return text

        sl = "auto" if source_lang in ("auto", "") else source_lang
        tl = (target_lang or "vi").strip()
        if tl.lower() in ("zh", "zh-cn", "chinese"):
            tl = "zh-CN"

        url = (
            f"https://translate.googleapis.com/translate_a/single?client=gtx&sl={sl}&tl={tl}&dt=t&q="
            + urllib.parse.quote(text_clean)
        )
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
                )
            }
        )

        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            raw = resp.read().decode("utf-8")
            data = json.loads(raw)
            parts: List[str] = []
            if data and isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
                for part in data[0]:
                    if part and len(part) > 0 and part[0]:
                        parts.append(str(part[0]))
            return "".join(parts) if parts else text_clean

    def translate_batch(
        self,
        texts: List[str],
        source_lang: str = "auto",
        target_lang: str = "vi",
        context: Optional[str] = None
    ) -> List[str]:
        """Concurrently translate a batch of sentences."""
        if not texts:
            return []

        def _do_translate(t: str) -> str:
            return retry_call(
                lambda: self._translate_single(t, source_lang, target_lang),
                max_retries=3,
                initial_delay=0.8
            )

        with ThreadPoolExecutor(max_workers=min(len(texts), self.max_workers)) as executor:
            return list(executor.map(_do_translate, texts))


class OpenAITranslationProvider(BaseTranslationProvider):
    """Translation provider using standard OpenAI-compatible Chat Completions API."""

    def __init__(
        self,
        base_url: str = "https://api.openai.com/v1",
        api_key: str = "",
        model: str = "gpt-4o-mini",
        temperature: float = 0.3,
        timeout: int = 60
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.timeout = timeout

    def _get_headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def test_connection(self) -> Tuple[bool, str]:
        """Test API availability with a minimal translation probe."""
        if not self.api_key and "localhost" not in self.base_url and "127.0.0.1" not in self.base_url:
            return False, "Chưa cung cấp API Key cho dịch thuật."

        try:
            url = f"{self.base_url}/chat/completions"
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "You are a translator. Translate to Vietnamese."},
                    {"role": "user", "content": "Hello"}
                ],
                "max_tokens": 10
            }
            resp = requests.post(url, headers=self._get_headers(), json=payload, timeout=10)
            if resp.status_code == 200:
                return True, "Kết nối API dịch thuật thành công!"
            return False, f"API phản hồi mã lỗi {resp.status_code}: {resp.text[:200]}"
        except Exception as e:
            return False, f"Lỗi kết nối API: {e}"

    def translate_batch(
        self,
        texts: List[str],
        source_lang: str = "auto",
        target_lang: str = "vi",
        context: Optional[str] = None
    ) -> List[str]:
        """Translate a batch of sentences maintaining strict order and index mapping."""
        if not texts:
            return []

        def _do_request():
            lang_name = get_target_lang_prompt_name(target_lang)
            system_prompt = (
                f"Bạn là chuyên gia dịch thuật và lồng tiếng phim chuyên nghiệp sang {lang_name}.\n"
                "Quy tắc bắt buộc:\n"
                f"1. Dịch chuẩn xác, tự nhiên, văn phong bản xứ của {lang_name}, phù hợp phong cách thuyết minh/lồng tiếng truyền cảm.\n"
                "2. Giữ nguyên thuật ngữ quan trọng, tên riêng, con số và ngữ nghĩa gốc.\n"
                "3. Giữ đúng thứ tự và số lượng câu trong mảng.\n"
                "4. CHỈ TRẢ VỀ DUY NHẤT một mảng JSON hợp lệ dạng [\"câu 1\", \"câu 2\", ...]. Không thêm bất kỳ văn bản giải thích hay markdown nào khác."
            )

            user_content = json.dumps(texts, ensure_ascii=False)
            url = f"{self.base_url}/chat/completions"
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Dịch mảng câu sau sang {lang_name}:\n{user_content}"}
                ],
                "temperature": self.temperature
            }

            resp = requests.post(url, headers=self._get_headers(), json=payload, timeout=self.timeout)
            if resp.status_code != 200:
                raise TranslationError(
                    f"API dịch thuật trả về lỗi {resp.status_code}",
                    details=resp.text[:500]
                )

            data = resp.json()
            content = data["choices"][0]["message"]["content"].strip()

            # Clean markdown codeblocks if present
            if content.startswith("```"):
                content = re.sub(r"^```(?:json)?\s*", "", content)
                content = re.sub(r"\s*```$", "", content)

            try:
                translated_list = json.loads(content)
                if isinstance(translated_list, list) and len(translated_list) == len(texts):
                    return [str(item).strip() for item in translated_list]
            except Exception:
                pass

            # Fallback: split by lines
            lines = [l.strip() for l in content.split("\n") if l.strip()]
            cleaned_lines = []
            for l in lines:
                l_clean = re.sub(r"^\d+[\.\)]\s*", "", l).strip("\"'[] ")
                if l_clean:
                    cleaned_lines.append(l_clean)

            if len(cleaned_lines) == len(texts):
                return cleaned_lines

            # If count mismatches, fallback to line by line or return best effort
            if len(cleaned_lines) > 0:
                # Pad or slice to match
                while len(cleaned_lines) < len(texts):
                    cleaned_lines.append(texts[len(cleaned_lines)])
                return cleaned_lines[:len(texts)]

            raise TranslationError("Không thể phân tích phản hồi JSON từ API dịch thuật.", details=content[:300])

        return retry_call(_do_request, max_retries=3, initial_delay=1.5)


class LocalLLMTranslationProvider(OpenAITranslationProvider):
    """Offline translation provider using local OpenAI-compatible LLMs (Ollama / LM Studio / LocalAI)."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434/v1",
        model: str = "qwen2.5:latest",
        temperature: float = 0.2,
        timeout: int = 120
    ):
        super().__init__(
            base_url=base_url,
            api_key="ollama",  # Local servers typically do not enforce authentication
            model=model,
            temperature=temperature,
            timeout=timeout
        )

    def test_connection(self) -> Tuple[bool, str]:
        ok, msg = super().test_connection()
        if not ok:
            return (
                False,
                f"Không thể kết nối máy chủ LLM cục bộ ({self.base_url}).\n"
                f"Vui lòng đảm bảo Ollama hoặc LM Studio đã được bật trên máy của bạn.\nChi tiết: {msg}"
            )
        return True, f"Kết nối LLM cục bộ ({self.model}) thành công!"


