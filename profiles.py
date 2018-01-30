from spectrum import load, input, checks
from sys import argv, exit
import fileinput
import requests

JOURNAL = checks.JOURNAL.with_resource_checking_method('head').with_query_string("open-sesame")


if __name__ == '__main__':
    api_checks = bool(argv[2]) if len(argv) > 2 else False
    limit = load.Limit(argv[3] if len(argv) > 3 else None)
    load.LOGGER.info("Setting iterations limit %s", limit)

    pages = []
    for line in fileinput.input():
        profile_id = line.strip("\n")
        checks.LOGGER.info("Profile: %s", profile_id) 
        if api_checks:
            # basic check on profile existence
            checks.API.profile(profile_id)
            # first page of annotations on the API
            annotations_response = checks.API.annotations(profile_id)
            checks.LOGGER.info("%s has %s annotations", profile_id, annotations_response['total'])

        pages.append((load.JournalProfile(JOURNAL, "/profiles/%s" % profile_id), 1))

    load_strategy = load.AllOf(pages)
    limit.run(load_strategy)


