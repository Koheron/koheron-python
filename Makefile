
TMP = tmp
TEST_VENV = venv
PY2_VENV = $(TEST_VENV)/py2
PY3_VENV = $(TEST_VENV)/py3
TESTS_PY = koheron/test/tests.py koheron/test/exception_tests.py

PYPI_VERSION=$(shell curl -s 'https://pypi.python.org/pypi/koheron/json'| PYTHONIOENCODING=utf8 python -c "import sys, json; print json.load(sys.stdin)['info']['version']")
CURRENT_VERSION=$(shell python -c "from koheron.version import __version__; print(__version__)")

.PHONY: test test_common deploy clean_dist clean_venv clean

# -------------------------------------------------------------------------------------
# Provides start_koheron_server and stop_koheron_server targets
# -------------------------------------------------------------------------------------

KOHERON_SERVER_DEST=$(TMP)
ifndef KOHERON_SERVER_BRANCH
KOHERON_SERVER_BRANCH=master
endif
KOHERON_SERVER_MK=build_run.mk
DUMMY:=$(shell curl https://raw.githubusercontent.com/Koheron/koheron-server/$(KOHERON_SERVER_BRANCH)/scripts/build_run.mk > $(KOHERON_SERVER_MK))
include $(KOHERON_SERVER_MK)

# -------------------------------------------------------------------------------------
# Tests
# -------------------------------------------------------------------------------------

$(PY2_VENV): requirements.txt
	test -d $(PY2_VENV) || (virtualenv $(PY2_VENV) && $(PY2_VENV)/bin/pip install -r requirements.txt)

$(PY3_VENV): requirements.txt
	test -d $(PY3_VENV) || (virtualenv -p python3 $(PY3_VENV) && $(PY3_VENV)/bin/pip3 install -r requirements.txt)

test: $(PY2_VENV) $(PY3_VENV) $(TESTS_PY)
	PYTEST_UNIXSOCK=/tmp/kserver_local.sock $(PY2_VENV)/bin/python -m pytest -v $(TESTS_PY)
	PYTEST_UNIXSOCK=/tmp/kserver_local.sock $(PY3_VENV)/bin/python3 -m pytest -v $(TESTS_PY)

test_common:
	python -m pytest -v koheron/test/test_common.py
	python3 -m pytest -v koheron/test/test_common.py
	cat server.log

# -------------------------------------------------------------------------------------
# Deploy
# -------------------------------------------------------------------------------------

deploy: clean_dist
	@echo PYPI_VERSION = $(PYPI_VERSION)
	@echo CURRENT_VERSION = $(CURRENT_VERSION)
ifneq ($(PYPI_VERSION),$(CURRENT_VERSION))
	python setup.py sdist bdist_wheel
	twine upload -u $(PYPI_USERNAME) -p $(PYPI_PASSWORD) dist/*
endif

# -------------------------------------------------------------------------------------
# Clean
# -------------------------------------------------------------------------------------

clean_dist:
	rm -rf build
	rm -rf dist
	rm -rf koheron.egg-info

clean_venv:
	rm -rf $(TEST_VENV)

clean: clean_dist
	rm -rf $(TMP)
	rm -f $(KOHERON_SERVER_MK)
