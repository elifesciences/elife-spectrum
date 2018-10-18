from __future__ import absolute_import
import os
from pprint import pformat
from urlparse import urlparse

import polling
from requests.exceptions import ConnectionError

from spectrum import debug
from spectrum.exceptions import TimeoutError


GLOBAL_TIMEOUT = int(os.environ['SPECTRUM_TIMEOUT']) if 'SPECTRUM_TIMEOUT' in os.environ else 600

def poll(action_fn, error_message, *error_message_args):
    """
    Poll until action_fn returns something truthy. After GLOBAL_TIMEOUT throw an exception.

    action_fn may return:
    - a tuple: first element is a result (truthy or falsy), second element any detail
    - any other type: truthy or falsy decides whether the polling has been successful or not

    error_message may be:
    - a string to be formatted with error_message_args
    - a callable returning such a string"""
    details = {'last_seen': None}
    def wrapped_action_fn():
        possible_result = action_fn()
        if isinstance(possible_result, tuple) and len(possible_result) == 2:
            details['last_seen'] = possible_result[1]
            return possible_result[0]
        else:
            return possible_result
    try:
        return polling.poll(
            wrapped_action_fn,
            timeout=GLOBAL_TIMEOUT,
            step=5
        )
    except polling.TimeoutException:
        if callable(error_message):
            error_message_template = error_message()
        else:
            error_message_template = error_message
        built_error_message = error_message_template % tuple(error_message_args)
        if 'last_seen' in details:
            built_error_message = built_error_message + "\n" + pformat(details['last_seen'])
            if isinstance(details['last_seen'], ConnectionError):
                host = urlparse(details['last_seen'].request.url).netloc
                built_error_message = built_error_message + ("\nHost: %s" % host)
                built_error_message = built_error_message + ("\nIp: %s" % debug.get_host_ip(host))
        raise TimeoutError.giving_up_on(built_error_message)
