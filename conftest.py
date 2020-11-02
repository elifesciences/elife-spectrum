"""Test fixtures made available via decorators during the test run.

The `conftest.py` file is a barely documented pytest-ism. 
pytest will look for this file and execute it's contents automatically.

In this file we're defining globally available test fixtures that are injected magically using parameter 
name matching alone. For example:

    def test_searching_for_a_new_article(generate_article, modify_article):
        ...

will have the results of calling the `generate_article` fixture passed as the first parameter and the 
results of calling the `modify_article` fixture passed as the second parameter.

Both of those fixtures `yield` a function that encloses a stateful list that is used to ensure the fixture knows what to clean up afterwards: 

https://stackoverflow.com/questions/34466027/in-pytest-what-is-the-use-of-conftest-py-files
https://docs.pytest.org/en/latest/writing_plugins.html#conftest-py-plugins
https://docs.pytest.org/en/stable/fixture.html#factories-as-fixtures"""

from datetime import datetime
import os
import sys

import pytest
from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from spectrumprivate import file_paths

from spectrum import generator
# so that other processes run by xdist can still print
# http://stackoverflow.com/questions/27006884/pytest-xdist-without-capturing-output
# https://github.com/pytest-dev/pytest/issues/680
sys.stdout = sys.stderr

def pytest_addoption(parser):
    parser.addoption("--article-id",
                     action="store",
                     default=None,
                     help="pass an article id to filter only tests related to it")

@pytest.fixture
def article_id_filter(request):
    return request.config.getoption('--article-id')

@pytest.yield_fixture
#@pytest.fixture in pytest>=2.10
def generate_article():
    created_articles = []
    def from_template_id(template_id, article_id=None, **template_variables):
        article = generator.article_zip(str(template_id), article_id=article_id, template_variables=template_variables)
        created_articles.append(article)
        return article
    yield from_template_id
    _clean_all(created_articles)

@pytest.yield_fixture
def version_article():
    created_articles = []
    def from_original_article(original_article, new_version):
        article = original_article.new_version(version=new_version)
        created_articles.append(article)
        return article
    yield from_original_article
    _clean_all(created_articles)

@pytest.yield_fixture
def modify_article():
    created_articles = []
    def from_original_article(original_article, new_version=None, replacements=None):
        article = original_article.new_revision(version=new_version)
        article.replace_in_text(replacements if replacements else {})
        created_articles.append(article)
        return article
    yield from_original_article
    _clean_all(created_articles)

@pytest.yield_fixture
def poa_csvs():
    created_files = []

    def create_csv_files(source_article_id, target_article_id):
        csv_files = []
        for csv_file in file_paths("poa/*.csv"):
            csv_files.append(generator.article_ejp_csv(
                csv_file,
                source_article_id=source_article_id,
                target_article_id=target_article_id
            ))
        created_files.extend(csv_files)

        return csv_files

    yield create_csv_files

    _remove_all(created_files)

@pytest.yield_fixture
def poa_zip():
    created_files = []

    def create_zip_file(source_article_id, target_article_id):
        source_zip_file = file_paths("poa/*.zip")[0]
        generated_zip_file = generator.article_ejp_zip(
            source_zip_file,
            source_article_id=source_article_id,
            target_article_id=target_article_id
        )
        created_files.append(generated_zip_file)

        return generated_zip_file

    yield create_zip_file

    _remove_all(created_files)

@pytest.yield_fixture
#@pytest.fixture in pytest>=2.10
def generate_digest():
    created_digests = []
    def from_template_id(template_id):
        digest = generator.digest_zip(str(template_id))
        created_digests.append(digest.filename())
        return digest
    yield from_template_id
    _remove_all(created_digests)

@pytest.yield_fixture
#@pytest.fixture in pytest>=2.10
def get_selenium_driver(request):
    test_function = "%s.%s" % (request.module.__name__, request.function.__name__)
    drivers = []
    def creation():
        driver = webdriver.Remote(
            command_executor='http://127.0.0.1:4444/wd/hub',
            desired_capabilities=DesiredCapabilities.CHROME
        )
        driver.implicitly_wait(10) # seconds
        drivers.append(driver)
        return driver
    yield creation
    for driver in drivers:
        screenshot_path = 'build/screenshots/%s-%s.png' % (test_function, datetime.utcnow().isoformat())
        # TODO: temporary LOGGER throughout this file
        generator.LOGGER.info("Taking final screenshot at %s", screenshot_path)
        driver.save_screenshot(screenshot_path)
        generator.LOGGER.info("Deleting Selenium driver %s", driver)
        driver.quit()

def _remove_all(created_files):
    for filename in created_files:
        os.remove(filename)
        generator.LOGGER.info("Deleted %s", filename)

def _clean_all(created_articles):
    for article in created_articles:
        article.clean()

# FUTURE: try to customize report
#def pytest_runtest_makereport(item):
#    pass
