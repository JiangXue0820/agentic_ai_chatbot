# =====================================================
# app/guardrails/security_guard.py
# Security Guardrail Module for Input/Output Filtering
# =====================================================

import re
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class SecurityGuard:
    """
    Security and privacy guard for the Agentic AI system.
    - Detects and blocks unsafe or malicious input/output
    - Masks and unmasks PII entities (mobile, email, IP)
    - Sanitizes model responses for sensitive data
    """

    def __init__(self):
        # --- Restricted or unsafe keywords ---
        self.blocked_keywords = [
            "terrorism", "bomb", "kill", "suicide", "child abuse",
            "sex", "porn", "hate speech", "racism", "violence", "drugs",
        ]

        # --- Basic PII recognition patterns ---
        self.pii_patterns = {
            "EMAIL": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
            "MOBILE": r"\b(?:\+?\d{1,3}[-.\s]?)?\d{3,4}[-.\s]?\d{4}\b",
            "IPADDR": r"\b(?:\d{1,3}\.){3}\d{1,3}\b|\b(?:[A-Fa-f0-9]{0,4}:){2,7}[A-Fa-f0-9]{0,4}\b",
        }

        self.mask_map: Dict[str, str] = {}

    # =====================================================
    # 🧩 Inbound: Validate and mask user input
    # =====================================================
    def inbound(self, text: str) -> Dict[str, Any]:
        """
        Validate and mask user input (supports multiple entities).
        Returns:
            {"safe": bool, "text": processed_text, "reason": optional_reason}
        """

        lowered = text.lower()

        # 1️⃣ Block unsafe queries
        if any(bad in lowered for bad in self.blocked_keywords):
            logger.warning(f"Blocked unsafe user query: {text[:50]}")
            return {
                "safe": False,
                "text": "sorry, I cannot answer this question",
                "reason": "unsafe_input"
            }

        # 2️⃣ Mask detected PII entities (assign sequential IDs)
        masked_text = text
        self.mask_map.clear()
        mask_index = 1

        # Use re.finditer() to replace entities one-by-one, preserving order
        for ptype, pattern in self.pii_patterns.items():
            matches = list(re.finditer(pattern, masked_text))
            offset = 0  # track index shift due to insertions

            for match in matches:
                start, end = match.start() + offset, match.end() + offset
                original = masked_text[start:end]
                mask_token = f"[{ptype}_{mask_index}]"

                # Replace this exact span only
                masked_text = masked_text[:start] + mask_token + masked_text[end:]
                offset += len(mask_token) - len(original)

                self.mask_map[mask_token] = original
                mask_index += 1

        if self.mask_map:
            logger.info(f"Masked PII entities: {self.mask_map}")

        return {"safe": True, "text": masked_text}

    # =====================================================
    # 🧩 Outbound: Validate and unmask model output
    # =====================================================
    def outbound(self, text: str) -> Dict[str, Any]:
        """
        Validate model output, sanitize sensitive data, and restore masked entities.
        """

        lowered = text.lower()

        # 1️⃣ Block unsafe model output
        if any(bad in lowered for bad in self.blocked_keywords):
            logger.warning("Blocked unsafe model output.")
            return {
                "safe": False,
                "text": "sorry, I cannot answer this question",
                "reason": "unsafe_output"
            }

        # 2️⃣ Detect and sanitize new PII
        pii_found = []
        for ptype, pattern in self.pii_patterns.items():
            for m in re.findall(pattern, text):
                pii_found.append(m)

        if pii_found:
            logger.info(f"Detected new PII in model output: {pii_found}")
            text = self._sanitize_pii_output(text, pii_found)

        # 3️⃣ Restore masked entities from inbound
        for mask, original in self.mask_map.items():
            text = text.replace(mask, original)

        return {"safe": True, "text": text}

    # =====================================================
    # 🔒 Internal helper: sanitize model-generated PII
    # =====================================================
    def _sanitize_pii_output(self, text: str, pii_list: list[str]) -> str:
        """
        Sanitize PII in model-generated output.
        """
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