import re
import datetime
import logging
from ssl import SSLError
from bs4 import BeautifulSoup

import polling
import requests
from requests.exceptions import ConnectionError
from spectrum import aws

# TODO: install proper SSL certificate on elife-dashboard-develop--end2end to avoid this
requests.packages.urllib3.disable_warnings()

GLOBAL_TIMEOUT = 300
LOGGER = logging.getLogger(__name__)

class TimeoutException(RuntimeError):
    @staticmethod
    def giving_up_on(what):
        timestamp = datetime.datetime.today().isoformat()
        return TimeoutException(
            "Cannot find '%s'; Giving up at %s" \
                    % (what, timestamp)
        )

class UnrecoverableException(RuntimeError):
    def __init__(self, response):
        super(UnrecoverableException, self).__init__(self, response)
        self._response = response

    def __str__(self):
        return "RESPONSE CODE: %d\nRESPONSE BODY:\n%s\n" \
                % (self._response.status_code, self._response.text)


class BucketFileCheck:
    def __init__(self, s3, bucket_name, key):
        self._s3 = s3
        self._bucket_name = bucket_name
        self._key = key

    def of(self, **kwargs):
        criteria = self._key.format(**kwargs)
        try:
            return polling.poll(
                lambda: self._is_present(criteria, kwargs['id']),
                timeout=GLOBAL_TIMEOUT,
                step=5
            )
        except polling.TimeoutException:
            raise TimeoutException.giving_up_on(
                "object matching criteria %s in bucket %s" \
                    % (criteria, self._bucket_name)
            )

    def _is_present(self, criteria, id):
        try:
            bucket = self._s3.Bucket(self._bucket_name)
            bucket.load()
            for file in bucket.objects.all():
                match = re.match(criteria, file.key)
                if match:
                    LOGGER.info(
                        "Found %s in bucket %s",
                        file.key,
                        self._bucket_name,
                        extra={'id': id}
                    )
                    if match.groups():
                        LOGGER.info(
                            "Found groups %s in matching the file name %s",
                            match.groupdict(),
                            file.key,
                            extra={'id': id}
                        )
                        return match.groups()
                    else:
                        return True
        except SSLError as e:
            _log_connection_error(e)
        return False

class WebsiteArticleCheck:
    def __init__(self, host, user, password):
        self._host = host
        self._user = user
        self._password = password

    def unpublished(self, id, version=1):
        return self._wait_for_status(id, version, publish=False)

    def published(self, id, version=1):
        return self._wait_for_status(id, version, publish=True)

    def _wait_for_status(self, id, version, publish):
        try:
            article = polling.poll(
                lambda: self._is_present(id, version, publish),
                timeout=GLOBAL_TIMEOUT,
                step=5
            )
            assert article['article-id'] == id, \
                    "The article id does not correspond to the one we were looking for"
            return article
        except polling.TimeoutException:
            raise TimeoutException.giving_up_on(
                "article on website with publish status %s: %s/api/article/%s.%s.json" \
                    % (publish, self._host, id, version)
            )

    def visible(self, path, **kwargs):
        try:
            article = polling.poll(
                lambda: self._is_visible(path, extra=kwargs),
                timeout=GLOBAL_TIMEOUT,
                step=5
            )
            return article
        except polling.TimeoutException:
            raise TimeoutException.giving_up_on(
                "article visible on website: %s%s" \
                    % (self._host, path)
            )

    def _is_present(self, id, version, publish):
        template = "%s/api/article/%s.%s.json"
        url = template % (self._host, id, version)
        try:
            response = requests.get(url, auth=(self._user, self._password))
            if response.status_code == 200:
                article = response.json()
                if article['publish'] is publish:
                    LOGGER.info(
                        "Found %s on website with publish status %s",
                        url,
                        publish,
                        extra={'id': id}
                    )
                    return article
        except ConnectionError as e:
            _log_connection_error(e)
        return False

    def _is_visible(self, path, extra=None):
        extra = {} if extra is None else extra
        template = "%s/%s"
        url = template % (self._host, path)
        try:
            response = requests.get(url)
            if response.status_code >= 500:
                raise UnrecoverableException(response)
            if response.status_code == 200:
                LOGGER.info("Found %s visible on website", url, extra=extra)
                return True
        except ConnectionError as e:
            _log_connection_error(e)
        return False

