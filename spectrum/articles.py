"lifecycle actions for articles, like ingesting/publishing/correcting"
from spectrum import checks
from spectrum import input

def ingest(article):
    input.PRODUCTION_BUCKET.upload(article.filename(), id=article.id())

def wait_for_publishable(article, run_after):
    article_on_dashboard = checks.DASHBOARD.ready_to_publish(id=article.id(), version=article.version(), run_after=run_after)
    current_version = article_on_dashboard['versions'][str(article.version())]
    runs = current_version['runs']
    last_run_number = max([int(i) for i in runs.keys()])
    run = runs[str(last_run_number)]['run-id']
    for each in article.figure_names():
        checks.IMAGES_PUBLISHED_CDN_BUCKET.of(id=article.id(), figure_name=each, version=article.version())
    checks.XML_PUBLISHED_CDN_BUCKET.of(id=article.id(), version=article.version())
    if article.has_pdf():
        checks.PDF_PUBLISHED_CDN_BUCKET.of(id=article.id(), version=article.version())
    checks.API_SUPER_USER.article(id=article.id(), version=article.version())
    return run

def publish(article, run):
    input.DASHBOARD.publish(id=article.id(), version=article.version(), run=run)

def feed_silent_correction(article):
    input.SILENT_CORRECTION_BUCKET.upload(article.filename(), id=article.id())
