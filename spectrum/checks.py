"""
Read-only, headless checks against services under test.

Contains anything from HTTP(S) calls to REST JSON APIs to S3 checks over the presence or recent modification of files.
"""
from concurrent.futures import ThreadPoolExecutor, wait
from datetime import datetime
from pprint import pformat
import re
from ssl import SSLError

from bs4 import BeautifulSoup
import requests
from requests.exceptions import ConnectionError
from requests_futures.sessions import FuturesSession
from spectrum import aws, config, logger, polling, retries
from spectrum.config import SETTINGS
from spectrum.exceptions import UnrecoverableError, assert_status_code
from spectrum.mailcatcher import MailcatcherCheck


# TODO: install proper SSL certificate on elife-dashboard-develop--end2end to avoid this
requests.packages.urllib3.disable_warnings()
GLOBAL_TIMEOUT = polling.GLOBAL_TIMEOUT
HTTP_TIMEOUT = 30
LOGGER = logger.logger(__name__)

class BucketFileCheck:
    def __init__(self, s3, bucket_name, key, prefix=None):
        """Polls for the existence of a file in bucket_name.

        key is a pattern to be filled with the args passed to of().
        prefix is a API call filter to be used to reduce the number of objects to scan.
        """
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
            id = kwargs.get('id')
            bucket = self._s3.Bucket(self._bucket_name)
            # TODO: necessary?
            bucket.load()
            all_objects = bucket.objects.all()
            if self._prefix:
                prefix = self._prefix.format(**kwargs)
                all_objects = all_objects.filter(Prefix=prefix)
                LOGGER.debug(
                    "Filtering by prefix %s",
                    prefix,
                    extra={'id': id}
                )
            for file in all_objects:
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
                            match.groups(),
                            file.key,
                            extra={'id': id}
                        )
                        return (match.groups(), {'key': file.key})
                    else:
                        return True
        except SSLError as e:
            _log_connection_error(e)
        return False

