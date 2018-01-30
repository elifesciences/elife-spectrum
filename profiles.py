from spectrum import load, input, checks
from sys import argv, exit
import fileinput
import requests


if __name__ == '__main__':
    anonymous_session = input.JOURNAL.session()
    anonymous_session.enable_feature_flag()
    for line in fileinput.input():
        profile_id = line.strip("\n")
        checks.LOGGER.info("Profile: %s", profile_id) 
        checks.API.profile(profile_id)
        anonymous_session.check('/profiles/%s' % profile_id)

