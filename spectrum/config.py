from ConfigParser import RawConfigParser

CONFIG = RawConfigParser()
CONFIG.read('./app.cfg')

if __name__ == '__main__':
    for section in CONFIG.sections():
        print section
        for option in CONFIG.options(section):
            print "   %s: %s" % (option, CONFIG.get(section, option))


