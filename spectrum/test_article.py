"Test that involve publishing articles and checking their visibility and correctness throughout different systems"
from datetime import datetime
import os
import random
import re
import string
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
    _ingest_and_publish(article)

@pytest.mark.continuum
def test_article_multiple_ingests_of_the_same_version(generate_article, modify_article):
    template_id = 15893
    article = generate_article(template_id)
    _ingest(article)
    run1 = _wait_for_publishable(article)

    run2_start = datetime.now()
    modified_article = modify_article(article, replacements={'cytomegalovirus': 'CYTOMEGALOVIRUS'})
    _ingest(modified_article)
    (run2, ) = checks.EIF.of(id=article.id(), version=article.version(), last_modified_after=run2_start)
    checks.DASHBOARD.ready_to_publish(id=article.id(), version=article.version(), run=run2)
    assert run2 != run1, "A new run should have been triggered"
    input.DASHBOARD.publish(id=article.id(), version=article.version(), run=run2)
    checks.API.wait_article(id=article.id(), title='Correction: Human CYTOMEGALOVIRUS IE1 alters the higher-order chromatin structure by targeting the acidic patch of the nucleosome')

@pytest.mark.continuum
def test_article_multiple_versions(generate_article, modify_article):
    template_id = 15893
    article = generate_article(template_id)
    _ingest_and_publish(article)
    new_article = modify_article(article, new_version=2, replacements={'cytomegalovirus': 'CYTOMEGALOVIRUS'})
    article_from_api = _ingest_and_publish(new_article)
    version1_content = checks.JOURNAL.article(id=article.id(), volume=article_from_api['volume'], version=1)
    assert 'cytomegalovirus' in version1_content
    assert 'CYTOMEGALOVIRUS' not in version1_content

# this is a silent correction of a 'correction' article, don't be confused
# we use this article because it's small and fast to process
# the silent correction is changing one word from lowercase to uppercase
@pytest.mark.continuum
def test_article_silent_correction(generate_article, modify_article):
    template_id = 15893
    article = generate_article(template_id)
    _ingest_and_publish(article)

    # TODO: for stability, wait until all the publishing workflows have finished
    checks.GITHUB_XML.article(id=article.id(), version=article.version(), text_match='cytomegalovirus')

    silent_correction_start = datetime.now()
    silently_corrected_article = modify_article(article, replacements={'cytomegalovirus': 'CYTOMEGALOVIRUS'})
    _feed_silent_correction(silently_corrected_article)
    input.SILENT_CORRECTION.article(os.path.basename(silently_corrected_article.filename()))
    checks.API.wait_article(id=article.id(), title='Correction: Human CYTOMEGALOVIRUS IE1 alters the higher-order chromatin structure by targeting the acidic patch of the nucleosome')
    checks.GITHUB_XML.article(id=article.id(), version=article.version(), text_match='CYTOMEGALOVIRUS')
    checks.ARCHIVE.of(id=article.id(), version=article.version(), last_modified_after=silent_correction_start)


@pytest.mark.continuum
def test_article_already_present_version(generate_article, version_article):
    template_id = 15893
    article = generate_article(template_id)
    _ingest_and_publish(article)
    new_article = version_article(article, new_version=1)
    _ingest(new_article)
    # article stops sometimes in this state, sometimes in 'published'?
    #checks.DASHBOARD.publication_in_progress(id=article.id(), version=article.version())
    error = checks.DASHBOARD.error(id=article.id(), version=1, run=2)
    assert re.match(r".*already published article version.*", error['event-message']), ("Error found on the dashboard does not match the expected description: %s" % error)

@pytest.mark.continuum
def test_article_with_unicode_content(generate_article):
    article = generate_article(template_id=19532)
    _ingest(article)
    _publish(article)
    checks.API.wait_article(id=article.id())
    journal_page = checks.JOURNAL.article(id=article.id(), volume=5, has_figures=article.has_figures())
    print journal_page
    assert "Szymon \xc5\x81\xc4\x99ski" in journal_page

@pytest.mark.continuum
@pytest.mark.search
def test_searching_for_a_new_article(generate_article, modify_article):
    template_id = 15893
    invented_word = _invented_word()
    new_article = modify_article(generate_article(template_id), replacements={'cytomegalovirus':invented_word})
    _ingest_and_publish(new_article)
    result = checks.API.wait_search(invented_word)
    assert len(result['items']) == 1, "Searching for %s returned too many results: %d" % (invented_word, len(result['items']))

def _ingest(article):
    input.PRODUCTION_BUCKET.upload(article.filename(), article.id())

def _feed_silent_correction(article):
    input.SILENT_CORRECTION_BUCKET.upload(article.filename(), article.id())

def _wait_for_publishable(article):
    # fails quite often but is now late in the process, can we make an intermediate check?
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
    checks.DASHBOARD.ready_to_publish(id=article.id(), version=article.version(), run=run)
    return run

def _wait_for_published(article):
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
    return article_from_api

def _publish(article):
    run = _wait_for_publishable(article)
    input.DASHBOARD.publish(id=article.id(), version=article.version(), run=run)


def _ingest_and_publish(article):
    _ingest(article)
    _publish(article)
    return _wait_for_published(article)

def _invented_word():
    return ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(30))
