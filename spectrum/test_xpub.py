"Tests that involve Xpub integrations"
from datetime import datetime
import pytest
from spectrum import generator, input, checks

@pytest.mark.journal
@pytest.mark.profiles
@pytest.mark.xpub
def test_login(get_selenium_driver):
    journal_session = input.JOURNAL_CDN.javascript_session(get_selenium_driver())
    xpub_session = journal_session.submit()
    xpub_session.login()

# FUTURE: add to journal_cms when included
#@pytest.mark.journal_cms
@pytest.mark.xpub
def test_initial_submission(get_selenium_driver):
    journal_session = input.JOURNAL_CDN.javascript_session(get_selenium_driver())
    xpub_session = journal_session.submit()
    xpub_session.login()

    author_page = xpub_session.dashboard().create_initial_submission()
    author_page.populate_required_fields()
    files_page = author_page.next()

    files_page.populate_required_fields()
    submission_page = files_page.next()

    title = generator.generate_article_title()
    submission_page.populate_required_fields(title)
    editors_page = submission_page.next()

    editors_page.populate_required_fields()
    disclosure_page = editors_page.next()
    disclosure_page.acknowledge()
    submission_time = datetime.now()
    disclosure_page.submit()

    meca_titles = [checks.MecaFile(url).title() for url in checks.XPUB_MECA.recent_files(after=submission_time)]
    assert title in meca_titles
