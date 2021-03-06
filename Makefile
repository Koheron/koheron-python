
TMP = tmp
TEST_VENV = venv
PY2_VENV = $(TEST_VENV)/py2
PY3_VENV = $(TEST_VENV)/py3
TESTS_PY = koheron/test/tests.py koheron/test/exception_tests.py koheron/test/context_tests.py koheron/test/cli_tests.py

PYPI_VERSION=$(shell curl -s 'https://pypi.python.org/pypi/koheron/json'| PYTHONIOENCODING=utf8 python -c "import sys, json; print json.load(sys.stdin)['info']['version']")
CURRENT_VERSION=$(shell python -c "from koheron.version import __version__; print(__version__)")

.PHONY: test test_common deploy clean_dist clean_venv clean

# -------------------------------------------------------------------------------------
# Provides start_koheron_server and stop_koheron_server targets
# -------------------------------------------------------------------------------------

KOHERON_SERVER_DEST=$(TMP)
KOHERON_SERVER_BRANCH = v0.13.0

KOHERON_SERVER_MK=build_run.mk
DUMMY:=$(shell curl https://raw.githubusercontent.com/Koheron/koheron-server/$(KOHERON_SERVER_BRANCH)/scripts/build_run.mk > $(KOHERON_SERVER_MK))
include $(KOHERON_SERVER_MK)

# -------------------------------------------------------------------------------------
# Tests
# -------------------------------------------------------------------------------------

$(PY2_VENV): requirements.txt
	test -d $(PY2_VENV) || (virtualenv $(PY2_VENV) && \
	                        $(PY2_VENV)/bin/pip install -r requirements.txt && \
	                        $(PY2_VENV)/bin/pip install numpy==1.11.1 pytest)

$(PY3_VENV): requirements.txt
	test -d $(PY3_VENV) || (virtualenv -p python3 $(PY3_VENV) && \
	                        $(PY3_VENV)/bin/pip3 install -r requirements.txt && \
	                        $(PY3_VENV)/bin/pip3 install numpy==1.11.1 pytest)

test: $(PY2_VENV) $(PY3_VENV) $(TESTS_PY)
	PYTEST_UNIXSOCK=/tmp/kserver_local.sock $(PY2_VENV)/bin/python -m pytest -v $(TESTS_PY)
	PYTEST_UNIXSOCK=/tmp/kserver_local.sock $(PY3_VENV)/bin/python3 -m pytest -v $(TESTS_PY)

test_common:
	$(PY2_VENV)/bin/python -m pytest -v koheron/test/test_common.py
	$(PY3_VENV)/bin/python3 -m pytest -v koheron/test/test_common.py

# -------------------------------------------------------------------------------------
# Deploy
# -------------------------------------------------------------------------------------

deploy: clean_dist $(PY2_VENV)
	@echo PYPI_VERSION = $(PYPI_VERSION)
	# @echo CURRENT_VERSION = $(CURRENT_VERSION)
ifneq ($(PYPI_VERSION),$(shell $(PY2_VENV)/bin/python -c "from koheron.version import __version__; print(__version__)"))
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
