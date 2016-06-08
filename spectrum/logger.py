import logging

class OptionalArticleIdFilter(logging.Filter):
    def filter(self, record):
        if not hasattr(record, 'id'):
            record.id = ''
        return True

FORMAT = "[%(asctime)-15s][%(levelname)s][%(name)s][%(id)s] %(message)s"
FORMATTER = logging.Formatter(FORMAT)
HANDLER = logging.StreamHandler()
HANDLER.setFormatter(FORMATTER)
HANDLER.addFilter(logging.Filter('spectrum'))
HANDLER.addFilter(OptionalArticleIdFilter())
logging.getLogger().addHandler(HANDLER)
logging.getLogger().setLevel(logging.INFO)
