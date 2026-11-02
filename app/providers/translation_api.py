import json
import logging
import re
import asyncio
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


class GeminiWebAPITranslationProvider(BaseTranslationProvider):
    """Translation provider using Gemini Web API with browser cookies, system prompt priming, and translation styles."""

    def __init__(
        self,
        secure_1psid: Optional[str] = None,
        secure_1psidts: Optional[str] = None,
        proxy: Optional[str] = None,
        style: str = "storytelling",
        timeout: int = 45
    ):
        self.secure_1psid = secure_1psid
        self.secure_1psidts = secure_1psidts
        self.proxy = proxy
        self.style = style
        self.timeout = timeout
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._client = None
        self._chat = None
        self._session_metadata = None
        self._current_target_lang = None
        self._current_style = None

    def _get_loop(self) -> asyncio.AbstractEventLoop:
        if self._loop is None or self._loop.is_closed():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
        return self._loop

    def _run_async(self, coro):
        loop = self._get_loop()
        return loop.run_until_complete(coro)

    async def _close_session(self):
        """Close active Gemini client session and reset states."""
        if self._client:
            try:
                await self._client.close()
            except Exception:
                pass
            self._client = None
        self._chat = None
        self._session_metadata = None
        self._current_target_lang = None
        self._current_style = None

    def close(self):
        """Clean up client and event loop."""
        if self._loop and not self._loop.is_closed():
            try:
                self._run_async(self._close_session())
            except Exception:
                pass
            try:
                pending = [t for t in asyncio.all_tasks(self._loop) if not t.done()]
                for t in pending:
                    t.cancel()
                if pending:
                    self._loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                self._loop.close()
            except Exception:
                pass
            self._loop = None

    def test_connection(self) -> Tuple[bool, str]:
        """Test authentication and connectivity with Gemini Web API."""
        try:
            from gemini_webapi import GeminiClient

            async def _do_test():
                c = GeminiClient(
                    secure_1psid=self.secure_1psid or None,
                    secure_1psidts=self.secure_1psidts or None,
                    proxy=self.proxy or None
                )
                try:
                    await c.init(
                        timeout=min(self.timeout, 30),
                        auto_close=False,
                        close_delay=300,
                        auto_refresh=False
                    )
                    chat = c.start_chat()
                    res = await chat.send_message("Xin chào, hãy phản hồi ngắn gọn 1 câu.")
                    return res.text if res else ""
                finally:
                    try:
                        await c.close()
                    except Exception:
                        pass

            reply = self._run_async(_do_test())
            if reply:
                snippet = reply.strip()[:100].replace("\n", " ")
                return True, f"Kết nối Gemini Web API thành công!\nGemini phản hồi: '{snippet}'"
            return False, "Không nhận được phản hồi từ Gemini Web API."
        except Exception as e:
            return False, f"Lỗi kết nối Gemini Web API: {e}"

    async def _ensure_chat_session(self, target_lang: str, style_id: str):
        """Initialize Gemini client and prime chat session with system prompt if needed."""
        from gemini_webapi import GeminiClient
        from app.constants import TRANSLATION_STYLES

        if (
            self._chat is not None
            and self._current_target_lang == target_lang
            and self._current_style == style_id
        ):
            return self._chat

        if self._client is None:
            self._client = GeminiClient(
                secure_1psid=self.secure_1psid or None,
                secure_1psidts=self.secure_1psidts or None,
                proxy=self.proxy or None
            )
            await self._client.init(
                timeout=self.timeout,
                auto_close=False,
                close_delay=300,
                auto_refresh=False
            )

        # Start a new chat session or load from metadata
        chat = self._client.start_chat()

        # Prime AI with system prompt for translation
        target_lang_name = get_target_lang_prompt_name(target_lang)
        style_item = next((s for s in TRANSLATION_STYLES if s["id"] == style_id), None)
        style_name = style_item["name"] if style_item else style_id
        style_desc = style_item["prompt"] if style_item else "Tự nhiên, phù hợp lồng tiếng."

        system_prompt = (
            f"Bạn là chuyên gia biên dịch kịch bản lồng tiếng video chuyên nghiệp sang {target_lang_name}.\n"
            f"Phong cách dịch bắt buộc: {style_name} ({style_desc}).\n\n"
            "QUY TẮC BẮT BUỘC:\n"
            "1. Dịch truyền cảm, tự nhiên theo đúng phong cách yêu cầu, giữ nguyên ngữ cảnh và cảm xúc của lời thoại.\n"
            "2. Giữ độ dài câu dịch vừa vặn với nhịp điệu phát âm để thuận tiện cho việc lồng tiếng TTS.\n"
            "3. Định dạng đầu ra nghiêm ngặt: Mỗi câu được đánh số [1], [2], [3]... Bạn CHỈ trả về đúng danh sách các câu đã dịch:\n"
            "[1] Bản dịch câu 1\n"
            "[2] Bản dịch câu 2\n"
            "4. TUYỆT ĐỐI KHÔNG kèm theo lời chào, giải thích, chú thích hay bất kỳ từ ngữ nào khác ngoài danh sách [số]."
        )

        try:
            await chat.send_message(system_prompt)
            self._session_metadata = chat.metadata
        except Exception as e:
            logger.warning(f"Error sending system prompt to Gemini chat: {e}")

        self._chat = chat
        self._current_target_lang = target_lang
        self._current_style = style_id
        return self._chat

    def _translate_single(self, text: str, source_lang: str = "auto", target_lang: str = "vi", style_id: Optional[str] = None) -> str:
        text_clean = text.strip()
        if not text_clean:
            return text

        style_id = style_id or self.style or "storytelling"
        target_lang_name = get_target_lang_prompt_name(target_lang)

        async def _do():
            chat = await self._ensure_chat_session(target_lang, style_id)
            prompt = f"Dịch câu thoại sau sang {target_lang_name}:\n[1] {text_clean}"
            res = await chat.send_message(prompt)
            self._session_metadata = chat.metadata
            ans = res.text.strip()
            m = re.search(r"^\[1\]\s*(.*)", ans, re.MULTILINE)
            if m:
                return m.group(1).strip()
            return ans.strip("[]\"' \n")

        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                return self._run_async(_do())
            except Exception as e:
                logger.warning(f"Gemini single translation error on attempt {attempt}/{max_retries}: {e}")
                self._run_async(self._close_session())
                if attempt == max_retries:
                    raise TranslationError(f"Lỗi dịch câu với Gemini Web API: {e}")
                import time
                time.sleep(1.5 * attempt)

    def translate_batch(
        self,
        texts: List[str],
        source_lang: str = "auto",
        target_lang: str = "vi",
        context: Optional[str] = None
    ) -> List[str]:
        if not texts:
            return []

        style_id = self.style or "storytelling"
        target_lang_name = get_target_lang_prompt_name(target_lang)

        async def _do_batch():
            chat = await self._ensure_chat_session(target_lang, style_id)
            prompt_lines = [f"[{i + 1}] {t.strip()}" for i, t in enumerate(texts)]
            user_prompt = (
                f"Hãy dịch các câu thoại sau sang {target_lang_name}:\n"
                + "\n".join(prompt_lines)
            )
            res = await chat.send_message(user_prompt)
            self._session_metadata = chat.metadata
            content = res.text.strip()

            # Parse numbered answers [1], [2]...
            results_map = {}
            for line in content.split("\n"):
                m = re.match(r"^\[(\d+)\]\s*(.*)", line.strip())
                if m:
                    idx = int(m.group(1)) - 1
                    results_map[idx] = m.group(2).strip()

            if len(results_map) == len(texts):
                return [results_map[i] for i in range(len(texts))]

            # Fallback parsing line by line
            lines = [l.strip() for l in content.split("\n") if l.strip()]
            cleaned_lines = []
            for l in lines:
                l_clean = re.sub(r"^\d+[\.\)\]]\s*", "", l).strip("\"'[] ")
                if l_clean:
                    cleaned_lines.append(l_clean)

            if len(cleaned_lines) == len(texts):
                return cleaned_lines

            # Best effort mapping
            final_res = []
            for i in range(len(texts)):
                if i in results_map:
                    final_res.append(results_map[i])
                elif i < len(cleaned_lines):
                    final_res.append(cleaned_lines[i])
                else:
                    final_res.append(texts[i])
            return final_res

        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                return self._run_async(_do_batch())
            except Exception as e:
                err_str = str(e)
                logger.warning(f"Gemini batch translation error on attempt {attempt}/{max_retries}: {err_str}")
                # Reset connection and session on network / SSL drop
                self._run_async(self._close_session())
                if attempt == max_retries:
                    raise TranslationError(f"Dịch thuật thất bại với Gemini Web API sau {max_retries} lần thử: {err_str}")
                import time
                time.sleep(2.0 * attempt)


