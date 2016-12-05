import logging

class OptionalArticleIdFilter(logging.Filter):
    def filter(self, record):
        if not hasattr(record, 'id'):
            record.id = ''
        return True

FORMAT = "[%(asctime)-15s][%(levelname)s][%(name)s][%(id)s] %(message)s"
FORMATTER = logging.Formatter(FORMAT)

def configure_handler(handler):
    handler.addFilter(logging.Filter('spectrum'))
    handler.addFilter(OptionalArticleIdFilter())
    handler.setFormatter(FORMATTER)
    logging.getLogger().addHandler(handler)

logging.getLogger().setLevel(logging.INFO)

configure_handler(logging.StreamHandler())
configure_handler(logging.FileHandler('build/test.log'))

def logger(name):
    return logging.getLogger(name)