class DashboardArticleCheck:
    def __init__(self, host, user, password):
        self._host = host
        self._user = user
        self._password = password

    def ready_to_publish(self, id, version, run=None, run_after=None):
        # it is not enough to wait for the "ready to publish" state because
        # when ingesting a run 2 for a particular version, the article is still
        # in "ready to publish" from run 1. This is a problem of the dashboard
        # that should change into "not ready to publish, if you press the button
        # now it will break everything".
        # We can't change the dashboard easily because it's a warzone
        # so we will pass an additional check on the current run instead.
        article_on_dashboard = self._wait_for_status(id, version, run=run, status="ready to publish", run_after=run_after, run_contains_events=['Ready To Publish'])
        current_version = article_on_dashboard['versions'][str(version)]
        preview_link = current_version['details']['preview-link']
        LOGGER.info("Found preview-link on dashboard: %s", preview_link)
        assert preview_link, ("Article %s version %s must have a preview-link:\n%s" % (id, version, current_version))
        return article_on_dashboard

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

    def _wait_for_status(self, id, version, status, run=None, run_after=None, run_contains_events=None):
        return _poll(
            lambda: self._is_present(id, version, status, run=run, run_after=run_after, run_contains_events=run_contains_events),
            lambda: "article version %s in status %s on dashboard (run filter %s, run_after filter %s): %s/api/article/%s",
            version,
            status,
            run,
            run_after,
            self._host,
            id
        )

    def _is_present(self, id, version, status, run=None, run_after=None, run_contains_events=None):
        url = self._article_api(id)
        try:
            response = requests.get(url, auth=(self._user, self._password), verify=False)
            if response.status_code != 200:
                return False, "Response code: %s" % response.status_code
            if response.status_code >= 500:
                raise UnrecoverableError(response)
            article = response.json()
            version_contents = self._check_for_version(article, version)
            outcome, dump = self._extract_run_contents(article, version_contents, status, run, run_after, run_contains_events)
            if not outcome:
                return outcome, dump
            else:
                run_contents = dump
            LOGGER.info(
                "Found %s version %s in status %s on dashboard with run %s (required: events: %s)",
                url,
                version,
                status,
                run_contents['run-id'],
                run_contains_events,
                extra={'id': id}
            )
            return article
        except ConnectionError as e:
            _log_connection_error(e)
            return False, e

    def _extract_run_contents(self, article, version_contents, status, run, run_after, run_contains_events):
        if not version_contents:
            return False, article
        if not version_contents['details'].get('preview-link'):
            return False, version_contents
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
            return False, version_contents
        if not self._check_run_events(run_contents, run_contains_events):
            return False, run_contents

        self._ensure_no_unrecoverable_errors(run_contents)

        return True, run_contents

    def _check_for_version(self, article, version):
        version_key = str(version)
        if 'versions' not in article:
            return False
        if version_key not in article['versions']:
            return False
        return article['versions'][version_key]

    def _check_for_run(self, version_contents, run=None):
        if run:
            matching_runs = [r for _, r in version_contents['runs'].items() if r['run-id'] == run]
        else:
            matching_runs = version_contents['runs'].values()
        if len(matching_runs) > 1:
            raise RuntimeError("Too many runs matching run-id %s: %s", run, pformat(matching_runs))
        if len(matching_runs) == 0:
            return False
        return list(matching_runs)[0]

    def _check_for_run_after(self, version_contents, run_after):
        matching_runs = [r for _, r in version_contents['runs'].items() if datetime.fromtimestamp(r['first-event-timestamp']).strftime('%s') >= run_after.strftime('%s')]
        if len(matching_runs) > 1:
            raise RuntimeError("Too many runs after run_after %s: %s", run_after, matching_runs)
        if len(matching_runs) == 0:
            return False
        return list(matching_runs)[0]

    def _check_run_events(self, run_contents, run_contains_events):
        if run_contains_events:
            for important_event in run_contains_events:
                if important_event not in [e['event-type'] for e in run_contents['events']]:
                    return False

        return True

    def _ensure_no_unrecoverable_errors(self, run_contents):
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
            "article version %s in lax: %s/api/v2/articles/%s/versions/%s",
            version, self._host, id, version
        )

    def _is_present(self, id, version):
        template = "%s/api/v2/articles/%s/versions/%s"
        url = template % (self._host, id, version)
        try:
            response = requests.get(url)
            if response.status_code != 200:
                return False
            if response.status_code >= 500:
                raise UnrecoverableError(response)
            LOGGER.info("Found article version %s in lax: %s", version, url, extra={'id': id})
            return response.json()
        except ConnectionError as e:
            _log_connection_error(e)
            return False