class DashboardArticleCheck:
    def __init__(self, host, user, password):
        self._host = host
        self._user = user
        self._password = password

    def ready_to_publish(self, id, version):
        return self._wait_for_status(id, version, "ready to publish")

    def published(self, id, version):
        return self._wait_for_status(id, version, "published")

    def publication_in_progress(self, id, version):
        return self._wait_for_status(id, version, "publication in progress")

    def error(self, id, version, run=1):
        try:
            error = polling.poll(
                lambda: self._is_last_event_error(id, version, run),
                timeout=GLOBAL_TIMEOUT,
                step=5
            )
            return error
        except polling.TimeoutException:
            raise TimeoutException.giving_up_on(
                "having the last event as an error on the article version %s on dashboard: %s/api/article/%s" \
                    % (version, self._host, id)
            )

    def _wait_for_status(self, id, version, status):
        try:
            article = polling.poll(
                lambda: self._is_present(id, version, status),
                timeout=GLOBAL_TIMEOUT,
                step=5
            )
            return article
        except polling.TimeoutException:
            raise TimeoutException.giving_up_on(
                "article version %s in status %s on dashboard: %s/api/article/%s" \
                    % (version, status, self._host, id)
            )

    def _is_present(self, id, version, status):
        template = "%s/api/article/%s"
        url = template % (self._host, id)
        version_key = str(version)
        try:
            response = requests.get(url, auth=(self._user, self._password), verify=False)
            if response.status_code != 200:
                return False
            if response.status_code >= 500:
                raise UnrecoverableException(response)
            article = response.json()
            if 'versions' not in article:
                return False
            if version_key not in article['versions']:
                return False
            version_details = article['versions'][version_key]['details']
            if version_details['publication-status'] != status:
                return False
            LOGGER.info(
                "Found %s version %s in status %s on dashboard",
                url,
                version_key,
                status,
                extra={'id': id}
            )
            return article
        except ConnectionError as e:
            _log_connection_error(e)
            return False

    def _is_last_event_error(self, id, version, run):
        template = "%s/api/article/%s"
        url = template % (self._host, id)
        version_key = str(version)
        try:
            response = requests.get(url, auth=(self._user, self._password), verify=False)
            if response.status_code >= 500:
                raise UnrecoverableException(response)
            article = response.json()
            version_runs = article['versions'][version_key]['runs']
            run_key = str(run)
            if not run_key in version_runs:
                return False
            run_details = version_runs[run_key]
            events = run_details['events']
            last_event = events[-1]
            LOGGER.info(
                "Found last event of %s version %s run %s on dashboard: %s",
                url,
                version_key,
                run_key,
                last_event,
                extra={'id': id}
            )
            if last_event['event-status'] == 'error':
                return last_event
            return False
        except ConnectionError as e:
            _log_connection_error(e)
            return False


class LaxArticleCheck:
    def __init__(self, host):
        self._host = host

    def published(self, id, version):
        try:
            article = polling.poll(
                lambda: self._is_present(id, version),
                # TODO: duplication of polling configuration
                timeout=GLOBAL_TIMEOUT,
                step=5
            )
            return article
        except polling.TimeoutException:
            raise TimeoutException.giving_up_on(
                "article version %s in lax: %s/api/v1/article/10.7554/eLife.%s/version" \
                    % (version, self._host, id)
            )

    def _is_present(self, id, version):
        template = "%s/api/v1/article/10.7554/eLife.%s/version"
        url = template % (self._host, id)
        version_key = str(version)
        # TODO: remove verify=False
        try:
            response = requests.get(url, verify=False)
            if response.status_code != 200:
                return False
            if response.status_code >= 500:
                raise UnrecoverableException(response)
            article_versions = response.json()
            if version_key not in article_versions:
                return False
            LOGGER.info("Found article version %s in lax: %s", version_key, url, extra={'id': id})
            return article_versions[version_key]
        except ConnectionError as e:
            _log_connection_error(e)
            return False

