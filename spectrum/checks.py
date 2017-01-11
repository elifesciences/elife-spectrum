import datetime
from pprint import pformat
import re
from ssl import SSLError

from bs4 import BeautifulSoup

import polling
import requests
from requests.exceptions import ConnectionError
from spectrum import aws, logger


# TODO: install proper SSL certificate on elife-dashboard-develop--end2end to avoid this
requests.packages.urllib3.disable_warnings()

GLOBAL_TIMEOUT = 300
LOGGER = logger.logger(__name__)

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
    def __init__(self, s3, bucket_name, key, prefix=None):
        self._s3 = s3
        self._bucket_name = bucket_name
        self._key = key
        self._prefix = prefix

    def of(self, last_modified_after=None, **kwargs):
        criteria = self._key.format(**kwargs)
        last_modified_suffix = (" and being last_modified after %s" % last_modified_after) if last_modified_after else ""
        return _poll(
            lambda: self._is_present(criteria, last_modified_after, **kwargs),
            "object matching criteria %s in bucket %s"+last_modified_suffix,
            criteria, self._bucket_name
        )

    def _is_present(self, criteria, last_modified_after, **kwargs):
        try:
            id = kwargs['id']
            bucket = self._s3.Bucket(self._bucket_name)
            # TODO: necessary?
            bucket.load()
            all = bucket.objects.all()
            if self._prefix:
                prefix = self._prefix.format(**kwargs)
                all = all.filter(Prefix=prefix)
                LOGGER.debug(
                    "Filtering by prefix %s",
                    prefix,
                    extra={'id': id}
                )
            for file in all:
                match = re.match(criteria, file.key)
                if match:
                    LOGGER.debug(
                        "Found candidate %s in bucket %s (last modified: %s)",
                        file.key,
                        self._bucket_name,
                        file.last_modified,
                        extra={'id': id}
                    )
                    if last_modified_after:
                        if file.last_modified.strftime('%s') <= last_modified_after.strftime('%s'):
                            continue
                    LOGGER.info(
                        "Found %s in bucket %s (last modified: %s)",
                        file.key,
                        self._bucket_name,
                        file.last_modified,
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
        #try:
        #    text_file = StringIO.StringIO()
        #    LOGGER.debug(
        #        "Downloading %s/%s",
        #        self._bucket_name,
        #        file.key,
        #        extra={'id': id}
        #    )
        #    bucket.download_fileobj(file.key, text_file)
        #    if text_match not in text_file.getvalue():
        #        LOGGER.info(
        #            "%s/%s does not match `%s`",
        #            self._bucket_name,
        #            file.key,
        #            text_match,
        #            extra={'id': id}
        #        )
        #        return False
        #finally:
        #    text_file.close()

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
        article = _poll(
            lambda: self._is_present(id, version, publish),
            "article on website with publish status %s: %s/api/article/%s.%s.json",
            publish, self._host, id, version
        )
        assert article['article-id'] == id, \
                "The article id does not correspond to the one we were looking for"
        return article

    def visible(self, path, **kwargs):
        article = _poll(
            lambda: self._is_visible(path, extra=kwargs),
            "article visible on website: %s%s",
            self._host, path
        )
        return article

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

    def ready_to_publish(self, id, version, run=None):
        return self._wait_for_status(id, version, run=run, status="ready to publish")

    def published(self, id, version, run=None):
        return self._wait_for_status(id, version, run=run, status="published")

    def publication_in_progress(self, id, version, run=None):
        return self._wait_for_status(id, version, run=run, status="publication in progress")

    def error(self, id, version, run=1):
        return _poll(
            lambda: self._is_last_event_error(id, version, run),
            "having the last event as an error on the article version %s on dashboard: %s/api/article/%s",
            version, self._host, id
        )

    def _wait_for_status(self, id, version, run, status):
        return _poll(
            lambda: self._is_present(id, version, run, status),
            "article version %s in status %s on dashboard: %s/api/article/%s",
            version, status, self._host, id
        )

    def _is_present(self, id, version, run, status):
        url = self._article_api(id)
        try:
            response = requests.get(url, auth=(self._user, self._password), verify=False)
            if response.status_code != 200:
                return False
            if response.status_code >= 500:
                raise UnrecoverableException(response)
            article = response.json()
            version_contents = self._check_for_version(article, version)
            if not version:
                return False
            if version_contents['details']['publication-status'] != status:
                return False
            run_suffix = ''
            if run:
                run_contents = self._check_for_run(version_contents, run)
                if not run_contents:
                    return False
                run_suffix = " with run %s" % run
            LOGGER.info(
                "Found %s version %s in status %s on dashboard" + run_suffix,
                url,
                version,
                status,
                extra={'id': id}
            )
            return article
        except ConnectionError as e:
            _log_connection_error(e)
            return False

    def _check_for_version(self, article, version):
        version_key = str(version)
        if 'versions' not in article:
            return False
        if version_key not in article['versions']:
            return False
        return article['versions'][version_key]

    def _check_for_run(self, version_contents, run):
        matching_runs = [r for _, r in version_contents['runs'].iteritems() if r['run-id'] == run]
        if len(matching_runs) > 1:
            raise RuntimeError("Too many runs matching run-id %s: %s", run, matching_runs)
        if len(matching_runs) == 0:
            return False
        return matching_runs[0]

    def _is_last_event_error(self, id, version, run):
        url = self._article_api(id)
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

    def _article_api(self, id):
        template = "%s/api/article/%s"
        return template % (self._host, id)

class LaxArticleCheck:
    def __init__(self, host):
        self._host = host

    def published(self, id, version):
        return _poll(
            lambda: self._is_present(id, version),
            "article version %s in lax: %s/api/v1/article/10.7554/eLife.%s/version",
            version, self._host, id
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

    def wait_article(self, id, **constraints):
        "Article must be immediately present with this version, but will poll until the constraints (fields with certain values) are satisfied"
        latest_url = "%s/articles/%s" % (self._host, id)
        def _is_ready():
            response = requests.get(latest_url, headers={})
            if response.status_code == 404:
                LOGGER.debug("%s: 404", latest_url)
                return False
            body = self._ensure_sane_response(response, latest_url)
            for field, value in constraints.iteritems():
                if body[field] != value:
                    LOGGER.debug("%s: field `%s` is not `%s` but `%s`",
                                 latest_url, field, value, body[field])
                    return False
            LOGGER.info("%s: conforming to constraints %s",
                        latest_url, constraints)
            return body
        return _poll(
            _is_ready,
            "%s to satisfy constraints %s",
            latest_url, constraints
        )

    def search(self, for_input):
        url = "%s/search?for=%s" % (self._host, for_input)
        response = requests.get(url)
        return self._ensure_sane_response(response, url)

    def wait_search(self, word):
        "Returns as soon as there is one result"
        search_url = "%s/search?for=%s" % (self._host, word)
        def _is_ready():
            response = requests.get(search_url, headers={})
            body = self._ensure_sane_response(response, search_url)
            if len(body['items']) == 0:
                return False
            LOGGER.info("%s: returning %d results",
                        search_url,
                        len(body['items']))
            return body
        return _poll(
            _is_ready,
            "%s returning at least 1 result",
            search_url
        )

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

    def article(self, id, volume, has_figures):
        url = _build_url("/content/%s/e%s" % (volume, id), self._host)
        LOGGER.info("Loading %s", url)
        response = requests.get(url)
        _assert_status_code(response, 200, url)
        _assert_all_resources_of_page_load(response.content, self._host)
        figures_link_selector = 'view-selector__link--figures'
        figures_link = self._link(response.content, figures_link_selector)
        if has_figures:
            assert figures_link is not None, "Cannot find figures link with selector %s" % figures_link_selector
            figures_url = _build_url(figures_link, self._host)
            LOGGER.info("Loading %s", figures_url)
            response = requests.get(figures_url)
            _assert_status_code(response, 200, figures_url)
            _assert_all_resources_of_page_load(response.content, self._host)
        return response.content
        #TODO figures page will also be present if article has any tables, data sets or additional files
        #else:
        #    assert figures_link is None, "Found a figure link %s but it should not be there as the article has no figures" % figures_link

    def homepage(self):
        url = _build_url("/", self._host)
        LOGGER.info("Loading %s", url)
        response = requests.get(url)
        _assert_status_code(response, 200, url)

    def _link(self, body, class_name):
        """Finds out where the link selected with CSS class_name points to.

        May return None if there is no actual link with this class on the page"""
        soup = BeautifulSoup(body, "html.parser")
        links = soup.find_all("a", class_=class_name)
        assert len(links) <= 1, \
               ("Found too many links for the class name %s: %s" % (class_name, links))
        return links[0]['href'] if len(links) == 1 else None


class GithubCheck:
    def __init__(self, repo_url):
        "repo_url must have a {path} placeholder in it that will be substituted with the file path"
        self._repo_url = repo_url

    def article(self, id, version=1, text_match=None):
        url = self._repo_url.format(path=('/articles/elife-%s-v%s.xml' % (id, version)))
        error_message_suffix = (" and matching %s" % text_match) if text_match else ""
        _poll(
            lambda: self._is_present(url, text_match, id),
            "article on github with URL %s existing" + error_message_suffix,
            url
        )

    def _is_present(self, url, text_match, id):
        try:
            response = requests.get(url)
            if response.status_code == 200:
                if text_match:
                    if text_match in response.content:
                        LOGGER.info("Body of %s matches %s", url, text_match, extra={'id': id})
                        return True
                else:
                    LOGGER.info("GET on %s with status 200", url, extra={'id': id})
                    return True
            return False
        except ConnectionError as e:
            _log_connection_error(e)
        return False

def _poll(action_fn, error_message, *error_message_args):
    try:
        return polling.poll(
            action_fn,
            timeout=GLOBAL_TIMEOUT,
            step=5
        )
    except polling.TimeoutException:
        raise TimeoutException.giving_up_on(error_message % tuple(error_message_args))

def _log_connection_error(e):
    LOGGER.debug("Connection error, will retry: %s", e)

def _assert_status_code(response, expected_status_code, url):
    assert response.status_code == expected_status_code, \
        "Response from %s had status %d, body %s" % (url, response.status_code, response.content)

RESOURCE_CACHE = {}

def _assert_all_resources_of_page_load(html_content, host):
    """Checks that all <script>, <link>, <video>, <source>, <srcset> load, by issuing HEAD requests that must give 200 OK.

    Returns the BeautifulSoup for reuse"""
    def _srcset_values(srcset):
        values = []
        for candidate_string in [s.strip() for s in srcset.split(",")]:
            url_and_maybe_descriptors = candidate_string.split(" ")
            values.append(url_and_maybe_descriptors[0])
            return values
    def _resources_from(soup):
        resources = []
        for img in soup.find_all("img"):
            resources.append(img.get("src"))
            srcset = img.get("srcset")
            if srcset:
                resources.extend(_srcset_values(srcset))
        for script in soup.find_all("script"):
            if script.get("src"):
                resources.append(script.get("src"))
        for link in soup.find_all("link"):
            resources.append(link.get("href"))
        for video in soup.find_all("video"):
            resources.append(video.get("poster"))
        for media_source in soup.find_all("source"):
            srcset = media_source.get("srcset")
            if srcset:
                resources.extend(_srcset_values(srcset))
        return resources
    soup = BeautifulSoup(html_content, "html.parser")
    resources = _resources_from(soup)
    LOGGER.info("Found resources %s", pformat(resources))
    for path in resources:
        if path is None:
            continue
        url = _build_url(path, host)
        if url in RESOURCE_CACHE:
            LOGGER.info("Cached %s: %s", url, RESOURCE_CACHE[url])
        else:
            LOGGER.info("Loading %s", url)
            response = requests.head(url)
            _assert_status_code(response, 200, url)
            RESOURCE_CACHE[url] = response.status_code
    return soup

def _build_url(path, host):
    if path.startswith("http://") or path.startswith("https://"):
        return path
    assert path.startswith("/"), ("I found a non-absolute path %s and I don't know how to load it" % path)
    return "%s%s" % (host, path)

EIF = BucketFileCheck(
    aws.S3,
    aws.SETTINGS.bucket_eif,
    '{id}.{version}/(?P<run>.*)/elife-{id}-v{version}.json',
    '{id}.{version}/'
)
ARCHIVE = BucketFileCheck(
    aws.S3,
    aws.SETTINGS.bucket_archive,
    # notice {{6}} is the escaping for {6} in the regex,
    # it should not be substituted
    'elife-{id}-(poa|vor)-v{version}-20[0-9]{{12}}.zip',
    'elife-{id}-'
)
WEBSITE = WebsiteArticleCheck(
    host=aws.SETTINGS.website_host,
    user=aws.SETTINGS.website_user,
    password=aws.SETTINGS.website_password
)
IMAGES_BOT_CDN = BucketFileCheck(
    aws.S3,
    aws.SETTINGS.bucket_cdn,
    '{id}/elife-{id}-{figure_name}-v{version}.jpg',
    '{id}/elife-{id}-{figure_name}-v{version}.jpg'
)
IMAGES_PUBLISHED_CDN = BucketFileCheck(
    aws.S3,
    aws.SETTINGS.bucket_published,
    'articles/{id}/elife-{id}-{figure_name}-v{version}.jpg',
    'articles/{id}/elife-{id}-{figure_name}-v{version}.jpg'
)
XML_PUBLISHED_CDN = BucketFileCheck(
    aws.S3,
    aws.SETTINGS.bucket_published,
    'articles/{id}/elife-{id}-v{version}.xml',
    'articles/{id}/elife-{id}-v{version}.xml'
)
XML_DOWNLOAD_PUBLISHED_CDN = BucketFileCheck(
    aws.S3,
    aws.SETTINGS.bucket_published,
    'articles/{id}/elife-{id}-v{version}-download.xml',
    'articles/{id}/elife-{id}-v{version}-download.xml'
)
PDF_BOT_CDN = BucketFileCheck(
    aws.S3,
    aws.SETTINGS.bucket_cdn,
    '{id}/elife-{id}-v{version}.pdf',
    '{id}/elife-{id}-v{version}.pdf'
)
PDF_PUBLISHED_CDN = BucketFileCheck(
    aws.S3,
    aws.SETTINGS.bucket_published,
    'articles/{id}/elife-{id}-v{version}.pdf',
    'articles/{id}/elife-{id}-v{version}.pdf'
)
PDF_DOWNLOAD_PUBLISHED_CDN = BucketFileCheck(
    aws.S3,
    aws.SETTINGS.bucket_published,
    'articles/{id}/elife-{id}-v{version}-download.pdf',
    'articles/{id}/elife-{id}-v{version}-download.pdf'
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
