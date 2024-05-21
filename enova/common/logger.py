import os
import re
import sys
import uuid
from logging import Formatter
from logging import StreamHandler
from logging import getLogger
from logging.handlers import TimedRotatingFileHandler
from enova.common.config import CONFIG
from enova.common.g_vars import get_traceid


LOGGER_MAP = {}


class AddRequestIdFormatter(Formatter):
    def formatMessage(self, record):
        trace_id = get_traceid()
        if CONFIG.app_name:
            record.message = f"[{CONFIG.app_name}][trace_id: {trace_id}]|{record.message}"
        else:
            record.message = f"[trace_id: {trace_id}]|{record.message}"
        return super().formatMessage(record)


def setup_logger(name=None, path=None, level=None, file_handler_backupCount=None):
    # sys.stdout = Unbuffered(sys.stdout)
    # sys.stderr = Unbuffered(sys.stderr)
    logger_conf = CONFIG.logger
    name = name or logger_conf["name"]
    path = path or logger_conf["path"]
    level = level or logger_conf["level"]
    file_handler_backupCount = file_handler_backupCount or logger_conf["file_handler_backupCount"]

    logger = getLogger(name)
    logger.setLevel(level.upper())

    formatter = AddRequestIdFormatter(datefmt=logger_conf["datefmt"], fmt=logger_conf["fmt"])
    stream_handler = StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    os.makedirs(path, exist_ok=True)
    file_handler = TimedRotatingFileHandler(
        filename=logger_conf["file_handler_filename_format"].format(path=path, name=name),
        when=logger_conf["file_handler_when"],
        interval=logger_conf["file_handler_interval"],
        backupCount=file_handler_backupCount,
    )
    file_handler.suffix = logger_conf["file_handler_suffix"]
    file_handler.extMatch = re.compile(logger_conf["file_handler_extMatch_pattern"])
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


def get_logger_by_name(name="default"):
    if name not in LOGGER_MAP:
        logger_conf = {}
        logger = setup_logger(**logger_conf)
        LOGGER_MAP[name] = logger
    return LOGGER_MAP[name]


LOGGER = get_logger_by_name()
