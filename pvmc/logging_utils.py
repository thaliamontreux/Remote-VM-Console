import logging
import os
from collections import deque
from datetime import datetime


class LogBufferHandler(logging.Handler):
    def __init__(self, capacity=5000):
        super().__init__()
        self.buffer = deque(maxlen=capacity)
        self.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s', datefmt='%H:%M:%S'))

    def emit(self, record: logging.LogRecord):
        try:
            msg = self.format(record)
            self.buffer.append(msg)
        except Exception:
            pass

    def get_text(self) -> str:
        return '\n'.join(self.buffer)


_log_buffer_handler = LogBufferHandler()


def attach_to_root():
    root = logging.getLogger()
    if _log_buffer_handler not in root.handlers:
        root.addHandler(_log_buffer_handler)


def save_diagnostics(appdata_dir: str) -> str:
    diag_dir = os.path.join(appdata_dir, 'diagnostics')
    os.makedirs(diag_dir, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    path = os.path.join(diag_dir, f'diagnostics_{ts}.log')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(_log_buffer_handler.get_text())
        f.write('\n')
    return path


def set_debug_enabled(on: bool):
    root = logging.getLogger()
    if on:
        # Re-enable all logging and set DEBUG for visibility
        logging.disable(logging.NOTSET)
        level = logging.DEBUG
        root.setLevel(level)
        try:
            for h in list(root.handlers):
                h.setLevel(level)
        except Exception:
            pass
    else:
        # Disable all logging (no INFO/WARNING/ERROR/CRITICAL)
        logging.disable(logging.CRITICAL)
        level = logging.CRITICAL + 1
        root.setLevel(level)
        try:
            for h in list(root.handlers):
                h.setLevel(level)
        except Exception:
            pass


def get_debug_enabled() -> bool:
    # True if not globally disabled
    return logging.getLogger().manager.disable <= logging.NOTSET
