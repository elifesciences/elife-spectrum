from os import path
import random
import string
import requests
from spectrum import aws, logger
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
        self._browser = mechanicalsoup.Browser()

    def login(self):
        login_url = "%s/user/login" % self._host
        login_page = self._browser.get(login_url)
        form = login_page.soup.form
        form.find("input", {"name": "name"})['value'] = self._user
        form.find("input", {"name": "pass"})['value'] = self._password
        response = self._browser.submit(form, login_page.url)
        #<h1 class="js-quickedit-page-title title page-title">alfred</h1>
        title = response.soup.find("h1", {"class" : "page-title"})
        assert title.text == self._user

    def create_blog_article(self, title, text):
        create_url = "%s/node/add/blog_article" % self._host
        create_page = self._browser.get(create_url)
        form = create_page.soup.form
        form.find("input", {"name": "title[0][value]"})['value'] = title
        add_paragraph = form.find("input", {"name":"field_content_paragraph_add_more"})
        print add_paragraph
        print form
        wrapped_form = mechanicalsoup.Form(form)
        wrapped_form.choose_submit(add_paragraph)
        response = self._browser.submit(form, create_page.url, data={'field_content_paragraph_add_more': 'Add Paragraph'})
        #form.find("input", {"name": "title[0][value]"})['value'] = title
        #print response.content
        form = response.soup.form
        form.find('textarea', {"name": "field_content[0][subform][field_block_html][0][value]"}).insert(0, text)
        response = self._browser.submit(form, create_page.url, data={'op': 'Save and publish'})
        print response
        #check https://end2end--journal-cms.elifesciences.org/admin/content?status=All&type=All&title=b9djvu04y6v1t4kug4ts8kct5pagf8&langcode=All
        # but in checks module

def invented_word():
    return ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(30))

PRODUCTION_BUCKET = InputBucket(aws.S3, aws.SETTINGS.bucket_input)
SILENT_CORRECTION_BUCKET = InputBucket(aws.S3, aws.SETTINGS.bucket_silent_corrections)
DASHBOARD = Dashboard(
    aws.SETTINGS.dashboard_host,
    aws.SETTINGS.dashboard_user,
    aws.SETTINGS.dashboard_password
)

SILENT_CORRECTION = SilentCorrectionWorkflowStarter(
    aws.SETTINGS.aws_access_key_id,
    aws.SETTINGS.aws_secret_access_key,
    aws.SETTINGS.region_name,
    SILENT_CORRECTION_BUCKET.name(),
    aws.SETTINGS.queue_workflow_starter,
    'SilentCorrectionsIngest'
)

JOURNAL_CMS = JournalCms(
    aws.SETTINGS.journal_cms_host,
    aws.SETTINGS.journal_cms_user,
    aws.SETTINGS.journal_cms_password
)
