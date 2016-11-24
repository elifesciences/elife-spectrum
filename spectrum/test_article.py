import os
import re
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

@pytest.mark.continuum
def test_article_multiple_versions(generate_article, version_article):
    template_id = 15893
    article = generate_article(template_id, version=1)
    _feed_and_verify(article)
    new_article = version_article(article, new_version=2)
    _feed_and_verify(new_article)

@pytest.mark.continuum
def test_article_silent_correction(generate_article):
    template_id = 15893
    article = generate_article(template_id, version=1)
    _feed_and_verify(article)
    input.SILENT_CORRECTION.article(os.path.basename(article.filename()))

@pytest.mark.continuum
def test_article_already_present_version(generate_article, version_article):
    template_id = 15893
    article = generate_article(template_id, version=1)
    _feed_and_verify(article)
    new_article = version_article(article, new_version=1, version_number_prefix='v')
    _feed(new_article)
    # article stops in this state, it's stable
    checks.DASHBOARD.publication_in_progress(id=article.id(), version=article.version())
    error = checks.DASHBOARD.error(id=article.id(), version=1, run=2)
    assert re.match(r".*already published article version.*", error['event-message']), ("Error found on the dashboard does not match the expected description: %s" % error)

def _feed(article):
    input.PRODUCTION_BUCKET.upload(article.filename(), article.id())

def _feed_and_verify(article):
    _feed(article)
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
    checks.WEBSITE.visible('/content/%s/e%sv%s' % \
        (version_info['volume'], version_info['manuscript_id'], \
         version_info['version']), id=article.id())

    checks.ARCHIVE.of(id=article.id(), version=article.version())
    article_from_api = checks.API.article(id=article.id(), version=article.version())
    checks.JOURNAL.article(id=article.id(), volume=article_from_api['volume'])
    checks.GITHUB_XML.article(id=article.id(), version=article.version())
