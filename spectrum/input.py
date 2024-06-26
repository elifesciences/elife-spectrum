"""utility library for interacting with remote services, such as:

* dashboard
* journal
* elife-bot
* journal-cms

contains no tests to be run."""

import os
import random
import string
import contextlib
import requests
from econtools import econ_workflow
import mechanicalsoup
from spectrum import aws, logger
from spectrum.config import SETTINGS


LOGGER = logger.logger(__name__)

@contextlib.contextmanager
def modified_environ(env_updates):
    old_env = dict(os.environ)
    os.environ.update(env_updates)
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(old_env)

class InputBucket:
    def __init__(self, s3, bucket_name):
        self._s3 = s3
        self._bucket_name = bucket_name

    def upload(self, filename, destination_filename=None, id=None):
        if not destination_filename:
            destination_filename = os.path.basename(filename)
        self._s3.meta.client.upload_file(filename, self._bucket_name, destination_filename)
        LOGGER.info("Uploaded %s to %s/%s", filename, self._bucket_name, destination_filename, extra={'id': id})

    def clean(self, prefix=None):
        aws.clean_bucket(self._bucket_name, prefix)

    def name(self):
        return self._bucket_name

class Dashboard:
    def __init__(self, host, user, password):
        self._host = host
        self._user = user
        self._password = password

    def publish(self, id, version, run):
        template = "%s/api/queue_article_publication"
        url = template % self._host
        body = {'articles': [{'id': id, 'version': version, 'run': run}]}
        response = requests.post(url, auth=(self._user, self._password), json=body)
        assert response.status_code == 200, ("Response status was %s: %s" % (response.status_code, response.text))
        LOGGER.info(
            "Pressed Publish for %s version %s run %s on dashboard",
            url,
            version,
            run,
            extra={'id': id}
        )

class BotWorkflowStarter:
    def __init__(self, aws_access_key_id, aws_secret_access_key, region_name, queue_name):
        self._aws_access_key_id = aws_access_key_id
        self._aws_secret_access_key = aws_secret_access_key
        self._region_name = region_name
        self._queue_name = queue_name

    def pubmed(self):
        LOGGER.info("Starting workflow PubmedArticleDeposit")
        env_updates = {
            'AWS_ACCESS_KEY_ID': self._aws_access_key_id,
            'AWS_SECRET_ACCESS_KEY': self._aws_secret_access_key,
            'AWS_DEFAULT_REGION': self._region_name
        }
        with modified_environ(env_updates):
            econ_workflow.start_workflow(
                self._queue_name,
                workflow_name='PubmedArticleDeposit'
            )

    def package_poa(self, filename):
        LOGGER.info("Starting workflow PackagePOA(document=%s)", filename)
        env_updates = {
            'AWS_ACCESS_KEY_ID': self._aws_access_key_id,
            'AWS_SECRET_ACCESS_KEY': self._aws_secret_access_key,
            'AWS_DEFAULT_REGION': self._region_name
        }
        with modified_environ(env_updates):
            econ_workflow.start_workflow(
                self._queue_name,
                workflow_name='PackagePOA',
                workflow_data={
                    'document': filename,
                }
            )

class JournalCms:
    def __init__(self, host, user, password):
        self._host = host
        self._user = user
        self._password = password

    def login(self):
        browser = mechanicalsoup.Browser()
        login_url = "%s/user/login" % self._host
        login_page = browser.get(login_url)
        form = mechanicalsoup.Form(login_page.soup.form)
        form.input({'name': self._user, 'pass': self._password})
        response = browser.submit(form, login_page.url)
        assert _journal_cms_page_title(response.soup) == self._user
        return JournalCmsSession(self._host, browser)

