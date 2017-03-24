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
