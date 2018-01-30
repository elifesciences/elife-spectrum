from spectrum import load, input, checks
from sys import argv, exit
import fileinput
import requests

JOURNAL = checks.JOURNAL.with_resource_checking_method('get').with_query_string("open-sesame")


if __name__ == '__main__':
    limit = load.Limit(argv[1] if len(argv) > 1 else None)
    load.LOGGER.info("Setting iterations limit %s", limit)

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
    limit.run(load_strategy)