class JournalCmsSession:
    def __init__(self, host, browser):
        self._host = host
        self._browser = browser

    def create_podcast_episode(self, title, image, uri, chapter_title):
        create_url = "%s/node/add/podcast_episode" % self._host
        create_page = self._browser.get(create_url)
        form = mechanicalsoup.Form(create_page.soup.form)
        form.input({'title[0][value]': title})

        form.attach({'files[field_image_0]': image})
        LOGGER.info("Attaching image")

        form.input({'field_episode_mp3[0][uri]': uri})
        chapter_title_field = create_page.soup.form.find('input', {'name': 'field_episode_chapter[form][0][title][0][value]'})
        # Leave this condition in until after inline_entity_form is updated
        if chapter_title_field is None:
            chapter_title_field = create_page.soup.form.find('input', {'name': 'field_episode_chapter[form][inline_entity_form][title][0][value]'})
        chapter_title_field['value'] = chapter_title

        response = self._browser.submit(form, create_page.url, data={'op': 'Save'})
        # requests follows redirects by default
        _assert_html_response(response)
        assert _journal_cms_page_title(response.soup) == title

    def create_article_fragment(self, id, image):
        filtered_content_url = "%s/admin/content?status=All&type=article&title=%s" % (self._host, id)
        filtered_content_page = self._browser.get(filtered_content_url)
        assert filtered_content_page.status_code == 200, \
            "Response status of %s was: %s\nBody: %s" % (filtered_content_url, filtered_content_page.status_code, filtered_content_page.content)

        try:
            view_url = "%s%s" % (self._host, filtered_content_page.soup.find('td', 'views-field-title').find('a', href=True, string=id).get('href'))
            edit_url = "%s%s" % (self._host, filtered_content_page.soup.find('td', 'views-field-operations').find('li', 'edit').find('a', href=True, string='Edit').get('href'))
        except (AttributeError, TypeError) as exc:
            raise AssertionError('Edit link not found for article %s when loading URL %s' % (id, filtered_content_url)) from exc

        LOGGER.info("Access edit form", extra={'id': id})

        edit_page = self._browser.get(edit_url)

        form = mechanicalsoup.Form(edit_page.soup.form)

        if edit_page.soup.find('input', {'name': 'field_image_0_remove_button'}):
            self._choose_submit(form, 'field_image_0_remove_button', value='Remove')
            LOGGER.info("Removing existing thumbnail", extra={'id': id})
            response = self._browser.submit(form, edit_page.url)
            form = mechanicalsoup.Form(response.soup.form)

        LOGGER.info("Attaching thumbnail %s", image, extra={'id': id})
        form.attach({'files[field_image_0]': image})

        LOGGER.info("Saving form", extra={'id': id})
        # Button text will be 'Save and keep published' or 'Save and keep unpublished'
        button_text = edit_page.soup.find('div', {'id': 'edit-actions'}).find('input', 'form-submit').get('value')
        response = self._browser.submit(form, edit_page.url, data={'op': button_text})
        # request follows redirects by default
        _assert_html_response(response)

        # lsh@2022-10-18: I don't know what the problem here is, everything is difficult to debug, but I've spent
        # a lot of time beating my head against it.
        # I suspect it's a timing issue, either too quick to check the 'view' URL or
        # a bad interaction with the event listener and article events.
        # the 'find_img' code below is just temporary to rule out the too-quick hypothesis.
        # - https://github.com/elifesciences/issues/issues/7719
        # - https://github.com/elifesciences/issues/issues/6670

        def find_img():
            view_page = self._browser.get(view_url)
            img_selector = ".field--name-field-image img"
            img = view_page.soup.select_one(img_selector)
            try:
                assert img is not None, ("Cannot find %r in %s response\n%s" % (img_selector, view_page.status_code, view_page.content))
                assert "king_county" in img.get('src')
                LOGGER.info("Tag: %s", img, extra={'id': id})
                return True, None
            except AssertionError as err:
                return False, err

        for _ in range(0, 3):
            success, err = find_img()
            if success:
                return

        LOGGER.error("Failed to find image after 3 attempts")

        raise err

    def _choose_submit(self, wrapped_form, name, value=None):
        """Fixed version of mechanicalsoup.Form.choose_submit()

        https://github.com/hickford/MechanicalSoup/issues/61"""

        form = wrapped_form.form

        criteria = {"name":name}
        if value:
            criteria['value'] = value
        chosen_submit = form.find("input", criteria)

        for inp in form.select("input"):
            if inp.get('type') != 'submit':
                continue
            if inp == chosen_submit:
                continue
            del inp['name']


def _assert_html_response(response):
    assert response.status_code == 200, "Response from saving the form was expected to be 200 from the listing page, but it was %s\nBody: %s" % (response.status_code, response.text)

def _journal_cms_page_title(soup):
    # <h1 class="js-quickedit-page-title title page-title"><span data-quickedit-field-id="node/1709/title/en/full" class="field field--name-title field--type-string field--label-hidden">Spectrum blog article: jvsfz4oj9vz9hk239fbpq4fbjc9yoh</span></h1>
    #<h1 class="js-quickedit-page-title title page-title">alfred</h1>
    return soup.find("h1", {"class": "page-title"}).text.strip()

class Journal:
    def __init__(self, host):
        self._host = host

    def session(self):
        browser = mechanicalsoup.Browser()
        return JournalHtmlSession(self._host, browser)

    def javascript_session(self, driver):
        return JournalJavaScriptSession(driver, self._host)


class JournalJavaScriptSession:
    ID_SUBMIT_MY_RESEARCH = 'submitResearchButton'

    def __init__(self, driver, host):
        self._driver = driver
        self._host = host

    def _log(self, message, *args, **kwargs):
        LOGGER.info(message, extra={'app':'journal'}, *args, **kwargs)

    def submit(self):
        LOGGER.info("Loading: %s", self._host)
        self._driver.get(self._host)
        selenium_title_smoke_test('eLife', self._driver)

        submit_link = self._driver.find_element_by_id(self.ID_SUBMIT_MY_RESEARCH)
        self._log("Found #%s `%s`", self.ID_SUBMIT_MY_RESEARCH, submit_link.text)
        submit_link.click()
        self._log("Clicked #%s", self.ID_SUBMIT_MY_RESEARCH)

        selenium_title_smoke_test('eLife', self._driver)
        # expand: click on login button, log in, and check final destination
        # lsh@2020-10-22: xpub removed without replacement
        #return XpubJavaScriptSession(self._driver)


