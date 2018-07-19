import os
from ConfigParser import RawConfigParser

CONFIG = RawConfigParser()
CONFIG.read('./app.cfg')
ENV = os.environ['SPECTRUM_ENVIRONMENT'] if 'SPECTRUM_ENVIRONMENT' in os.environ else 'end2end'
COMMON = dict(CONFIG.items('common'))
SETTINGS = dict(CONFIG.items(ENV))

GOOGLEBOT_USER_AGENT = 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'

if __name__ == '__main__':
    for section in CONFIG.sections():
        print section
        for option in CONFIG.options(section):
            print "   %s: %s" % (option, CONFIG.get(section, option))


