# elife-spectrum
Runs tests agains eLife's projects from the one end of the spectrum to the other.

## Requirements

Requires the [https://git-lfs.github.com/](git-lfs) extension to be able to download the large `.tif` files.

Requires an `app.cfg` file to be provided, see [https://github.com/elifesciences/elife-alfred-formula](elife-alfred-formula).

## Usage

```
./execute-simplest-possible-tests.sh
```
publishes and tests a single, small article. Useful as a smoke test.

```
./execute-single-article.sh 15893
```
publishes and tests a single article from [spectrum/templates](spectrum/templates).

```
./execute.sh
```
publishes and tests everything.

```
./execute.sh -m continuum
```
publishes and tests everything marked with `continuum` or other labels.


## Environment variable

- `SPECTRUM_PROCESSES` how many parallel processes to use to run tests.
- `SPECTRUM_TIMEOUT` how much polling has to wait for a life sign before giving up with an exception.
- `SPECTRUM_ENVIRONMENT` which environment to run tests in e.g. `end2end` (default) or `continuumtest'.

## Run "locally"

To update or develop new tests, you can run the Python testing framework locally, pointing it to a staging environment like `continuumtest` which is always available.

Install a virtual environment:

```
./install.sh
source venv/bin/activate
```

Retrieve a configuration containing secrets to introspect into the environment to run commands and assertions:

```
scp elife@alfred.elifesciences.org:/srv/elife-spectrum/app.cfg .
```

You may want to edit the `[common]` section of `app.cfg` to point it to your own `/tmp` folder.

Run a test with:
```
export SPECTRUM_ENVIRONMENT=continuumtest  # mandatory
export SPECTRUM_LOG_LEVEL=DEBUG  # more output
export SPECTRUM_TIMEOUT=60  # speeds up errors
python -m pytest -s spectrum/test_api.py
python -m pytest -s spectrum/test_article.py::test_article_multiple_ingests_of_the_same_version
```
