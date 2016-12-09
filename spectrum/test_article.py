from datetime import datetime
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
    if template_id == '00230':
        pytest.skip("SKIPPING 00230 due to incomplete support for videos")

    article = generate_article(template_id)
    _feed_and_verify(article)

@pytest.mark.continuum
def test_article_multiple_versions(generate_article, version_article):
    template_id = 15893
    article = generate_article(template_id)
    _feed_and_verify(article)
    new_article = version_article(article, new_version=2)
    _feed_and_verify(new_article)

# this is a silent correction of a 'correction' article, don't be confused
# we use this article because it's small and fast to process
# the silent correction is changing one word from lowercase to uppercase
@pytest.mark.continuum
def test_article_silent_correction(generate_article, silently_correct_article):
    template_id = 15893
    article = generate_article(template_id)
    _feed_and_verify(article)
    silent_correction_start = datetime.now()
    corrected_article = silently_correct_article(article, {'cytomegalovirus': 'CYTOMEGALOVIRUS'})
    _feed_silent_correction(corrected_article)
    input.SILENT_CORRECTION.article(os.path.basename(corrected_article.filename()))
    checks.API.wait_article(id=article.id(), title='Correction: Human CYTOMEGALOVIRUS IE1 alters the higher-order chromatin structure by targeting the acidic patch of the nucleosome')
    checks.GITHUB_XML.article(id=article.id(), version=article.version(), text_match='CYTOMEGALOVIRUS')
    checks.ARCHIVE.of(id=article.id(), version=article.version(), last_modified_after=silent_correction_start)


@pytest.mark.continuum
def test_article_already_present_version(generate_article, version_article):
    template_id = 15893
    article = generate_article(template_id)
    _feed_and_verify(article)
    new_article = version_article(article, new_version=1, version_number_prefix='v')
    _feed(new_article)
    # article stops in this state, it's stable
    checks.DASHBOARD.publication_in_progress(id=article.id(), version=article.version())
    error = checks.DASHBOARD.error(id=article.id(), version=1, run=2)
    assert re.match(r".*already published article version.*", error['event-message']), ("Error found on the dashboard does not match the expected description: %s" % error)

def _feed(article):
    input.PRODUCTION_BUCKET.upload(article.filename(), article.id())

def _feed_silent_correction(article):
    input.SILENT_CORRECTION_BUCKET.upload(article.filename(), article.id())

def _verify(article):
    (run, ) = checks.EIF.of(id=article.id(), version=article.version())
    for each in article.figure_names():
        checks.IMAGES_BOT_CDN.of(id=article.id(), figure_name=each, version=article.version())
        checks.IMAGES_PUBLISHED_CDN.of(id=article.id(), figure_name=each, version=article.version())
    checks.XML_PUBLISHED_CDN.of(id=article.id(), version=article.version())
    checks.XML_DOWNLOAD_PUBLISHED_CDN.of(id=article.id(), version=article.version())
    if article.has_pdf():
        checks.PDF_BOT_CDN.of(id=article.id(), version=article.version())
        checks.PDF_PUBLISHED_CDN.of(id=article.id(), version=article.version())
        checks.PDF_DOWNLOAD_PUBLISHED_CDN.of(id=article.id(), version=article.version())
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
    checks.JOURNAL.article(id=article.id(), volume=article_from_api['volume'], has_figures=article.has_figures())
    checks.GITHUB_XML.article(id=article.id(), version=article.version())

def _feed_and_verify(article):
    _feed(article)
    _verify(article)

