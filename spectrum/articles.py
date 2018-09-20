"lifecycle actions for articles, like ingesting/publishing/correcting"
from spectrum import input

def ingest(article):
    input.PRODUCTION_BUCKET.upload(article.filename(), id=article.id())
