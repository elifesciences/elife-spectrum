from os import path
import random
import string
import requests
from spectrum import aws, logger
from spectrum.config import SETTINGS
from econtools import econ_article_feeder
from pollute import modified_environ
import mechanicalsoup

LOGGER = logger.logger(__name__)

class InputBucket:
    def __init__(self, s3, bucket_name):
        self._s3 = s3
        self._bucket_name = bucket_name

    def upload(self, filename, id):
        self._s3.meta.client.upload_file(filename, self._bucket_name, path.basename(filename))
        LOGGER.info("Uploaded %s to %s", filename, self._bucket_name, extra={'id': id})

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
        body = {}
        body = {'articles': [{'id': id, 'version': version, 'run': run}]}
        response = requests.post(url, auth=(self._user, self._password), json=body, verify=False)
        assert response.status_code == 200, ("Response status was %s: %s" % (response.status_code, response.text))
        LOGGER.info(
            "Pressed Publish for %s version %s run %s on dashboard",
            url,
            version,
            run,
            extra={'id': id}
        )

class SilentCorrectionWorkflowStarter:
    def __init__(self, aws_access_key_id, aws_secret_access_key, region_name, input_bucket_name, queue_name, workflow_name):
        self._aws_access_key_id = aws_access_key_id
        self._aws_secret_access_key = aws_secret_access_key
        self._region_name = region_name
        self._input_bucket_name = input_bucket_name
        self._queue_name = queue_name
        self._workflow_name = workflow_name

    def article(self, filename):
        with modified_environ(added={'AWS_ACCESS_KEY_ID': self._aws_access_key_id, 'AWS_SECRET_ACCESS_KEY': self._aws_secret_access_key, 'AWS_DEFAULT_REGION': self._region_name}):
            econ_article_feeder.feed_econ(
                self._input_bucket_name,
                self._queue_name,
                rate=1,
                prefix=filename,
                workflow_name='SilentCorrectionsIngest'
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

    def create_blog_article(self, title, text='Lorem ipsum', image=None):
        create_url = "%s/node/add/blog_article" % self._host
        create_page = self._browser.get(create_url)
        form = mechanicalsoup.Form(create_page.soup.form)
        form.input({'title[0][value]': title})
        LOGGER.info("Adding paragraph")
        self._choose_submit(form, 'field_content_paragraph_add_more')
        response = self._browser.submit(form, create_page.url)
        form = mechanicalsoup.Form(response.soup.form)
        form.textarea({'field_content[0][subform][field_block_html][0][value]': text})
        if image:
            form.attach({'files[field_image_0]': image})
            LOGGER.info("Attaching image")

        LOGGER.info("Saving form")
        self._choose_submit(form, 'op', value='Save and publish')
        # not sure why, but `data` here is necessary
        response = self._browser.submit(form, create_page.url, data={'op': 'Save and publish'})
        # requests follows redirects by default
        _assert_html_response(response)
        assert _journal_cms_page_title(response.soup) == title
        #check https://end2end--journal-cms.elifesciences.org/admin/content?status=All&type=All&title=b9djvu04y6v1t4kug4ts8kct5pagf8&langcode=All
        # but in checks module
        # TODO: return id and/or node id

    def create_article_fragment(self, id, image):
        filtered_content_url = "%s/admin/content?status=All&type=article&title=%s" % (self._host, id)
        filtered_content_page = self._browser.get(filtered_content_url)
        assert filtered_content_page.status_code == 200, "Response status of %s was: %s\nBody: %s" % (filtered_content_url, filtered_content_page.status_code, filtered_content_page.content)

        try:
            view_url = "%s%s" % (self._host, filtered_content_page.soup.find('td', 'views-field-title').find('a', href=True, text=id).get('href'))
            edit_url = "%s%s" % (self._host, filtered_content_page.soup.find('td', 'views-field-operations').find('li', 'edit').find('a', href=True, text='Edit').get('href'))
        except (AttributeError, TypeError):
            raise AssertionError('Edit link not found for article %s when loading URL %s' % (id, filtered_content_url))

        LOGGER.info(
            "Access edit form",
            extra={'id': id}
        )

        edit_page = self._browser.get(edit_url)

        form = mechanicalsoup.Form(edit_page.soup.form)

        if edit_page.soup.find('input', {'name': 'field_image_0_remove_button'}):
            self._choose_submit(form, 'field_image_0_remove_button', value='Remove')
            LOGGER.info(
                "Removing existing thumbnail",
                extra={'id': id}
            )
            response = self._browser.submit(form, edit_page.url)
            form = mechanicalsoup.Form(response.soup.form)

        form.attach({'files[field_image_0]': image})
        LOGGER.info(
            "Attaching thumbnail %s",
            image,
            extra={'id': id}
        )

        LOGGER.info(
            "Saving form",
            extra={'id': id}
        )
        # Button text will be 'Save and keep published' or 'Save and keep unpublished'
        button_text = edit_page.soup.find('div', {'id': 'edit-actions'}).find('input', 'form-submit').get('value')
        response = self._browser.submit(form, edit_page.url, data={'op': button_text})
        # requests follows redirects by default
        _assert_html_response(response)
        view_page = self._browser.get(view_url)
        img_selector = ".field--name-field-image img"
        img = view_page.soup.select_one(img_selector)
        assert img is not None, ("Cannot find %s in %s response\n%s" % (img_selector, view_page.status_code, view_page.content))
        assert "king_county" in img.get('src')
        LOGGER.info(
            "Tag: %s",
            img,
            extra={'id': id}
        )

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
    assert response.status_code == 200, "Response from saving the from was expected to be 200 from the listing page, but it was %s\nBody: %s" % (response.status_code, response.content)

def _journal_cms_page_title(soup):
    # <h1 class="js-quickedit-page-title title page-title"><span data-quickedit-field-id="node/1709/title/en/full" class="field field--name-title field--type-string field--label-hidden">Spectrum blog article: jvsfz4oj9vz9hk239fbpq4fbjc9yoh</span></h1>
    #<h1 class="js-quickedit-page-title title page-title">alfred</h1>
    return soup.find("h1", {"class": "page-title"}).text.strip()

class Journal:
    def __init__(self, host):
        self._host = host

    def session(self):
        browser = mechanicalsoup.Browser()
        return JournalSession(self._host, browser)

class JournalSession:
    def __init__(self, host, browser):
        self._host = host
        self._browser = browser

    def login(self):
        self._enable_feature_flag()

        login_url = "%s/log-in" % self._host
        # should be automatically redirected back by simulator
        logged_in_page = self._browser.get(login_url)
        _assert_html_response(logged_in_page)

        # if changing to another check, move in logout()
        profile_selector = ".login-control__non_js_control_link"
        profile = logged_in_page.soup.select_one(profile_selector)
        assert profile is not None, ("Cannot find %s in %s response\n%s" % (profile_selector, logged_in_page.status_code, logged_in_page.content))

        return logged_in_page

    def logout(self):
        logout_url = "%s/log-out" % self._host
        logged_in_page = self._browser.get(logout_url)
        _assert_html_response(logged_in_page)

        profile_selector = ".login-control__non_js_control_link"
        profile = logged_in_page.soup.select_one(profile_selector)
        assert profile is None, ("Found %s in %s response\n%s" % (profile_selector, logged_in_page.status_code, logged_in_page.content))

    def check(self, page_path):
        page = self._browser.get("%s/%s" % (self._host, page_path.lstrip('/')))
        _assert_html_response(page)

        return page

    def _enable_feature_flag(self):
        feature_flag = "%s/?open-sesame" % self._host
        flagged_page = self._browser.get(feature_flag)
        _assert_html_response(flagged_page)

def invented_word(length=30, characters=None):
    if not characters:
        characters = string.ascii_lowercase + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

PRODUCTION_BUCKET = InputBucket(aws.S3, SETTINGS['bucket_input'])
SILENT_CORRECTION_BUCKET = InputBucket(aws.S3, SETTINGS['bucket_silent_corrections'])
PACKAGING_BUCKET = InputBucket(aws.S3, SETTINGS['bucket_packaging'])
DASHBOARD = Dashboard(
    SETTINGS['dashboard_host'],
    SETTINGS['dashboard_user'],
    SETTINGS['dashboard_password']
)

SILENT_CORRECTION = SilentCorrectionWorkflowStarter(
    SETTINGS['aws_access_key_id'],
    SETTINGS['aws_secret_access_key'],
    SETTINGS['region_name'],
    SILENT_CORRECTION_BUCKET.name(),
    SETTINGS['queue_workflow_starter'],
    'SilentCorrectionsIngest'
)

JOURNAL_CMS = JournalCms(
    SETTINGS['journal_cms_host'],
    SETTINGS['journal_cms_user'],
    SETTINGS['journal_cms_password']
)

JOURNAL = Journal(
    SETTINGS['journal_host'],
)
