---
lang: python
keywords: logging, RotatingFileHandler, log file, formatter, level, rotate, log rotation, stream handler
---

# Logging with rotating file handlers

`print` is for debugging; `logging` is for production. Set levels, route to console and file
simultaneously, and let `RotatingFileHandler` cap each log file so the disk never fills.

```python
import logging
from logging.handlers import RotatingFileHandler

FMT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def setup_logger(name: str, log_file: str = "app.log") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()                        # avoid duplicate handlers on re-setup

    formatter = logging.Formatter(FMT)

    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    console.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10_000,                           # rotate after 10 KB
        backupCount=3,                             # keep app.log.1, .2, .3
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    logger.addHandler(console)
    logger.addHandler(file_handler)
    logger.propagate = False                       # don't double-log to root
    return logger


log = setup_logger("app", "app.log")
log.debug("low-level detail")
log.info("request %d handled", 42)                 # lazy formatting: use %-style
log.error("failure", exc_info=True)
```

Gotchas:
- `RotatingFileHandler` rotates when the *current file* exceeds `maxBytes`; with no maxBytes it
  grows unbounded, and `backupCount` limits only the number of rotated files.
- Keep `logger.propagate = False` when you attach handlers to a named logger, or messages also
  go to the root logger's handlers and you get every line twice.
- `basicConfig` is a no-op after the first call — call your setup exactly once, or guard with
  `logger.handlers` empty check / `logger.handlers.clear()`.
- Use `%`-style lazy formatting (`log.info("user=%s", user)`) — an f-string is evaluated even
  when the record is filtered out by level.
- Logging from multiple threads is safe; a single `RotatingFileHandler` serializes writes. For
  multiple processes, a single file handler still works but rotates lossily — consider
  `concurrent-log-handler` or per-process files.
- Don't log secrets (tokens, passwords) at DEBUG; rotate is not a substitute for redaction.
