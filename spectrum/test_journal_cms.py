"Tests that go through Journal CMS and propagate content to the rest of the system"
import pytest
import requests
from spectrum import input
from spectrum import checks

@pytest.mark.journal_cms
def test_login():
    input.JOURNAL_CMS.login()

@pytest.mark.journal_cms
@pytest.mark.search
def test_content_type_propagates_to_other_services():
    journal_cms_session = input.JOURNAL_CMS.login()

    invented_word = input.invented_word()
    title = 'Spectrum podcast episode: %s' % invented_word

    journal_cms_session.create_podcast_episode(title=title, image='./spectrum/fixtures/king_county.jpg', uri='https://cdn.elifesciences.org/podcast-episode.mp3', chapter_title='Chapter 1')
    result = checks.API.wait_search(invented_word)
    assert result['total'] == 1, "There should only be one result containing this word"
    assert result['items'][0]['title'] == title, "The title of the podcast episode found through search is incorrect"
    number = result['items'][0]['number']
    podcast_episode = checks.API.podcast_episode(number)
    # TODO: transition to IIIF and use a IiifCheck object
    image_url = blog_article['image']['banner']['source']['uri']
    response = requests.head(image_url)
    checks.LOGGER.info("Found %s: %s", image_url, response.status_code)
    assert response.status_code == 200, "Image %s is not loading" % image_url

