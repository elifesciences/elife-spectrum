"""
    Settings for eLife Spectrum
    ~~~~~~~~~~~
    To specify multiple environments, each environment gets its own class,
    and calling get_settings will return the specified class that contains
    the settings.

    You must modify:
        aws_access_key_id
        aws_secret_access_key
"""

class end2end():
    aws_access_key_id = ""
    aws_secret_access_key = ""
    bucket_input = 'end2end-elife-production-final'
    bucket_eif = 'end2end-elife-publishing-eif'
    # ...
    # see https://github.com/elifesciences/elife-alfred-formula/blob/master/salt/elife-alfred/config/srv-elife-spectrum-settings.py for a complete list

def get_settings(env="end2end"):
    """
    Returns the settings class based on the environment type provided,
    by default use the end2end environment settings
    """
    return eval(env)
