import logging
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
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(MultiLineFormatter("%(levelname)s: %(message)s"))
    logger.addHandler(stream_handler)
