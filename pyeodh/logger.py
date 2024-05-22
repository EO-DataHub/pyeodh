import logging
import os
import textwrap


class MultiLineFormatter(logging.Formatter):
    def format(self, record):
        message = record.msg
        record.msg = ""
        header = super().format(record)
        msg = textwrap.indent(message, " " * len(header)).lstrip()
        record.msg = message
        return header + msg


def setup(level: int = logging.WARNING):
    logger = logging.getLogger("pyeodh")
    logger.setLevel(level)
    env_level = os.getenv("PYEODH_DEBUG")
    if env_level is not None and env_level.lower() in ["yes", "true", "on", "1"]:
        logger.setLevel(logging.DEBUG)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(MultiLineFormatter("%(levelname)s: %(message)s"))
    logger.addHandler(stream_handler)


def set_log_level(level: int):
    """Set message level for logging.

    Args:
        level (int): Message level, recommended to use constants provided by logging
            module.
    """
    logging.getLogger("pyeodh").setLevel(level)
