import logging
import re

EMAIL_RE = re.compile(r"([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+)\.[A-Za-z]{2,}")
TOKEN_RE = re.compile(r"(Bearer\s+)?([A-Za-z0-9-_]{20,})")

class MaskPIIFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            msg = EMAIL_RE.sub(lambda m: f"{m.group(1)[:2]}***@***", record.msg)
            msg = TOKEN_RE.sub("***TOKEN***", msg)
            record.msg = msg
        return True

def configure_logging():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    logger = logging.getLogger()
    logger.addFilter(MaskPIIFilter())