class ApiCheck:
    def __init__(self, host):
        self._host = host

    def labs_experiments(self):
        body = self._list_api('/labs-experiments', 'labs-experiment')
        self._ensure_list_has_at_least_1_element(body)

    def subjects(self):
        body = self._list_api('/subjects', 'subject')
        self._ensure_list_has_at_least_1_element(body)

    def podcast_episodes(self):
        self._list_api('/podcast-episodes', 'podcast-episode')

    def people(self):
        self._list_api('/people', 'person')

    def medium_articles(self):
        self._list_api('/medium-articles', 'medium-article')

    def blog_articles(self):
        self._list_api('/blog-articles', 'blog-article')

    def events(self):
        self._list_api('/events', 'event')

    def interviews(self):
        self._list_api('/interviews', 'interview')

    def collections(self):
        self._list_api('/collections', 'collection')

    def _list_api(self, path, entity):
        url = "%s%s" % (self._host, path)
        response = requests.get(url, headers={'Accept': 'application/vnd.elife.%s-list+json' % entity})
        body = self._ensure_sane_response(response, url)
        return body

    def article(self, id, version=1):
        versioned_url = "%s/articles/%s/versions/%s" % (self._host, id, version)
        # we should pass 'Accept': 'application/vnd.elife.article-poa+json,application/vnd.elife.article-vor+json'
        # if that works... requests does not support a multidict, it seems
        response = requests.get(versioned_url, headers={})
        body = self._ensure_sane_response(response, versioned_url)
        assert body['version'] == version, \
            ("Version in body %s not consistent with requested version %s" % (body['version'], version))
        LOGGER.info("Found article version %s on api: %s", body['version'], versioned_url, extra={'id': id})

        latest_url = "%s/articles/%s" % (self._host, id)
        response = requests.get(latest_url, headers={})
        body = self._ensure_sane_response(response, latest_url)
        assert body['version'] == version, \
            ("We were expecting /article/%s to be at version %s now" % (id, version))
        LOGGER.info("Found article version %s on api: %s", version, latest_url, extra={'id': id})
        return body

    def search(self, for_input):
        url = "%s/search?for=%s" % (self._host, for_input)
        response = requests.get(url)
        return self._ensure_sane_response(response, url)

    def _ensure_sane_response(self, response, url):
        assert response.status_code is 200, \
            "Response from %s had status %d, body %s" % (url, response.status_code, response.content)
        try:
            return response.json()
        except ValueError:
            raise ValueError("Response from %s is not JSON: %s" % (url, response.content))

    def _ensure_list_has_at_least_1_element(self, body):
        assert body['total'] >= 1, \
                ("We were expecting the body of the list to have some content, but the total is not >= 1: %s" % body)

class JournalCheck:
    def __init__(self, host):
        self._host = host

    def article(self, id, volume=5):
        url = "%s/content/%s/e%s" % (self._host, volume, id)
        LOGGER.info("Loading %s", url)
        response = requests.get(url)
        _assert_status_code(response, 200, url)
        #_assert_all_resources_of_page_load(response.content, self._host)
        if False:
            url = "%s/content/%s/e%s/figures" % (self._host, volume, id)
            LOGGER.info("Loading %s", url)
            response = requests.get(url)
            _assert_status_code(response, 200, url)
            #_assert_all_resources_of_page_load(response.content, self._host)

