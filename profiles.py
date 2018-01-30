from spectrum import load, input, checks
from sys import argv, exit
import fileinput
import requests

# TODO: with_resource_checking_method('GET')
JOURNAL = checks.JOURNAL.with_query_string("open-sesame")


if __name__ == '__main__':
    pages = []
    for line in fileinput.input():
        profile_id = line.strip("\n")
        checks.LOGGER.info("Profile: %s", profile_id) 

        # basic check on profile existence
        checks.API.profile(profile_id)

        # first page of annotations on the API
        checks.API.annotations(profile_id)

        pages.append((load.JournalProfile(JOURNAL, "/profiles/%s" % profile_id), 1))
    load_strategy = load.AllOf(pages)
    while True:
        try:
            load_strategy.run()
        except (AssertionError, RuntimeError, ValueError, checks.UnrecoverableError, requests.exceptions.ConnectionError) as e:
            load.LOGGER.exception("Error in loading (%s)", e.message)


