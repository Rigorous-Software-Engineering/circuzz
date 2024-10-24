from dataclasses import dataclass
import logging

@dataclass(frozen=True)
class Color():
    RED          = "\033[0;31m"
    GREEN        = "\033[0;32m"
    YELLOW       = "\033[0;33m"
    BLUE         = "\033[0;34m"
    PURPLE       = "\033[0;35m"
    CYAN         = "\033[0;36m"
    BOLD         = "\033[1m"
    END          = "\033[0m"

class ColoredThreadAwareFormatter(logging.Formatter):

    FORMATS = {
        logging.DEBUG:    f"%(asctime)s %(processName)s %(threadName)s [{Color.GREEN}%(levelname)s{Color.END}]: %(message)s",
        logging.INFO:     f"%(asctime)s %(processName)s %(threadName)s [{Color.BLUE}%(levelname)s{Color.END}]: %(message)s",
        logging.WARNING:  f"%(asctime)s %(processName)s %(threadName)s [{Color.YELLOW}%(levelname)s{Color.END}]: %(message)s",
        logging.ERROR:    f"%(asctime)s %(processName)s %(threadName)s [{Color.RED}%(levelname)s{Color.END}]: %(message)s",
        logging.CRITICAL: f"%(asctime)s %(processName)s %(threadName)s [{Color.RED}{Color.BOLD}%(levelname)s{Color.END}]: %(message)s",
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

def get_color_logger() -> logging.Logger:
    logger = logging.getLogger()

    if len(logger.handlers) == 0:
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        ch.setFormatter(ColoredThreadAwareFormatter())
        logger.addHandler(ch)

    return logger