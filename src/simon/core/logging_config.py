import logging
import json 
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler

from simon.core.config import SimonSettings

class JsonFormatter(logging.Formatter):

    """This is a logging formatter that outputs logs in structured JSON format."""

    def format(self,record: logging.LogRecord) -> str:

        event = {
            "timestamp" : datetime.now(timezone.utc).isoformat(),
            "level" : record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.exc_info:
            event["exception"] = self.formatException(record.exc_info)

        return json.dumps(event,ensure_ascii=False)

def configure_logging(settings: SimonSettings) -> None:

    log_file = settings.log_dir / "simon.log"

    handler = RotatingFileHandler(
        filename=str(log_file),
        maxBytes = 2_000_000,
        backupCount=5,
        encoding="utf-8"
    )

    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # Checking for redundant duplicate handler

    if not any(
        isinstance(existing, RotatingFileHandler) and getattr(existing, "baseFilename", None) == str(log_file.resolve()) for existing in root.handlers):
        root.addHandler(handler)
    

        

        

        



    