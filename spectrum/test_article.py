"Test that involve publishing articles and checking their visibility and correctness throughout different systems"
from datetime import datetime
from os import path
import re
import pytest
import requests
from bs4 import BeautifulSoup

from spectrum import articles
from spectrum import generator
from spectrum import input
from spectrum import checks

SIMPLEST_ARTICLE_ID = 15893

@pytest.mark.continuum
@pytest.mark.article
@pytest.mark.journal
@pytest.mark.bot
@pytest.mark.lax
@pytest.mark.parametrize("template_id", generator.all_stored_articles())
def test_article_first_version(template_id, article_id_filter, generate_article):
    if article_id_filter:
        if template_id != article_id_filter:
            pytest.skip("Filtered out through the article_id_filter")

    article = generate_article(template_id)
    _ingest_and_publish_and_wait_for_published(article)

@pytest.mark.bot
@pytest.mark.skip(reason="unstable due to memoization in CSV parsing not picking up new files")
def test_package_poa(poa_csvs, poa_zip):
    sample_article_id = 36157
    article_id = generator.generate_article_id(sample_article_id)

    for csv_file in poa_csvs(source_article_id=sample_article_id, target_article_id=article_id):
        input.EJP.upload(csv_file)

    zip_file = poa_zip(source_article_id=sample_article_id, target_article_id=article_id)
    input.POA_DELIVERY.upload(zip_file)

    input.BOT_WORKFLOWS.package_poa(path.basename(zip_file))

    checks.PACKAGING_BUCKET_POA_ZIP.of(id=article_id)
    checks.PACKAGING_BUCKET_POA_XML.of(id=article_id)
    checks.PACKAGING_BUCKET_POA_PDF.of(id=article_id)


@pytest.mark.journal
@pytest.mark.continuum
@pytest.mark.bot
@pytest.mark.lax
def test_article_multiple_ingests_of_the_same_version(generate_article, modify_article):
    run1_start = datetime.now()
    article = generate_article(SIMPLEST_ARTICLE_ID)
    articles.ingest(article)
    run1 = articles.wait_for_publishable(article, run_after=run1_start)
    checks.CDN_XML.of(text_match='cytomegalovirus', id=article.id(), version=article.version())

    run2_start = datetime.now()
    modified_article = modify_article(article, replacements={'cytomegalovirus': 'CYTOMEGALOVIRUS'})
    articles.ingest(modified_article)
    article_on_dashboard = checks.DASHBOARD.ready_to_publish(id=article.id(), version=article.version(), run_after=run2_start)
    run2 = article_on_dashboard['versions'][str(article.version())]['runs']['2']['run-id']
    assert run2 != run1, "A new run should have been triggered"
    input.DASHBOARD.publish(id=article.id(), version=article.version(), run=run2)
    checks.API.wait_article(id=article.id(), title='Correction: Human CYTOMEGALOVIRUS IE1 alters the higher-order chromatin structure by targeting the acidic patch of the nucleosome')
    checks.CDN_XML.of(text_match='CYTOMEGALOVIRUS', id=article.id(), version=article.version())

@pytest.mark.journal
@pytest.mark.continuum
@pytest.mark.metrics
@pytest.mark.bot
@pytest.mark.lax
def test_article_multiple_versions(generate_article, modify_article):
    article = generate_article(SIMPLEST_ARTICLE_ID)
    _ingest_and_publish_and_wait_for_published(article)
    checks.GITHUB_XML.article(id=article.id(), version=article.version())
    new_article = modify_article(article, new_version=2, replacements={'cytomegalovirus': 'CYTOMEGALOVIRUS'})
    _ingest_and_publish_and_wait_for_published(new_article)
    checks.GITHUB_XML.article(id=new_article.id(), version=new_article.version())
    version1_content = checks.JOURNAL.article(id=article.id(), version=1)
    assert 'cytomegalovirus' in version1_content
    assert 'CYTOMEGALOVIRUS' not in version1_content
    version2_content_cdn = checks.JOURNAL_CDN.article(id=article.id(), version=2)
    assert 'CYTOMEGALOVIRUS' in version2_content_cdn
    assert 'cytomegalovirus' not in version2_content_cdn

# this is a silent correction of a 'correction' article, don't be confused
# we use this article because it's small and fast to process
# the silent correction is changing one word from lowercase to uppercase
@pytest.mark.journal
@pytest.mark.continuum
@pytest.mark.bot
@pytest.mark.lax
def test_article_silent_correction(generate_article, modify_article):
    article = generate_article(SIMPLEST_ARTICLE_ID)
    _ingest_and_publish_and_wait_for_published(article)

    # TODO: for stability, wait until all the publishing workflows have finished. Github xml is enough
    checks.GITHUB_XML.article(id=article.id(), version=article.version(), text_match='cytomegalovirus')
    checks.CDN_XML.of(text_match='cytomegalovirus', id=article.id(), version=article.version())

    silent_correction_start = datetime.now()
    silently_corrected_article = modify_article(article, replacements={'cytomegalovirus': 'CYTOMEGALOVIRUS'})
    articles.feed_silent_correction(silently_corrected_article)
    checks.API.wait_article(id=article.id(), title='Correction: Human CYTOMEGALOVIRUS IE1 alters the higher-order chromatin structure by targeting the acidic patch of the nucleosome')
    checks.GITHUB_XML.article(id=article.id(), version=article.version(), text_match='CYTOMEGALOVIRUS')
    checks.ARCHIVE.of(id=article.id(), version=article.version(), last_modified_after=silent_correction_start)
    checks.CDN_XML.of(text_match='CYTOMEGALOVIRUS', id=article.id(), version=article.version())

