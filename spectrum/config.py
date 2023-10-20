"""utility library for parsing app.cfg into global variables.

contains no tests to be run."""

import os
from configparser import RawConfigParser

import urllib3

CONFIG = RawConfigParser()
CONFIG.read('./app.cfg')
ENV = os.environ['SPECTRUM_ENVIRONMENT'] if 'SPECTRUM_ENVIRONMENT' in os.environ else 'end2end'
COMMON = dict(CONFIG.items('common'))
SETTINGS = dict(CONFIG.items(ENV))

GOOGLEBOT_USER_AGENT = 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'
# https://urllib3.readthedocs.io/en/latest/user-guide.html#ssl would solve the warning,
# but it is `requests` using `urllib3` here so unclear how to apply that guide
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

if __name__ == '__main__':
    for section in CONFIG.sections():
        print(section)
        for option in CONFIG.options(section):
            print("   %s: %s" % (option, CONFIG.get(section, option)))