# The API is large, hence many methods to test it
# pylint: disable=too-many-public-methods
class ApiCheck:
    def __init__(self, host, authorization=None):
        self._host = host
        self._authorization = authorization

    def labs_posts(self):
        #body =
        self._list_api('/labs-posts', 'labs-post')
        #self._ensure_list_has_at_least_1_element(body)

    def subjects(self):
        #body =
        self._list_api('/subjects', 'subject')
        #self._ensure_list_has_at_least_1_element(body)

    def podcast_episode(self, number):
        return self._item_api('/podcast-episodes/%d' % number, 'podcast-episode')

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

    def profiles(self):
        return self._list_api('/profiles', 'profile')

    def profile(self, id):
        return self._item_api('/profiles/%s' % id, 'profile')

    def annotations(self, profile_id, access='public'):
        return self._list_api('/annotations?by=%s&access=%s' % (profile_id, access), 'annotation')

    def digests(self):
        return self._list_api('/digests', 'digest')

    def digest(self, id):
        return self._item_api('/digests/%s' % id, 'digest')

    def wait_digest(self, id, item_check=None):
        latest_url = "%s/digests/%s" % (self._host, id)
        def _is_ready():
            response = requests.get(latest_url, headers=self._base_headers())
            if response.status_code == 404:
                LOGGER.debug("%s: 404", latest_url)
                return False
            body = self._ensure_sane_response(response, latest_url)

            item_check_presence = ''
            if item_check:
                if not item_check(body):
                    return False
                else:
                    item_check_presence = " and satisfying check %s" % item_check
            LOGGER.info("%s present%s", latest_url, item_check_presence)
            return body
        return _poll(
            _is_ready,
            "%s",
            latest_url
        )

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

    def wait_article(self, id, item_check=None, **constraints):
        "Article must be immediately present with this version, but will poll until the constraints (fields with certain values) are satisfied"
        latest_url = "%s/articles/%s" % (self._host, id)
        def _is_ready():
            response = requests.get(latest_url, headers=self._base_headers())
            if response.status_code == 404:
                LOGGER.debug("%s: 404", latest_url)
                return False
            body = self._ensure_sane_response(response, latest_url)
            item_check_presence = ''
            if item_check:
                if not item_check(body):
                    return False
                else:
                    item_check_presence = " and satisfying check %s" % item_check
            constraints_presence = ''
            if constraints:
                for field, value in constraints.items():
                    if body[field] != value:
                        LOGGER.debug("%s: field `%s` is not `%s` but `%s`",
                                     latest_url, field, value, body[field])
                        return False
                constraints_presence = " and conforming to constraints %s" % constraints
            LOGGER.info("%s present%s%s", latest_url, item_check_presence, constraints_presence)
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

    def wait_search(self, word, item_check=None):
        """Returns as soon as there is one result.

        item_check can be used to verify the only result satisfies a condition"""
        search_url = "%s/search?for=%s" % (self._host, word)
        def _is_ready():
            response = retries.persistently_get(search_url, headers=self._base_headers())
            body = self._ensure_sane_response(response, search_url)
            LOGGER.debug("Search result: %s", body)
            if len(body['items']) == 0:
                return False
            item_check_presence = ''
            if item_check:
                if not item_check(body['items'][0]):
                    return False
                else:
                    item_check_presence = " and satisfying check %s" % item_check
            LOGGER.info("%s: returning %d results%s",
                        search_url,
                        len(body['items']),
                        item_check_presence)
            return body
        return _poll(
            _is_ready,
            "%s returning at least 1 result",
            search_url
        )

    def item_check_image(self, uri=None):
        class ItemCheckImage():
            def __init__(self, uri):
                self._uri = uri
            def __call__(self, item):
                if 'image' not in item:
                    return False
                if self._uri is None:
                    return True
                return item['image']['thumbnail']['source']['uri'] == self._uri
            def __str__(self):
                return "ItemCheckImage(%s)" % self._uri
        return ItemCheckImage(uri)

    def item_check_content(self, contained):
        class ItemCheckContent():
            def __init__(self, contained):
                self._contained = contained
            def __call__(self, item):
                for block in item['content']:
                    if block.get('text'):
                        if self._contained in block['text']:
                            return True
                return False
            def __str__(self):
                return "ItemCheckContent(contained=%s)" % self._contained
        return ItemCheckContent(contained)

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
    CSS_TEASER_LINK = '.teaser__header_text_link'
    CSS_CAROUSEL_LINK = '.carousel-item__title_link'
    CSS_BLOCK_LINK = '.block-link .block-link__link'
    # only valid for non-JavaScript pages
    CSS_ANNOTATION_LINK = '.annotation-teaser'
    CSS_PAGER_LINK = '.pager a'
    CSS_ASSET_VIEWER_DOWNLOAD_LINK = '.asset-viewer-inline__download_all_link'
    CSS_DOWNLOAD_LINK = '#downloads a'
    CLASS_FIGURES_LINK = 'view-selector__link--figures'
    CLASS_SUBJECT_LINK = 'content-header__subject_link'

    def __init__(self, host, resource_checking_method='head', query_string=None, headers=None):
        self._host = host
        self._resource_checking_method = resource_checking_method
        self._query_string = query_string
        self._headers = headers

    def with_resource_checking_method(self, method):
        return JournalCheck(self._host, method, self._query_string, self._headers)

    def with_query_string(self, query_string):
        return JournalCheck(self._host, self._resource_checking_method, query_string, self._headers)

    def with_headers(self, headers):
        return JournalCheck(self._host, self._resource_checking_method, self._query_string, headers)

    def article(self, id, has_figures=False, version=None):
        url = _build_url("/articles/%s" % id, self._host)
        if version:
            url = "%sv%s" % (url, version)
        LOGGER.info("Loading %s", url, extra={'id':id})
        body = self.generic(url)
        figures_page_links = self._links(body, self.CLASS_FIGURES_LINK)
        if has_figures:
            assert len(figures_page_links) == 1, "Expected a single figures page link with selector %s, found %s" % (self.CLASS_FIGURES_LINK, figures_page_links)
            figures_url = _build_url(figures_page_links[0], self._host)
            LOGGER.info("Loading figures page %s", figures_url, extra={'id':id})
            self.generic(url)
        return body

    def article_only_subject(self, id, subject_id, version=None):
        url = _build_url("/articles/%s" % id, self._host)
        if version:
            url = "%sv%s" % (url, version)
        LOGGER.info("Loading %s", url, extra={'id':id})
        body = self.generic(url)
        subjects_links = self._links(body, self.CLASS_SUBJECT_LINK)
        assert subjects_links == ['/subjects/%s' % subject_id], "Incorrect subjects `%s` linked from article page %s (expected subject id `%s`)" % (subjects_links, url, subject_id)

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
        if self._query_string:
            if "?" in url:
                url = "%s&%s" % (url, self._query_string)
            else:
                url = "%s?%s" % (url, self._query_string)
        LOGGER.info("Loading %s", url)
        response = retries.persistently_get(url, headers=self._headers)
        assert_status_code(response, 200, url)
        return response

    def redirect(self, path, expected, status_code=301):
        url = _build_url(path, self._host)
        LOGGER.info("Loading %s", url)
        response = requests.get(url, allow_redirects=False)
        assert_status_code(response, status_code, url)
        location = response.headers['Location']
        assert location.startswith(self._host)
        assert location == ('%s%s' % (self._host, expected))

    def listing(self, path):
        body = self.generic(path)
        soup = BeautifulSoup(body, "html.parser")
        teaser_a_tags = soup.select(self.CSS_TEASER_LINK)
        teaser_links = [a['href'] for a in teaser_a_tags]
        LOGGER.info("Loaded listing %s, found teaser links: %s", path, teaser_links)
        pager_a_tags = soup.select(self.CSS_PAGER_LINK)
        pager_links = [a['href'] for a in pager_a_tags]
        LOGGER.info("Loaded listing %s, found page links: %s", path, pager_links)
        return teaser_links, pager_links

    def listing_of_listing(self, path):
        body = self.generic(path)
        soup = BeautifulSoup(body, "html.parser")
        a_tags = soup.select(self.CSS_BLOCK_LINK)
        links = [a['href'] for a in a_tags]
        LOGGER.info("Loaded listing of listing %s, found links: %s", path, links)
        return links

    # TODO: use elsewhere than spectrum.load?
    def profile(self, path):
        body = self.generic(path)
        soup = BeautifulSoup(body, "html.parser")
        annotation_li_tags = soup.select(self.CSS_ANNOTATION_LINK)
        annotation_links = [a['data-in-context-uri'] for a in annotation_li_tags]
        LOGGER.info("Loaded listing %s, found annotation links: %s", path, annotation_links)
        pager_a_tags = soup.select(self.CSS_PAGER_LINK)
        pager_links = [a['href'] for a in pager_a_tags]
        LOGGER.info("Loaded listing %s, found page links: %s", path, pager_links)
        return annotation_links, pager_links

    def digest(self, id):
        url = _build_url("/digests/%s" % id, self._host)
        LOGGER.info("Loading %s", url, extra={'id':id})
        return self.generic(url)

    def _links(self, body, class_name):
        """Finds out where 0 or more links selected with CSS class_name point to.

        Will return [] if there are no actual links with this class on the page"""
        soup = BeautifulSoup(body, "html.parser")
        links = soup.find_all("a", class_=class_name)
        return [l['href'] for l in links]

    def _assert_all_resources_of_page_load(self, body, **extra):
        return _assert_all_resources_of_page_load(body, self._host, resource_checking_method=self._resource_checking_method, **extra)

    def _assert_all_load(self, links, **extra):
        return _assert_all_load(links, self._host, resource_checking_method=self._resource_checking_method, **extra)

    def _download_links(self, body):
        soup = BeautifulSoup(body, "html.parser")
        figure_download_links = [a.get('href') for a in soup.select(self.CSS_ASSET_VIEWER_DOWNLOAD_LINK)]
        pdf_download_links = [a.get('href') for a in soup.select(self.CSS_DOWNLOAD_LINK) if a.text in ['Article PDF', 'Figures PDF']]
        return figure_download_links + pdf_download_links

