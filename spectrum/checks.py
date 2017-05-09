from datetime import datetime
from pprint import pformat
import os
import re
from ssl import SSLError

from bs4 import BeautifulSoup
import polling
import requests
from requests.exceptions import ConnectionError
from concurrent.futures import ThreadPoolExecutor, wait
from requests_futures.sessions import FuturesSession
from spectrum import aws, logger
from spectrum.config import SETTINGS


# TODO: install proper SSL certificate on elife-dashboard-develop--end2end to avoid this
requests.packages.urllib3.disable_warnings()


GLOBAL_TIMEOUT = int(os.environ['SPECTRUM_TIMEOUT']) if 'SPECTRUM_TIMEOUT' in os.environ else 600
HTTP_TIMEOUT = 30
LOGGER = logger.logger(__name__)

class TimeoutError(RuntimeError):
    @staticmethod
    def giving_up_on(what):
        timestamp = datetime.today().isoformat()
        return TimeoutError(
            "Cannot find '%s'; Giving up at %s" \
                    % (what, timestamp)
        )

class UnrecoverableError(RuntimeError):
    def __init__(self, details):
        super(UnrecoverableError, self).__init__(self, details)
        self._details = details

    def __str__(self):
        if isinstance(self._details, requests.Response):
            return "RESPONSE CODE: %d\nRESPONSE BODY:\n%s\n" \
                    % (self._details.status_code, self._details.text)
        else:
            return "DETAILS: %s" % pformat(self._details)


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
                        return (match.groups(), {'key': file.key})
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
                raise UnrecoverableError(response)
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

    def ready_to_publish(self, id, version, run=None, run_after=None):
        return self._wait_for_status(id, version, run=run, status="ready to publish", run_after=run_after)

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

    def _wait_for_status(self, id, version, status, run=None, run_after=None):
        return _poll(
            lambda: self._is_present(id, version, status, run=run, run_after=run_after),
            lambda: "article version %s in status %s on dashboard (run filter %s, run_after filter %s): %s/api/article/%s",
            version,
            status,
            run,
            run_after,
            self._host,
            id
        )

    def _is_present(self, id, version, status, run=None, run_after=None):
        url = self._article_api(id)
        try:
            response = requests.get(url, auth=(self._user, self._password), verify=False)
            if response.status_code != 200:
                return False, "Response code: %s" % response.status_code
            if response.status_code >= 500:
                raise UnrecoverableError(response)
            article = response.json()
            version_contents = self._check_for_version(article, version)
            if not version_contents:
                return False, article
            if version_contents['details']['publication-status'] != status:
                return False, version_contents
            if run or run_after:
                if run:
                    run_contents = self._check_for_run(version_contents, run)
                elif run_after:
                    run_contents = self._check_for_run_after(version_contents, run_after)
            else:
                run_contents = self._check_for_run(version_contents)
            if not run_contents:
                return False, version_contents['runs']
            self._check_correctness(run_contents)
            LOGGER.info(
                "Found %s version %s in status %s on dashboard with run %s",
                url,
                version,
                status,
                run_contents['run-id'],
                extra={'id': id}
            )
            return article
        except ConnectionError as e:
            _log_connection_error(e)
            return False, e

    def _check_for_version(self, article, version):
        version_key = str(version)
        if 'versions' not in article:
            return False
        if version_key not in article['versions']:
            return False
        return article['versions'][version_key]

    def _check_for_run(self, version_contents, run=None):
        if run:
            matching_runs = [r for _, r in version_contents['runs'].iteritems() if r['run-id'] == run]
        else:
            matching_runs = version_contents['runs'].values()
        if len(matching_runs) > 1:
            raise RuntimeError("Too many runs matching run-id %s: %s", run, pformat(matching_runs))
        if len(matching_runs) == 0:
            return False
        return matching_runs[0]

    def _check_for_run_after(self, version_contents, run_after):
        matching_runs = [r for _, r in version_contents['runs'].iteritems() if datetime.fromtimestamp(r['first-event-timestamp']).strftime('%s') > run_after.strftime('%s')]
        if len(matching_runs) > 1:
            raise RuntimeError("Too many runs after run_after %s: %s", run_after, matching_runs)
        if len(matching_runs) == 0:
            return False
        return matching_runs[0]

    def _check_correctness(self, run_contents):
        errors = [e for e in run_contents['events'] if e['event-status'] == 'error']
        if errors:
            raise UnrecoverableError("At least one error event was reported for the run.\n%s" % pformat(errors))

    def _is_last_event_error(self, id, version, run):
        url = self._article_api(id)
        version_key = str(version)
        try:
            response = requests.get(url, auth=(self._user, self._password), verify=False)
            if response.status_code >= 500:
                raise UnrecoverableError(response)
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
                raise UnrecoverableError(response)
            article_versions = response.json()
            if version_key not in article_versions:
                return False
            LOGGER.info("Found article version %s in lax: %s", version_key, url, extra={'id': id})
            return article_versions[version_key]
        except ConnectionError as e:
            _log_connection_error(e)
            return False