class JournalHtmlSession:
    PROFILE_LINK = ".login-control__non_js_control_link"

    def __init__(self, host, browser):
        self._host = host
        self._browser = browser

    # TODO: automatically pass Referer when MechanicalSoup is upgraded to allow it
    def login(self, referer=None):
        login_url = "%s/log-in" % self._host
        headers = {}
        if referer:
            headers['Referer'] = '%s%s' % (self._host, referer)
        LOGGER.info("Logging in at %s (headers %s)", login_url, headers)
        logged_in_page = self._browser.get(login_url, headers=headers)
        # should be automatically redirected back by simulator
        LOGGER.info("Redirected to %s after log in", logged_in_page.url)
        _assert_html_response(logged_in_page)

        # if changing to another check, move in logout()
        profile = logged_in_page.soup.select_one(self.PROFILE_LINK)
        assert profile is not None, ("Cannot find %s in %s response\n%s" % (self.PROFILE_LINK, logged_in_page.status_code, logged_in_page.content))
        LOGGER.info("Found logged-in profile button at %s", self.PROFILE_LINK)

        return logged_in_page

    def logout(self):
        logout_url = "%s/log-out" % self._host
        LOGGER.info("Logging out at %s", logout_url)
        logged_out_page = self._browser.get(logout_url)
        LOGGER.info("Redirected to %s after log out", logged_out_page.url)
        _assert_html_response(logged_out_page)

        profile = logged_out_page.soup.select_one(self.PROFILE_LINK)
        assert profile is None, ("Found %s in %s response\n%s" % (self.PROFILE_LINK, logged_out_page.status_code, logged_out_page.content))

    def check(self, page_path):
        LOGGER.info("Loading page %s", page_path)
        page = self._browser.get("%s/%s" % (self._host, page_path.lstrip('/')))
        _assert_html_response(page)

        return page

class BioProtocol:
    def __init__(self, int_host, user, password):
        self.int_host = int_host
        self.user = user
        self.password = password

    def create_bioprotocol_data(self, article_id):
        "generates bioprotocol for given article data and posts it to the bioprotocol service"
        payload = [
            {
                "ProtocolSequencingNumber": "s4-1",
                "ProtocolTitle": "Protein production",
                "IsProtocol": True,
                "ProtocolStatus": 0,
                "URI": "https://en.bio-protocol.org/rap.aspx?eid=24419&item=s4-1"
            },
            {
                "ProtocolSequencingNumber": "s4-2",
                "ProtocolTitle": "Chitin-triggered alkalinization of tomato cell suspension",
                "IsProtocol": False,
                "ProtocolStatus": 0,
                "URI": "https://en.bio-protocol.org/rap.aspx?eid=24419&item=s4-2"
            }
        ]
        # http://end2end--bp.elife.internal/bioprotocol/article/123456789
        template = "%s/bioprotocol/article/%s"
        url = template % (self.int_host, article_id)
        response = requests.post(url, auth=(self.user, self.password), json=payload)
        assert response.status_code == 200, ("Response status was %s: %s" % (response.status_code, response.text))

def invented_word(length=30, characters=None):
    if not characters:
        characters = string.ascii_lowercase + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def selenium_title_smoke_test(portion, driver):
    title = driver.title
    assert portion in title, "Title: %s\nCurrent URL: %s" % (title, driver.current_url)

PRODUCTION_BUCKET = InputBucket(aws.S3, SETTINGS['bucket_input'])
DIGESTS_BUCKET = InputBucket(aws.S3, SETTINGS['bucket_digests_input'])
SILENT_CORRECTION_BUCKET = InputBucket(aws.S3, SETTINGS['bucket_silent_corrections'])
PACKAGING_BUCKET = InputBucket(aws.S3, SETTINGS['bucket_packaging'])
POA_DELIVERY = InputBucket(aws.S3, SETTINGS['bucket_ejp_poa_delivery'])
EJP = InputBucket(aws.S3, SETTINGS['bucket_ejp_ftp'])
DASHBOARD = Dashboard(
    SETTINGS['dashboard_host'],
    SETTINGS['dashboard_user'],
    SETTINGS['dashboard_password']
)

JOURNAL_CMS = JournalCms(
    SETTINGS['journal_cms_host'],
    SETTINGS['journal_cms_user'],
    SETTINGS['journal_cms_password']
)

JOURNAL = Journal(
    SETTINGS['journal_host']
)

JOURNAL_CDN = Journal(
    SETTINGS['journal_cdn_host']
)

BOT_WORKFLOWS = BotWorkflowStarter(
    SETTINGS['aws_access_key_id'],
    SETTINGS['aws_secret_access_key'],
    SETTINGS['region_name'],
    SETTINGS['queue_workflow_starter']
)

BOT_CONFIGURATION = InputBucket(aws.S3, SETTINGS['bucket_configuration'])

BIOPROTOCOL = BioProtocol(
    SETTINGS['bioprotocol_int_host'],
    SETTINGS['bioprotocol_user'],
    SETTINGS['bioprotocol_password'])
