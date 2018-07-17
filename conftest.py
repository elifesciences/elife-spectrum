import os
import sys

import pytest
from spectrum import generator
from spectrumprivate import file_paths
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
    def from_template_id(template_id, **template_variables):
        article = generator.article_zip(str(template_id), template_variables=template_variables)
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

    for filename in created_files:
        os.remove(filename)
        generator.LOGGER.info("Deleted %s", filename)

def _clean_all(created_articles):
    for article in created_articles:
        article.clean()

