from argparse import ArgumentParser
from spectrum import load, input, checks
from sys import argv, exit
import fileinput
import requests

JOURNAL = checks.JOURNAL.with_resource_checking_method('head').with_query_string("open-sesame")

def check_api(profile_ids):
    for profile_id in profile_ids:
        # basic check on profile existence
        checks.API.profile(profile_id)
        # first page of annotations on the API
        annotations_response = checks.API.annotations(profile_id)
        checks.LOGGER.info("%s has %s annotations", profile_id, annotations_response['total'])

def check_journal(profile_ids, limit):
    pages = [(load.JournalProfile(JOURNAL, "/profiles/%s" % profile_id), 1) for profile_id in profile_ids]
    load_strategy = load.AllOf(pages)
    limit.run(load_strategy)


if __name__ == '__main__':
    parser = ArgumentParser(description="Load tests profiles and annotations, data and pages")
    parser.add_argument('profile_ids', type=str, help='File from which to read profile ids')
    parser.add_argument('--check', choices=['api', 'journal'], default='journal', help='Which service to run checks on')
    parser.add_argument('--limit', type=int, default=None, help='The maximum number of checks to make before stopping. Only applicable for journal')
    arguments = parser.parse_args()
    limit = load.Limit(arguments.limit)
    load.LOGGER.info("Setting iterations limit %s", limit)

    profile_ids = []
    for line in fileinput.input(arguments.profile_ids):
        profile_id = line.strip("\n")
        checks.LOGGER.info("Profile: %s", profile_id) 
        profile_ids.append(profile_id)

    if arguments.check == 'api':
        check_api(profile_ids)
    if arguments.check == 'journal':
        check_journal(profile_ids, limit)

