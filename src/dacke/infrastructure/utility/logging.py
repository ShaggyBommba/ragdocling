import logging
import sys
from datetime import date
from pathlib import Path

from pythonjsonlogger import jsonlogger

from dacke.infrastructure.config import LoggingSettings


class LoggingSetup:
    @staticmethod
    def setup(settings: LoggingSettings) -> None:
        level = logging.getLevelName(settings.log_level.upper())

        if settings.log_json:
            formatter: logging.Formatter = jsonlogger.JsonFormatter(settings.log_format)
        else:
            formatter = logging.Formatter(settings.log_format)

        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        handlers: list[logging.Handler] = [stream_handler]

        if settings.log_dir is not None:
            log_path = Path(settings.log_dir)
            log_path.mkdir(parents=True, exist_ok=True)
            filename = log_path / f"{date.today().isoformat()}.log"
            file_handler = logging.FileHandler(filename, encoding="utf-8")
            file_handler.setFormatter(formatter)
            handlers.append(file_handler)

        root = logging.getLogger()
        root.setLevel(level)
        root.handlers.clear()
        for handler in handlers:
            root.addHandler(handler)
