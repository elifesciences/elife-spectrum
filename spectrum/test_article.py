import pytest
from spectrum import generator
from spectrum import input
from spectrum import checks

@pytest.mark.continuum
@pytest.mark.parametrize("template_id", generator.all_stored_articles())
def test_article_first_version(template_id, article_id_filter, generate_article):
    if article_id_filter:
        if template_id != article_id_filter:
            pytest.skip("Filtered out through the article_id_filter")

    article = generate_article(template_id)
    _feed_and_verify(article)

# TODO:  will need to pass a filter in execute-simplest-possible-test.sh
@pytest.mark.continuum
def _test_article_multiple_versions():
    article = generate_article(template_id, version=1)
    _feed_and_verify(article)
    new_version = article.new_version(version=2)
    _feed_and_verify(new_version)

def _feed_and_verify(article):
    input.PRODUCTION_BUCKET.upload(article.filename(), article.id())
    (run, ) = checks.EIF.of(id=article.id(), version=article.version())
    for each in article.figure_names():
        checks.IMAGES.of(id=article.id(), figure_name=each, version=article.version())
    if article.has_pdf():
        checks.PDF.of(id=article.id(), version=article.version())
    checks.WEBSITE.unpublished(id=article.id(), version=article.version())
    checks.DASHBOARD.ready_to_publish(id=article.id(), version=article.version())

    input.DASHBOARD.publish(id=article.id(), version=article.version(), run=run)
    checks.DASHBOARD.published(id=article.id(), version=article.version())
    version_info = checks.LAX.published(id=article.id(), version=article.version())
    checks.WEBSITE.published(id=article.id(), version=article.version())
    checks.WEBSITE.visible('/content/%s/e%sv%s' % (version_info['volume'], version_info['manuscript_id'], version_info['version']), id=article.id())

    checks.ARCHIVE.of(id=article.id(), version=article.version())