class HttpCheck:
    def __init__(self, url):
        self._url = url

    def of(self, text_match=None, **kwargs):
        target = self._url.format(**kwargs)
        if text_match:
            text_match_suffix = ' with text matching `%s`' % text_match
        else:
            text_match_suffix = ''
        return _poll(
            lambda: _is_content_present(target, text_match, **kwargs),
            "URL %s%s",
            target,
            text_match_suffix
        )


class GithubCheck:
    def __init__(self, repo_url):
        "repo_url must have a {path} placeholder in it that will be substituted with the file path"
        self._repo_url = repo_url

    def article(self, id, version=1, text_match=None):
        url = self._repo_url.format(path=('/articles/elife-%s-v%s.xml' % (id, version)))
        error_message_suffix = (" and matching %s" % text_match) if text_match else ""
        _poll(
            lambda: _is_content_present(url, text_match=text_match, **{'id':id}),
            "article on github with URL %s existing" + error_message_suffix,
            url
        )

def _is_content_present(url, text_match=None, **extra):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            if text_match:
                if text_match in response.content:
                    LOGGER.info("Body of %s matches %s", url, text_match, extra=extra)
                    return True
                else:
                    LOGGER.debug("Body of %s does not match %s", url, text_match, extra=extra)
            else:
                LOGGER.info("GET on %s with status 200", url, extra=extra)
                return True
        else:
            LOGGER.debug("GET on %s with status %s", url, response.status_code, extra=extra)
            return False
    except ConnectionError as e:
        _log_connection_error(e)
    return False

