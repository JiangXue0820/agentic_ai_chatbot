import re
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class SecurityGuard:
    """
    Security and privacy guard for the Agentic AI system.
    - Detects and blocks unsafe or malicious input/output
    - Masks/unmasks PII (mobile, email, IP)
    - Sanitizes model responses for sensitive data
    """

    def __init__(self):
        self.blocked_keywords = [
            "terrorism", "bomb", "kill", "suicide", "child abuse",
            "sex", "porn", "hate speech", "racism", "violence", "drugs",
        ]
        self.pii_patterns = {
            "EMAIL": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
            "MOBILE": r"\b(?:\+?\d{1,3}[-.\s]?)?\d{3,4}[-.\s]?\d{4}\b",
            "IPADDR": r"\b(?:\d{1,3}\.){3}\d{1,3}\b|\b(?:[A-Fa-f0-9]{0,4}:){2,7}[A-Fa-f0-9]{0,4}\b",
        }
        self.mask_map: Dict[str, str] = {}

    def inbound(self, text: str) -> Dict[str, Any]:
        """Validate and mask user input."""
        lowered = text.lower()
        if any(bad in lowered for bad in self.blocked_keywords):
            return {"safe": False, "text": "sorry, I cannot answer this question", "reason": "unsafe_input"}

        masked_text = text
        self.mask_map.clear()
        mask_index = 1

        for ptype, pattern in self.pii_patterns.items():
            matches = list(re.finditer(pattern, masked_text))
            offset = 0
            for match in matches:
                start, end = match.start() + offset, match.end() + offset
                original = masked_text[start:end]
                mask_token = f"[{ptype}_{mask_index}]"
                masked_text = masked_text[:start] + mask_token + masked_text[end:]
                offset += len(mask_token) - len(original)
                self.mask_map[original] = mask_token
                mask_index += 1

        return {"safe": True, "text": masked_text}

    def outbound(self, text: str) -> Dict[str, Any]:
        """Validate and sanitize model output."""
        lowered = text.lower()
        if any(bad in lowered for bad in self.blocked_keywords):
            return {"safe": False, "text": "sorry, I cannot answer this question", "reason": "unsafe_output"}

        # 1️⃣ Unmask inbound placeholders
        for original, mask in self.mask_map.items():
            text = text.replace(mask, original)

        # 2️⃣ Detect and sanitize new PII
        pii_found = []
        for ptype, pattern in self.pii_patterns.items():
            for m in re.findall(pattern, text):
                pii_found.append(m)

        if pii_found:
            text = self._sanitize_pii_output(text, pii_found)

        # 3️⃣ Clear map to prevent leakage across queries
        self.mask_map.clear()

        return {"safe": True, "text": text}

    def _sanitize_pii_output(self, text: str, pii_list: list[str]) -> str:
        """Sanitize PII in model-generated output."""
        for pii in pii_list:
            if re.match(self.pii_patterns["MOBILE"], pii):
                text = text.replace(pii, pii[:3] + "****" + pii[-2:])
            elif re.match(self.pii_patterns["EMAIL"], pii):
                name, domain = pii.split("@", 1)
                text = text.replace(pii, name[0] + "***@" + domain)
            elif re.match(self.pii_patterns["IPADDR"], pii):
                text = text.replace(pii, "[REDACTED_IP]")
            else:
                text = text.replace(pii, "[REDACTED]")
        return text
