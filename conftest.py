import sys

import pytest

# so that other processes run by xdist can still print
# http://stackoverflow.com/questions/27006884/pytest-xdist-without-capturing-output
# https://github.com/pytest-dev/pytest/issues/680
sys.stdout = sys.stderr

def pytest_addoption(parser):
    parser.addoption("--article-id", action="store", default=None,
            help="pass an article id to filter only tests related to it")

@pytest.fixture
def article_id_filter(request):
    return request.config.getoption('--article-id')