class PeerscoutCheck:
    def __init__(self, host, user, password):
        self._host = host
        self._user = user
        self._password = password

    def recommend(self, manuscript='', subject='', keywords='', abstract=''):
        template = "%s/api/recommend-reviewers"
        query = {
            "manuscript_no": manuscript,
            "subject_area": subject,
            "keywords": keywords,
            "abstract": abstract,
        }
        url = template % self._host
        response = requests.get(url, params=query, auth=(self._user, self._password))
        LOGGER.info("Found recommendations at %s for query %s", url, query)
        if response.status_code > 299:
            raise UnrecoverableError(response)
        return response.json()

class ObserverCheck:
    def __init__(self, host):
        self._host = host

    def latest_article(self, id):
        template = "%s/report/latest-articles?per-page=100&page=%s"
        url = template % (self._host, "%s") # page will be substituted later
        return _poll(
            lambda: self._is_present(url, id),
            "article with id %s at %s",
            id, url
        )

    def _is_present(self, url_page_template, id):
        page = 1
        while True:
            url = url_page_template % page
            response = requests.get(url)
            LOGGER.debug("Loaded %s (%s)", url, response.status_code, extra={'id':id})
            if response.status_code > 299:
                raise UnrecoverableError(response)
            soup = BeautifulSoup(response.content, "lxml-xml")
            target_guid = "https://dx.doi.org/10.7554/eLife.%s" % id
            guids = {item.guid.string:item for item in soup.rss.channel.find_all("item")}
            if not guids:
                # we have reached an empty page
                return False
            if target_guid in guids.keys():
                LOGGER.info("Found item %s at %s:\n%s", target_guid, url, guids[target_guid], extra={'id':id})
                return guids[target_guid]
            LOGGER.debug("Item %s not found on page %s: %s", target_guid, page, pformat(guids.keys()), extra={'id':id})
            page = page + 1