@pytest.mark.journal
@pytest.mark.continuum
@pytest.mark.bot
@pytest.mark.lax
def test_article_subject_change(generate_article):
    article = generate_article(SIMPLEST_ARTICLE_ID)
    _ingest_and_publish_and_wait_for_published(article)
    # TODO: for stability, wait until all the publishing workflows have finished. Github xml is enough
    checks.GITHUB_XML.article(id=article.id(), version=article.version(), text_match='cytomegalovirus')

    subjects_configuration = generator.article_subjects({article.id(): "Immunology"})
    input.BOT_CONFIGURATION.upload(subjects_configuration.filename(), 'article_subjects_data/article_subjects.csv')
    articles.feed_silent_correction(article)
    checks.API.wait_article(id=article.id(), subjects=[{'name':'Immunology', 'id': 'immunology'}])
    # are there caches that need to expire first?
    checks.JOURNAL.article_only_subject(id=article.id(), version=article.version(), subject_id='immunology')

@pytest.mark.continuum
@pytest.mark.bot
@pytest.mark.lax
def test_article_already_present_version(generate_article, version_article):
    article = generate_article(SIMPLEST_ARTICLE_ID)
    _ingest_and_publish_and_wait_for_published(article)
    new_article = version_article(article, new_version=1)
    articles.ingest(new_article)
    # article stops sometimes in this state, sometimes in 'published'?
    #checks.DASHBOARD.publication_in_progress(id=article.id(), version=article.version())
    error = checks.DASHBOARD.error(id=article.id(), version=1, run=2)
    assert re.match(r".*already published article version.*", error['event-message']), ("Error found on the dashboard does not match the expected description: %s" % error)

@pytest.mark.journal
@pytest.mark.continuum
@pytest.mark.bot
@pytest.mark.lax
def test_article_with_unicode_content(generate_article):
    article = generate_article(template_id=19532)
    _ingest_and_publish(article)
    checks.API.wait_article(id=article.id())
    journal_page = checks.JOURNAL.article(id=article.id(), has_figures=article.has_figures())
    assert "Szymon Łęski" in journal_page

@pytest.mark.journal
def test_googlebot_sees_citation_metadata(generate_article):
    article = generate_article(template_id=SIMPLEST_ARTICLE_ID)
    _ingest_and_publish(article)
    checks.API.wait_article(id=article.id())

    def find_citation_metadata(html):
        soup = BeautifulSoup(html, "html.parser")

        return soup.find_all("meta", {"name": re.compile("^citation_")})

    # As Googlebot

    page = checks.JOURNAL_GOOGLEBOT.article(id=article.id())
    citation_metadata = find_citation_metadata(page)

    assert len(citation_metadata) > 0, "Expected citation metadata for Googlebot, found none"

    # As public

    page = checks.JOURNAL_CDN.article(id=article.id())
    citation_metadata = find_citation_metadata(page)

    assert len(citation_metadata) == 0, "Expected no citation metadata publically, found %d meta elements" % (len(citation_metadata))

@pytest.mark.journal
@pytest.mark.continuum
@pytest.mark.search
@pytest.mark.lax
def test_searching_for_a_new_article(generate_article, modify_article):
    template_id = '00666'
    invented_word = input.invented_word()
    new_article = modify_article(generate_article(template_id), replacements={'falciparum':invented_word})
    _ingest_and_publish_and_wait_for_published(new_article)
    result = checks.API.wait_search(invented_word)
    assert len(result['items']) == 1, "Searching for %s returned too many results: %d" % (invented_word, len(result['items']))
    checks.JOURNAL.search(invented_word, count=1)
    checks.JOURNAL_CDN.search(invented_word, count=1)

