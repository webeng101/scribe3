import logging
import os
import sys

from ia_scribe.scribe_globals import ENTRY_POINTS, LOGGING_FORMAT

_running_known_entry_point = any(sys.argv[0].endswith(x) for x in ENTRY_POINTS)

# Disable Kivy default console nad file handlers
if _running_known_entry_point:
    os.environ['KIVY_NO_CONSOLELOG'] = '1'
    os.environ['KIVY_NO_FILELOG'] = '1'

from kivy.compat import PY2
from kivy.logger import (
    ConsoleHandler,
    FileHandler as KivyFileHandler,
    previous_stderr,
    Logger,
    LoggerHistory
)


class FileHandler(KivyFileHandler):

    def _write_message(self, record):
        if FileHandler.fd in (None, False):
            return
        msg = self.format(record)
        stream = FileHandler.fd
        fs = '%s\n'
        if PY2:
            try:
                if (isinstance(msg, str) and
                        getattr(stream, 'encoding', None)):
                    ufs = '%s\n'
                    try:
                        stream.write(ufs % msg)
                    except UnicodeEncodeError:
                        stream.write((ufs % msg).encode(stream.encoding))
                else:
                    stream.write(fs % msg)
            except UnicodeError:
                stream.write(fs % msg.encode('UTF-8'))
        else:
            stream.write(fs % msg)
        stream.flush()


class ConsoleFormatter(logging.Formatter):

    def format(self, record):
        try:
            msg = record.msg.split(':', 1)
            if len(msg) == 2:
                record.msg = msg[1].lstrip()
                if not record.name or record.name == 'kivy':
                    record.name = msg[0]
        except Exception:
            pass
        levelname = record.levelname
        if record.levelno == logging.TRACE:
            levelname = 'TRACE'
            record.levelname = levelname
        return super(ConsoleFormatter, self).format(record)


# Setup kivy.logger.Logger with our log handlers
if _running_known_entry_point:
    default_console_handler = ConsoleHandler(previous_stderr)
    default_console_handler.setFormatter(ConsoleFormatter(LOGGING_FORMAT))
    default_file_handler = FileHandler()
    default_file_handler.setFormatter(logging.Formatter(LOGGING_FORMAT))
    Logger.addHandler(default_console_handler)
    Logger.addHandler(default_file_handler)

    for record in LoggerHistory.history:
        Logger.callHandlers(record)