def _poll(action_fn, error_message, *error_message_args):
    return polling.poll(action_fn, error_message, *error_message_args)

def _log_connection_error(e):
    LOGGER.debug("Connection error, will retry: %s", e)

RESOURCE_CACHE = {}

def _assert_all_resources_of_page_load(html_content, host, resource_checking_method='head', **extra):
    """Checks that all <script>, <link>, <video>, <source>, srcset="" load, by issuing HEAD requests that must give 200 OK.

    Returns the BeautifulSoup for reuse"""
    def _srcset_values(srcset):
        values = []
        without_descriptors = re.sub(" \\d+(\\.\\d+)?[wx],?", " ", srcset)
        for candidate_string in [cs.strip() for cs in without_descriptors.strip().split(" ")]:
            if candidate_string:
                values.append(candidate_string)
        LOGGER.debug("srcset values: %s", values)
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
            if " ".join(link.get("rel")) not in ["canonical", "next", "prev", "shortlink"]:
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
    LOGGER.debug("Found resources %s", pformat(resources), extra=extra)
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

        if path.startswith("data:"):
            LOGGER.debug("Skipping `data:` resource '%s'", path)
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

        if response.status_code == 504:
            LOGGER.warning("Loading (%s) resource %s again due to 504 timeout", resource_checking_method, url, extra=extra)
            response = requests.get(url)

        assert_status_code(response, 200, url)
        RESOURCE_CACHE[url] = response.status_code

def _build_url(path, host):
    if path.startswith("http://") or path.startswith("https://"):
        return path
    assert path.startswith("/"), ("I found a non-absolute path %s and I don't know how to load it" % path)
    return "%s%s" % (host, path)