@pytest.mark.journal
@pytest.mark.recommendations
@pytest.mark.lax
def test_recommendations_for_new_articles(generate_article):
    template_id = '06847'
    related_template_id = '22661'

    first_article = generate_article(template_id)
    _ingest_and_publish_and_wait_for_published(first_article)
    second_article = generate_article(related_template_id, related_article_id=first_article.id())
    _ingest_and_publish_and_wait_for_published(second_article)

    def _single_relation(from_id, to_id):
        related = [a for a in checks.API.related_articles(from_id) if a['type'] != 'external-article']
        assert len(related) == 1, "There should be 1 related article to %s, but the result is: %s" % (from_id, related)
        assert related[0]['id'] == to_id, "The related article of %s should be %s but it is %s" % (from_id, to_id, related[0]['id'])

    _single_relation(from_id=first_article.id(), to_id=second_article.id())
    _single_relation(from_id=second_article.id(), to_id=first_article.id())

    for article, recommended in [(first_article, second_article), (second_article, first_article)]:
        result = checks.API.wait_recommendations(article.id())
        assert len(result['items']) >= 1
        assert result['items'][0]['id'] == recommended.id()
        # load the article page, this will call recommendations
        checks.JOURNAL.article(id=article.id())
        # see if it propagates through CDN?
        checks.JOURNAL_CDN.article(id=article.id())

@pytest.mark.continuum
@pytest.mark.article
@pytest.mark.bot
def test_article_propagates_to_github(generate_article):
    article = generate_article(SIMPLEST_ARTICLE_ID)
    _ingest_and_publish_and_wait_for_published(article)
    checks.GITHUB_XML.article(id=article.id(), version=article.version())

@pytest.mark.journal_cms
@pytest.mark.continuum
@pytest.mark.lax
def test_adding_article_fragment(generate_article, modify_article):
    journal_cms_session = input.JOURNAL_CMS.login()
    invented_word = input.invented_word()
    article = modify_article(generate_article(SIMPLEST_ARTICLE_ID), replacements={'cytomegalovirus':invented_word})
    _ingest_and_publish_and_wait_for_published(article)

    journal_cms_session.create_article_fragment(id=article.id(), image='./spectrum/fixtures/king_county.jpg')
    article = checks.API.wait_article(article.id(), item_check=checks.API.item_check_image())
    image_uri = article['image']['thumbnail']['source']['uri']
    response = requests.head(image_uri)
    checks.LOGGER.info("Found %s: %s", image_uri, response.status_code)
    assert response.status_code == 200, "Image %s is not loading" % image_uri
    checks.API.wait_search(invented_word, item_check=checks.API.item_check_image(image_uri))


#@pytest.mark.bot
#def test_downstream_upload_to_pubmed(generate_article):
#    article = generate_article(SIMPLEST_ARTICLE_ID)
#    input.PACKAGING_BUCKET.clean("pubmed/outbox/")
#    test_start = datetime.now()

#    _ingest_and_publish_and_wait_for_published(article)
#    checks.PACKAGING_BUCKET_OUTBOX.of(vendor="pubmed", folder="outbox", id=article.id())
#    input.BOT_WORKFLOWS.pubmed()

#    (xml, ) = checks.PACKAGING_BUCKET_BATCH.of(vendor="pubmed", last_modified_after=test_start)
#    checks.PUBMED.of(xml=xml)


@pytest.mark.personalised_covers
@pytest.mark.continuum
@pytest.mark.bot
def test_personalised_covers_for_new_articles(generate_article):
    article = generate_article(SIMPLEST_ARTICLE_ID)
    _ingest_and_publish_and_wait_for_published(article)
    checks.PERSONALISED_COVERS_A4.of(id=article.id())
    checks.PERSONALISED_COVERS_LETTER.of(id=article.id())

@pytest.mark.observer
@pytest.mark.lax
def test_rss_feed_contains_new_article(generate_article):
    article = generate_article(SIMPLEST_ARTICLE_ID)
    _ingest_and_publish_and_wait_for_published(article)
    checks.OBSERVER.latest_article(article.id())

def test_bioprotocol_has_protocol_data(generate_article):
    # the payload is for this article.
    # we're not going so far in this test as to do link checking (yet)
    article_with_mandms = "00790"
    article_with_mandms = SIMPLEST_ARTICLE_ID
    article = generate_article(article_with_mandms)
    _ingest_and_publish_and_wait_for_published(article)
    input.BIOPROTOCOL.create_bioprotocol_data(article.id())
    checks.API.bioprotocol(article.id())

#

def _wait_for_published(article):
    checks.DASHBOARD.published(id=article.id(), version=article.version())
    checks.LAX.published(id=article.id(), version=article.version())

    checks.ARCHIVE.of(id=article.id(), version=article.version())
    article_from_api = checks.API.article(id=article.id(), version=article.version())
    checks.JOURNAL.article(id=article.id(), has_figures=article.has_figures())
    checks.JOURNAL_CDN.article(id=article.id(), has_figures=article.has_figures())
    return article_from_api

def _publish(article, run_after):
    run = articles.wait_for_publishable(article, run_after)
    articles.publish(article, run)

def _ingest_and_publish_and_wait_for_published(article):
    _ingest_and_publish(article)
    return _wait_for_published(article)

def _ingest_and_publish(article):
    ingestion_start = datetime.now()
    articles.ingest(article)
    _publish(article, run_after=ingestion_start)