class GithubCheck:
    def __init__(self, repo_url):
        "repo_url must have a {path} placeholder in it that will be substituted with the file path"
        self._repo_url = repo_url

    def article(self, id, version=1):
        url = self._repo_url.format(path=('/articles/elife-%s-v%s.xml' % (id, version)))
        try:
            polling.poll(
                lambda: self._is_present(url),
                timeout=GLOBAL_TIMEOUT,
                step=5
            )
        except polling.TimeoutException:
            raise TimeoutException.giving_up_on("article on github with URL %s" % url)

    def _is_present(self, url):
        try:
            response = requests.get(url)
            if response.status_code == 200:
                LOGGER.info("HEAD on %s with status 200", url)
                return True
        except ConnectionError as e:
            _log_connection_error(e)
        return False

def _log_connection_error(e):
    LOGGER.debug("Connection error, will retry: %s", e)

def _assert_status_code(response, expected_status_code, url):
    assert response.status_code == expected_status_code, \
        "Response from %s had status %d, body %s" % (url, response.status_code, response.content)

def _assert_all_resources_of_page_load(html_content, host):
    soup = BeautifulSoup(html_content, "html.parser")
    resources = []
    for img in soup.find_all("img"):
        resources.append(img.get("src"))
    for script in soup.find_all("script"):
        if script.get("src"):
            resources.append(script.get("src"))
    for link in soup.find_all("link"):
        resources.append(link.get("href"))
    for video in soup.find_all("video"):
        resources.append(video.get("poster"))
    for media_source in soup.find_all("source"):
        resources.append(media_source.get("src"))
    # <srcset sources="/assets/img/patterns/molecules/nav-primary-menu-ic_2x.png?v1 48w, /assets/img/patterns/molecules/nav-primary-menu-ic_1x.png?v1 24w">
    for srcset in soup.find_all("srcset"):
        for source in [s.strip() for s in srcset.get("sources").split(",")]:
            (path, _) = source.split(" ")
            resources.append(path)
    for path in resources:
        url = _build_url(path, host)
        LOGGER.info("Loading %s", url)
        # there are no caches involved with this headless client
        _assert_status_code(requests.head(url), 200, url)

def _build_url(path, host):
    if path.startswith("http://") or path.startswith("https://"):
        return path
    assert path.startswith("/"), ("I found a non-absolute path %s and I don't know how to load it" % path)
    return "%s%s" % (host, path)

EIF = BucketFileCheck(
    aws.S3,
    aws.SETTINGS.bucket_eif,
    '{id}.{version}/(?P<run>.*)/elife-{id}-v{version}.json'
)
ARCHIVE = BucketFileCheck(
    aws.S3,
    aws.SETTINGS.bucket_archive,
    # notice {{6}} is the escaping for {6} in the regex,
    # it should not be substituted
    'elife-{id}-(poa|vor)-v{version}-20[0-9]{{12}}.zip'
)
WEBSITE = WebsiteArticleCheck(
    host=aws.SETTINGS.website_host,
    user=aws.SETTINGS.website_user,
    password=aws.SETTINGS.website_password
)
IMAGES = BucketFileCheck(
    aws.S3,
    aws.SETTINGS.bucket_cdn,
    '{id}/elife-{id}-{figure_name}-v{version}.jpg'
)
PDF = BucketFileCheck(
    aws.S3,
    aws.SETTINGS.bucket_cdn,
    '{id}/elife-{id}-v{version}.pdf'
)
DASHBOARD = DashboardArticleCheck(
    host=aws.SETTINGS.dashboard_host,
    user=aws.SETTINGS.dashboard_user,
    password=aws.SETTINGS.dashboard_password
)
LAX = LaxArticleCheck(
    host=aws.SETTINGS.lax_host
)
API = ApiCheck(
    host=aws.SETTINGS.api_gateway_host
)
JOURNAL = JournalCheck(
    host=aws.SETTINGS.journal_host
)
GITHUB_XML = GithubCheck(
    repo_url=aws.SETTINGS.github_article_xml_repository_url
)