ARCHIVE = BucketFileCheck(
    aws.S3,
    SETTINGS['bucket_archive'],
    # notice {{12}} is the escaping for {6} in the regex,
    # it should not be substituted
    'elife-{id}-(poa|vor)-v{version}-20[0-9]{{12}}.zip',
    'elife-{id}-'
)
PERSONALISED_COVERS_A4 = BucketFileCheck(
    aws.S3,
    SETTINGS['bucket_covers'],
    '{id}-cover-a4.pdf',
    '{id}-'
)
PERSONALISED_COVERS_LETTER = BucketFileCheck(
    aws.S3,
    SETTINGS['bucket_covers'],
    '{id}-cover-letter.pdf',
    '{id}-'
)
IMAGES_PUBLISHED_CDN_BUCKET = BucketFileCheck(
    aws.S3,
    SETTINGS['bucket_published'],
    'articles/{id}/elife-{id}-{figure_name}-v{version}.jpg',
    'articles/{id}/elife-{id}-{figure_name}-v{version}.jpg'
)
XML_PUBLISHED_CDN_BUCKET = BucketFileCheck(
    aws.S3,
    SETTINGS['bucket_published'],
    'articles/{id}/elife-{id}-v{version}.xml',
    'articles/{id}/elife-{id}-v{version}.xml'
)
PDF_PUBLISHED_CDN_BUCKET = BucketFileCheck(
    aws.S3,
    SETTINGS['bucket_published'],
    'articles/{id}/elife-{id}-v{version}.pdf',
    'articles/{id}/elife-{id}-v{version}.pdf'
)
DIGEST_JPG_PUBLISHED_CDN_BUCKET = BucketFileCheck(
    aws.S3,
    SETTINGS['bucket_published'],
    'digests/{id}/digest-{id}.jpg',
    'digests/{id}/digest-{id}.jpg'
)
PACKAGING_BUCKET_OUTBOX = BucketFileCheck(
    aws.S3,
    SETTINGS['bucket_packaging'],
    '{vendor}/outbox/elife{id}.xml',
    '{vendor}/outbox/elife{id}.xml'
)
PACKAGING_BUCKET_BATCH = BucketFileCheck(
    aws.S3,
    SETTINGS['bucket_packaging'],
    # could probably pass in the date as {date}
    '{vendor}/published/20[0-9]{{6}}/batch/(elife-.*\\.xml)',
    '{vendor}/published/'
)
PACKAGING_BUCKET_POA_ZIP = BucketFileCheck(
    aws.S3,
    SETTINGS['bucket_packaging'],
    'outbox/elife_poa_e{id}_ds.zip',
    'outbox/elife_poa_e{id}_ds.zip'
)
PACKAGING_BUCKET_POA_XML = BucketFileCheck(
    aws.S3,
    SETTINGS['bucket_packaging'],
    'outbox/elife_poa_e{id}.xml',
    'outbox/elife_poa_e{id}.xml'
)
PACKAGING_BUCKET_POA_PDF = BucketFileCheck(
    aws.S3,
    SETTINGS['bucket_packaging'],
    'outbox/decap_elife_poa_e{id}.pdf',
    'outbox/decap_elife_poa_e{id}.pdf'
)
BOT_INTERNAL_DIGEST_OUTBOX_DOC = BucketFileCheck(
    aws.S3,
    SETTINGS['bucket_configuration'],
    'digests/outbox/{id}/digest-{id}.docx',
    'digests/outbox/{id}/digest-{id}.docx',
)
BOT_INTERNAL_DIGEST_OUTBOX_JPG = BucketFileCheck(
    aws.S3,
    SETTINGS['bucket_configuration'],
    'digests/outbox/{id}/digest-{id}.jpg',
    'digests/outbox/{id}/digest-{id}.jpg',
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
# allow access to all restricted content
API_SUPER_USER = ApiCheck(
    host=SETTINGS['api_gateway_host'],
    authorization=SETTINGS['api_gateway_authorization']
)
JOURNAL = JournalCheck(
    host=SETTINGS['journal_host']
)
JOURNAL_CDN = JournalCheck(
    host=SETTINGS['journal_cdn_host']
)
JOURNAL_GOOGLEBOT = JOURNAL_CDN.with_headers({'User-Agent': config.GOOGLEBOT_USER_AGENT})
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
CDN_XML = HttpCheck(
    str(SETTINGS['generic_cdn_host']) + '/articles/{id}/elife-{id}-v{version}.xml'
)
GITHUB_XML = GithubCheck(
    repo_url=SETTINGS['github_article_xml_repository_url']
)
PEERSCOUT = PeerscoutCheck(
    host=SETTINGS['peerscout_host'],
    user=SETTINGS['peerscout_user'],
    password=SETTINGS['peerscout_password']
)
OBSERVER = ObserverCheck(
    host=SETTINGS['observer_host']
)
PUBMED = HttpCheck(
    str(SETTINGS['bot_host']) + '/pubmed/{xml}'
)
BOT_EMAILS = MailcatcherCheck(SETTINGS['bot_mailcatcher'])
BOT_INTERNAL = (SETTINGS['bot_mailcatcher'])
