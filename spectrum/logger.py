import logging
import os

class OptionalExtraFilter(logging.Filter):
    def filter(self, record):
        if not hasattr(record, 'id'):
            record.id = ''
        if not hasattr(record, 'app'):
            record.app = ''
        record.extra_merged = ','.join([e for e in [record.id, record.app] if e])
        return True

FORMAT = "[%(asctime)-15s][%(levelname)s][%(name)s][%(extra_merged)s] %(message)s"
FORMATTER = logging.Formatter(FORMAT)

def configure_handler(handler):
    handler.addFilter(logging.Filter('spectrum'))
    handler.addFilter(OptionalExtraFilter())
    handler.setFormatter(FORMATTER)
    logging.getLogger().addHandler(handler)

logging.getLogger().setLevel(logging.INFO)

configure_handler(logging.StreamHandler())
configure_handler(logging.FileHandler('build/test.log'))

def logger(name):
    "Returns a configured Logger"
    return logging.getLogger(name)

def set_logging_level(level):
    "e.g. logging.INFO"
    logging.getLogger().setLevel(level)

# pytest does not allow to read a cli argument globally, but
# only from a test or a fixture afaik
# so, workaround "trying hard to be an extensible tool and failing at it"
LOG_LEVEL = os.environ.get('SPECTRUM_LOG_LEVEL', 'INFO')
set_logging_level(getattr(logging, LOG_LEVEL))
