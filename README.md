# koheron-python

[![CircleCI](https://circleci.com/gh/Koheron/koheron-python.svg?style=shield)](https://circleci.com/gh/Koheron/koheron-python)
[![PyPI version](https://badge.fury.io/py/koheron.svg)](https://badge.fury.io/py/koheron)

Koheron Python Library

### Running tests

Testing server emission/reception:
```sh
make start-server
make test
```
This test runs locally and starts a server in background. The tests are run in virtualenvs (for Python 2 and 3). It takes some time to build then as they require Numpy to be install.

Testing `common`:
```sh
make NAME=oscillo HOST=192.168.1.100 test_common
```
Test common functionnalities on a remote host.