# elife-spectrum

Runs tests against eLife's projects from the one end of the spectrum to the other.

Coordination of tests in CI is tightly coupled to the 
[elife-alfred](https://github.com/elifesciences/elife-alfred-formula) and 
[elife-libraries](https://github.com/elifesciences/elife-libraries-formula) projects.

## Description

End-to-end testing in an infrastructure of microservices happens at the level above the individual service where *many* 
services exist. It is here real world user processes and the interactions between services are tested.

The most important process at eLife is publishing an article and ensuring it appears in all dependent services like the
journal, the search engine, metrics, reporting, buckets, archival, etc.

User interactions to drive the tests are simulated through the [input.py](./spectrum/input.py) module.

The various logic for checking API endpoints, polling and handling pagination are encapsulated in [checks.py](./spectrum.py).

The actual tests themselves live in the modules prefixed with `test_`, like [test_article.py](./spectrum/test_article.py),
and are executed by `pytest`. See below for options on running tests.

## Requirements

To run the tests from your local machine in the `continuumtest` environment, you need:

* [git-lfs](https://git-lfs.github.com/) to be installed to download the large `.tif` files.
* [docker](https://www.docker.com) and [docker-compose](https://docs.docker.com/compose/) to run [Selenium](http://www.seleniumframework.com)

and

* a configuration file '`app.cfg`' found on [elife-libraries](https://github.com/elifesciences/elife-libraries-formula) project instances. [Template here](https://github.com/elifesciences/builder-base-formula/blob/master/elife/config/srv-elife-spectrum-app.cfg).

The `app.cfg` file also contains credentials so you must already have permission to access `builder-private` at least, 
and understand the responsibilities of keeping any machines these credentials reside on secure.

## Usage

Publish and test a single, small article. Useful as a smoke test:

    ./execute-simplest-possible-tests.sh

Publish and test a single article from [spectrum/templates](spectrum/templates):

    ./execute-single-article.sh 15893

Publish and test everything:

    ./execute.sh

Publish and test everything marked with `continuum` (or other labels):

    ./execute.sh -m continuum

## Environment variable

- `SPECTRUM_PROCESSES` how many parallel processes to use to run tests (default 4).
- `SPECTRUM_TIMEOUT` how long to poll for a life sign before giving up with an exception.
- `SPECTRUM_ENVIRONMENT` which environment to run tests, either `end2end` (default) or `continuumtest'.

## Run "locally"

To update or develop new tests, you can run the Python testing framework locally, pointing it to a staging environment 
like `continuumtest` which is always available.

Install a virtual environment:

    ./install.sh
    source venv/bin/activate

Retrieve a configuration containing secrets to introspect into the environment to run commands and assertions:

    ./bldr download_file:elife-libraries--spectrum,/srv/elife-spectrum/app.cfg

You may want to edit the `[common]` section of `app.cfg` to point it to your own `/tmp` folder.

Run a test with:

```bash
export SPECTRUM_PROCESSES=1 # run tests serially
export SPECTRUM_ENVIRONMENT=continuumtest  # mandatory
export SPECTRUM_LOG_LEVEL=DEBUG  # more output
export SPECTRUM_TIMEOUT=60  # speeds up errors
python -m pytest -s spectrum/test_api.py
python -m pytest -s spectrum/test_article.py::test_article_multiple_ingests_of_the_same_version
```

See `example-local-test.sh`