class ApiCheck:
    def __init__(self, host, authorization=None):
        self._host = host
        self._authorization = authorization

    def labs_experiments(self):
        #body =
        self._list_api('/labs-experiments', 'labs-experiment')
        #self._ensure_list_has_at_least_1_element(body)

    def subjects(self):
        #body =
        self._list_api('/subjects', 'subject')
        #self._ensure_list_has_at_least_1_element(body)

    def podcast_episodes(self):
        self._list_api('/podcast-episodes', 'podcast-episode')

    def people(self):
        self._list_api('/people', 'person')

    def medium_articles(self):
        self._list_api('/medium-articles', 'medium-article')

    def blog_articles(self):
        self._list_api('/blog-articles', 'blog-article')

    def blog_article(self, id):
        return self._item_api('/blog-articles/%s' % id, 'blog-article')

    def events(self):
        self._list_api('/events', 'event')

    def interviews(self):
        self._list_api('/interviews', 'interview')

    def collections(self):
        self._list_api('/collections', 'collection')

    def _list_api(self, path, entity):
        url = "%s%s" % (self._host, path)
        response = requests.get(url, headers=self._base_headers({'Accept': 'application/vnd.elife.%s-list+json; version=1' % entity}))
        LOGGER.info("Found %s: %s", url, response.status_code)
        return self._ensure_sane_response(response, url)

    def _item_api(self, path, entity):
        url = "%s%s" % (self._host, path)
        response = requests.get(url, headers=self._base_headers({'Accept': 'application/vnd.elife.%s+json; version=1' % entity}))
        LOGGER.info("Found %s: %s", url, response.status_code)
        return self._ensure_sane_response(response, url)

    def article(self, id, version=1):
        versioned_url = "%s/articles/%s/versions/%s" % (self._host, id, version)
        # we should pass 'Accept': 'application/vnd.elife.article-poa+json,application/vnd.elife.article-vor+json'
        # if that works... requests does not support a multidict, it seems
        response = requests.get(versioned_url, headers=self._base_headers())
        body = self._ensure_sane_response(response, versioned_url)
        assert body['version'] == version, \
            ("Version in body %s not consistent with requested version %s" % (body['version'], version))
        LOGGER.info("Found article version %s on api: %s", body['version'], versioned_url, extra={'id': id})

        latest_url = "%s/articles/%s" % (self._host, id)
        response = requests.get(latest_url, headers=self._base_headers())
        body = self._ensure_sane_response(response, latest_url)
        assert body['version'] == version, \
            ("We were expecting /article/%s to be at version %s now" % (id, version))
        LOGGER.info("Found article version %s on api: %s", version, latest_url, extra={'id': id})
        return body

    def wait_article(self, id, **constraints):
        "Article must be immediately present with this version, but will poll until the constraints (fields with certain values) are satisfied"
        latest_url = "%s/articles/%s" % (self._host, id)
        def _is_ready():
            response = requests.get(latest_url, headers=self._base_headers())
            if response.status_code == 404:
                LOGGER.debug("%s: 404", latest_url)
                return False
            body = self._ensure_sane_response(response, latest_url)
            if constraints:
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

    def related_articles(self, id):
        url = "%s/articles/%s/related" % (self._host, id)
        response = requests.get(url, headers=self._base_headers())
        assert response.status_code == 200, "%s is not 200 but %s: %s" % (url, response.status_code, response.content)
        LOGGER.info("Found related articles of %s on api: %s", id, url, extra={'id': id})
        return response.json()

    def search(self, for_input):
        url = "%s/search?for=%s" % (self._host, for_input)
        response = requests.get(url, headers=self._base_headers())
        return self._ensure_sane_response(response, url)

    def wait_search(self, word):
        "Returns as soon as there is one result"
        search_url = "%s/search?for=%s" % (self._host, word)
        def _is_ready():
            response = requests.get(search_url, headers=self._base_headers())
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

    def wait_recommendations(self, id):
        "Returns as soon as there is one result"
        recommendations_url = "%s/recommendations/article/%s" % (self._host, id)
        def _is_ready():
            response = requests.get(recommendations_url, headers=self._base_headers({'Accept': 'application/vnd.elife.recommendations+json; version=1'}))
            body = self._ensure_sane_response(response, recommendations_url)
            if len(body['items']) == 0:
                return False
            LOGGER.info("%s: returning %d results",
                        recommendations_url,
                        len(body['items']))
            return body
        return _poll(
            _is_ready,
            "%s returning at least 1 result",
            recommendations_url
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

    def _base_headers(self, headers=None):
        final_headers = {}
        if self._authorization:
            final_headers['Authorization'] = self._authorization
        if headers:
            final_headers.update(headers)
        return final_headers

class JournalCheck:
    CSS_FIGURES_LINK = 'view-selector__link--figures'
    CSS_TEASER_LINK = '.teaser__header_text_link'
    CSS_CAROUSEL_LINK = '.carousel-item__title_link'
    CSS_BLOCK_LINK = '.block-link .block-link__link'
    CSS_PAGER_LINK = '.pager a'
    CSS_ASSET_VIEWER_DOWNLOAD_LINK = '.asset-viewer-inline__download_all_link'
    CSS_DOWNLOAD_LINK = '#downloads a'

    def __init__(self, host, resource_checking_method='head'):
        self._host = host
        self._resource_checking_method = resource_checking_method

    def with_resource_checking_method(self, method):
        return JournalCheck(self._host, method)

    def article(self, id, volume, has_figures=False, version=None):
        url = _build_url("/content/%s/e%s" % (volume, id), self._host)
        if version:
            url = "%sv%s" % (url, version)
        LOGGER.info("Loading %s", url, extra={'id':id})
        body = self.generic(url)
        figures_link = self._link(body, self.CSS_FIGURES_LINK)
        if has_figures:
            assert figures_link is not None, "Cannot find figures link with selector %s" % self.CSS_FIGURES_LINK
            figures_url = _build_url(figures_link, self._host)
            LOGGER.info("Loading %s", figures_url, extra={'id':id})
        return body

    def search(self, query, count=1):
        url = _build_url("/search?for=%s" % query, self._host)
        LOGGER.info("Loading %s", url)
        body = self.generic(url)
        soup = BeautifulSoup(body, "html.parser")
        teaser_links = [a['href'] for a in soup.select(self.CSS_TEASER_LINK)]
        if count is not None:
            assert len(teaser_links) == count, "There are only %d search results" % len(teaser_links)
        return teaser_links

    def homepage(self):
        body = self.generic("/")
        soup = BeautifulSoup(body, "html.parser")
        carousel_links = [a['href'] for a in soup.select(self.CSS_CAROUSEL_LINK)]
        teaser_links = [a['href'] for a in soup.select(self.CSS_TEASER_LINK)]
        links = carousel_links + teaser_links
        return links

    def magazine(self):
        return self.generic("/magazine")

    def generic(self, path):
        response = self.just_load(path)
        match = re.match("^"+self._host, response.url)
        if match:
            self._assert_all_resources_of_page_load(response.content)
        download_links = self._download_links(response.content)
        LOGGER.info("Found download links: %s", pformat(download_links))
        self._assert_all_load(download_links)
        return response.content

    def just_load(self, path):
        url = _build_url(path, self._host)
        LOGGER.info("Loading %s", url)
        response = self._persistently_get(url)
        _assert_status_code(response, 200, url)
        return response

    def listing(self, path):
        body = self.generic(path)
        soup = BeautifulSoup(body, "html.parser")
        teaser_a_tags = soup.select(self.CSS_TEASER_LINK)
        teaser_links = [a['href'] for a in teaser_a_tags]
        LOGGER.info("Loaded listing %s, found links: %s", path, teaser_links)
        pager_a_tags = soup.select(self.CSS_PAGER_LINK)
        pager_links = [a['href'] for a in pager_a_tags]
        return teaser_links, pager_links

    def listing_of_listing(self, path):
        body = self.generic(path)
        soup = BeautifulSoup(body, "html.parser")
        a_tags = soup.select(self.CSS_BLOCK_LINK)
        links = [a['href'] for a in a_tags]
        LOGGER.info("Loaded listing of listing %s, found links: %s", path, links)
        return links

    def _persistently_get(self, url):
        response = requests.get(url)
        # intended behavior at the moment: if the page is too slow to load,
        # timeouts will cut it (a CDN may serve a stale version if it has it)
        if response.status_code == 504:
            response = requests.get(url)
        return response

    def _link(self, body, class_name):
        """Finds out where the link selected with CSS class_name points to.

        May return None if there is no actual link with this class on the page"""
        soup = BeautifulSoup(body, "html.parser")
        links = soup.find_all("a", class_=class_name)
        assert len(links) <= 1, \
               ("Found too many links for the class name %s: %s" % (class_name, links))
        return links[0]['href'] if len(links) == 1 else None

    def _assert_all_resources_of_page_load(self, body, **extra):
        return _assert_all_resources_of_page_load(body, self._host, resource_checking_method=self._resource_checking_method, **extra)

    def _assert_all_load(self, links, **extra):
        return _assert_all_load(links, self._host, resource_checking_method=self._resource_checking_method, **extra)

    def _download_links(self, body):
        soup = BeautifulSoup(body, "html.parser")
        figure_download_links = [a.get('href') for a in soup.select(self.CSS_ASSET_VIEWER_DOWNLOAD_LINK)]
        pdf_download_links = [a.get('href') for a in soup.select(self.CSS_DOWNLOAD_LINK) if a.text in ['Article PDF', 'Figures PDF']]
        return figure_download_links + pdf_download_links


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
    """
    Poll until action_fn returns something truthy. After GLOBAL_TIMEOUT throws an exception.

    action_fn may return:
    - a tuple: first element is a result (truthy or falsy), second element any detail
    - any other type: truthy or falsy decides whether the polling has been successful or not

    error_message may be:
    - a string to be formatted with error_message_args
    - a callable returning such a string"""
    details = {'last_seen': None}
    def wrapped_action_fn():
        possible_result = action_fn()
        if isinstance(possible_result, tuple) and len(possible_result) == 2:
            details['last_seen'] = possible_result[1]
            return possible_result[0]
        else:
            return possible_result
    try:
        return polling.poll(
            wrapped_action_fn,
            timeout=GLOBAL_TIMEOUT,
            step=5
        )
    except polling.TimeoutException:
        if callable(error_message):
            error_message_template = error_message()
        else:
            error_message_template = error_message
        built_error_message = error_message_template % tuple(error_message_args)
        if 'last_seen' in details:
            built_error_message = built_error_message + "\n" + pformat(details['last_seen'])
        raise TimeoutError.giving_up_on(built_error_message)

def _log_connection_error(e):
    LOGGER.debug("Connection error, will retry: %s", e)

def _assert_status_code(response, expected_status_code, url):
    try:
        assert response.status_code == expected_status_code, \
            "Response from %s had status %d, body %s" % (url, response.status_code, response.content)
    except UnicodeDecodeError:
        LOGGER.exception("Unicode error on %s (status code %s)", url, response.status_code)
        LOGGER.error("(%s): type of content %s", url, type(response.content))
        LOGGER.error("(%s): apparent_encoding %s", url, response.apparent_encoding)
        with open("/tmp/response_content.txt", "w") as dump:
            dump.write(response.content)
        LOGGER.error("(%s): written response.content to /tmp")
        raise RuntimeError("Could not decode response from %s (status code %s, headers %s)" % (url, response.status_code, response.headers))

RESOURCE_CACHE = {}

def _assert_all_resources_of_page_load(html_content, host, resource_checking_method='head', **extra):
    """Checks that all <script>, <link>, <video>, <source>, srcset="" load, by issuing HEAD requests that must give 200 OK.

    Returns the BeautifulSoup for reuse"""
    def _srcset_values(srcset):
        values = []
        without_descriptors = re.sub(" \\d+[wx],?", " ", srcset)
        for candidate_string in [cs.strip() for cs in without_descriptors.strip().split(" ")]:
            if candidate_string:
                values.append(candidate_string)
        LOGGER.info("srcset values: %s", values)
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
            if "canonical" not in link.get("rel"):
                resources.append(link.get("href"))
        for video in soup.find_all("video"):
            resources.append(video.get("poster"))
        for media_source in soup.find_all("source"):
            srcset = media_source.get("srcset")
            if srcset:
                resources.extend(_srcset_values(srcset))
        return list(set(resources))
    soup = BeautifulSoup(html_content, "html.parser")
    resources = _resources_from(soup)
    LOGGER.info("Found resources %s", pformat(resources), extra=extra)
    _assert_all_load(resources, host, resource_checking_method, **extra)
    return soup

def _assert_all_load(resources, host, resource_checking_method='head', **extra):
    urls = []
    futures = []
    session = FuturesSession(executor=ThreadPoolExecutor(max_workers=2))
    for path in resources:
        if path is None:
            LOGGER.warning("empty path in resources: %s", resources)
            continue

        url = _build_url(path, host)
        if url in RESOURCE_CACHE and resource_checking_method == 'head':
            LOGGER.debug("Cached HEAD %s: %s", url, RESOURCE_CACHE[url], extra=extra)
            continue
        urls.append(url)
        futures.append(getattr(session, resource_checking_method)(url))

    wait(futures, HTTP_TIMEOUT)

    for url, future in zip(urls, futures):
        response = future.result()
        LOGGER.debug("Loading (%s) resource %s", resource_checking_method, url, extra=extra)
        _assert_status_code(response, 200, url)
        RESOURCE_CACHE[url] = response.status_code

def _build_url(path, host):
    if path.startswith("http://") or path.startswith("https://"):
        return path
    assert path.startswith("/"), ("I found a non-absolute path %s and I don't know how to load it" % path)
    return "%s%s" % (host, path)

EIF = BucketFileCheck(
    aws.S3,
    SETTINGS['bucket_eif'],
    '{id}.{version}/(?P<run>.*)/elife-{id}-v{version}.json',
    '{id}.{version}/'
)
ARCHIVE = BucketFileCheck(
    aws.S3,
    SETTINGS['bucket_archive'],
    # notice {{6}} is the escaping for {6} in the regex,
    # it should not be substituted
    'elife-{id}-(poa|vor)-v{version}-20[0-9]{{12}}.zip',
    'elife-{id}-'
)
WEBSITE = WebsiteArticleCheck(
    host=SETTINGS['website_host'],
    user=SETTINGS['website_user'],
    password=SETTINGS['website_password']
)
IMAGES_BOT_CDN = BucketFileCheck(
    aws.S3,
    SETTINGS['bucket_cdn'],
    'articles/{id}/elife-{id}-{figure_name}-v{version}.jpg',
    'articles/{id}/elife-{id}-{figure_name}-v{version}.jpg'
)
IMAGES_PUBLISHED_CDN = BucketFileCheck(
    aws.S3,
    SETTINGS['bucket_published'],
    'articles/{id}/elife-{id}-{figure_name}-v{version}.jpg',
    'articles/{id}/elife-{id}-{figure_name}-v{version}.jpg'
)
XML_PUBLISHED_CDN = BucketFileCheck(
    aws.S3,
    SETTINGS['bucket_published'],
    'articles/{id}/elife-{id}-v{version}.xml',
    'articles/{id}/elife-{id}-v{version}.xml'
)
XML_DOWNLOAD_PUBLISHED_CDN = BucketFileCheck(
    aws.S3,
    SETTINGS['bucket_published'],
    'articles/{id}/elife-{id}-v{version}-download.xml',
    'articles/{id}/elife-{id}-v{version}-download.xml'
)
PDF_BOT_CDN = BucketFileCheck(
    aws.S3,
    SETTINGS['bucket_cdn'],
    'articles/{id}/elife-{id}-v{version}.pdf',
    'articles/{id}/elife-{id}-v{version}.pdf'
)
PDF_PUBLISHED_CDN = BucketFileCheck(
    aws.S3,
    SETTINGS['bucket_published'],
    'articles/{id}/elife-{id}-v{version}.pdf',
    'articles/{id}/elife-{id}-v{version}.pdf'
)
PDF_DOWNLOAD_PUBLISHED_CDN = BucketFileCheck(
    aws.S3,
    SETTINGS['bucket_published'],
    'articles/{id}/elife-{id}-v{version}-download.pdf',
    'articles/{id}/elife-{id}-v{version}-download.pdf'
)
DASHBOARD = DashboardArticleCheck(
    host=SETTINGS['dashboard_host'],
    user=SETTINGS['dashboard_user'],
    password=SETTINGS['dashboard_password']
)
LAX = LaxArticleCheck(
    host=SETTINGS['lax_host']
)
API = ApiCheck(
    host=SETTINGS['api_gateway_host']
)
API_PREVIEW = ApiCheck(
    host=SETTINGS['api_gateway_host'],
    authorization=SETTINGS['api_gateway_authorization']
)
JOURNAL = JournalCheck(
    host=SETTINGS['journal_host']
)
JOURNAL_CDN = JournalCheck(
    host=SETTINGS['journal_cdn_host']
)
JOURNAL_GENERIC_PATHS = [
    '/about',
    '/about/early-career',
    '/about/innovation',
    '/about/openness',
    '/about/peer-review',
    '/alerts',
    '/contact',
    '/for-the-press',
    '/resources',
    '/terms',
    '/who-we-work-with',
]
JOURNAL_LISTING_PATHS = [
    '/annual-reports',
    '/articles/correction',
    '/collections',
    "/community",
    '/inside-elife',
    '/labs',
    '/podcast',
]
JOURNAL_LISTING_OF_LISTING_PATHS = [
    '/archive/2016',
    '/subjects',
]

GITHUB_XML = GithubCheck(
    repo_url=SETTINGS['github_article_xml_repository_url']
)
