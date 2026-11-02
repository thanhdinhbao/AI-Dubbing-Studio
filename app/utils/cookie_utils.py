import re
import json
from typing import Tuple


def extract_gemini_cookies(raw_input: str) -> Tuple[str, str]:
    """
    Extract __Secure-1PSID and __Secure-1PSIDTS from cookie string, header, or JSON.
    Returns: (secure_1psid, secure_1psidts)
    """
    if not raw_input or not raw_input.strip():
        return "", ""

    raw = raw_input.strip()
    psid = ""
    psidts = ""

    # 1. Try parsing JSON (e.g. exported from Cookie-Editor / EditThisCookie)
    if raw.startswith("[") or raw.startswith("{"):
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        n = str(item.get("name", ""))
                        v = str(item.get("value", ""))
                        if n == "__Secure-1PSID":
                            psid = v
                        elif n == "__Secure-1PSIDTS":
                            psidts = v
            elif isinstance(data, dict):
                psid = str(data.get("__Secure-1PSID") or data.get("secure_1psid") or data.get("1PSID") or "")
                psidts = str(data.get("__Secure-1PSIDTS") or data.get("secure_1psidts") or data.get("1PSIDTS") or "")
        except Exception:
            pass

    # 2. Try regex for standard Cookie Header: __Secure-1PSID=...; __Secure-1PSIDTS=...
    if not psid:
        m1 = re.search(r"(?:^|[;\s])__Secure-1PSID=([^;\s\r\n]+)", raw)
        if m1:
            psid = m1.group(1).strip().strip("\"';")
    if not psidts:
        m2 = re.search(r"(?:^|[;\s])__Secure-1PSIDTS=([^;\s\r\n]+)", raw)
        if m2:
            psidts = m2.group(1).strip().strip("\"';")

    # 3. Try Netscape / tab-separated or space-separated format
    if not psid:
        m3 = re.search(r"__Secure-1PSID\s+([^\s\r\n]+)", raw)
        if m3:
            psid = m3.group(1).strip().strip("\"';")
    if not psidts:
        m4 = re.search(r"__Secure-1PSIDTS\s+([^\s\r\n]+)", raw)
        if m4:
            psidts = m4.group(1).strip().strip("\"';")

    return psid, psidts
