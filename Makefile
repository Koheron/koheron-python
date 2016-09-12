
TMP = tmp

SERVER_URL = https://github.com/Koheron/koheron-server.git
SERVER_BRANCH = master
SERVER_DIR = $(TMP)/koheron-server
SERVER_PYTEST = $(SERVER_DIR)/tests/tests.py
SERVER_BIN = $(SERVER_DIR)/tmp/kserverd
SERVER_VENV = $(SERVER_DIR)/koheron_server_venv

TEST_VENV = venv
PY2_VENV = $(TEST_VENV)/py2
PY3_VENV = $(TEST_VENV)/py3
TESTS_PY = ./tests.py

.PHONY: test test_common start_server deploy clean_dist clean_venv clean

# -------------------------------------------------------------------------------------
# Build and run koheron-server
# -------------------------------------------------------------------------------------

$(SERVER_DIR):
	git clone $(SERVER_URL) $(SERVER_DIR)
	cd $(SERVER_DIR) && git checkout $(SERVER_BRANCH)

$(SERVER_DIR)/requirements.txt: $(SERVER_DIR)

$(SERVER_VENV): $(SERVER_DIR)/requirements.txt
	virtualenv $(SERVER_VENV)
	$(SERVER_VENV)/bin/pip install -r $(SERVER_DIR)/requirements.txt

$(SERVER_BIN): $(SERVER_VENV)
	make -C $(SERVER_DIR) CONFIG=config/config_local.yaml PYTHON=koheron_server_venv/bin/python

start_server: $(SERVER_BIN)
	make -C $(SERVER_DIR) PYTHON=koheron_server_venv/bin/python start_server

# -------------------------------------------------------------------------------------
# Tests
# -------------------------------------------------------------------------------------

$(PY2_VENV): requirements.txt
	virtualenv $(PY2_VENV)
	$(PY2_VENV)/bin/pip install -r requirements.txt

$(PY3_VENV): requirements.txt
	virtualenv -p python3 $(PY3_VENV)
	$(PY3_VENV)/bin/pip3 install -r requirements.txt

$(TESTS_PY): $(SERVER_DIR)
	cp $(SERVER_PYTEST) $(TESTS_PY)

test: $(PY2_VENV) $(PY3_VENV) $(TESTS_PY)
	PYTEST_UNIXSOCK=/tmp/kserver_local.sock $(PY2_VENV)/bin/python -m pytest -v $(TESTS_PY)
	PYTEST_UNIXSOCK=/tmp/kserver_local.sock $(PY3_VENV)/bin/python3 -m pytest -v $(TESTS_PY)

test_common:
	python -m pytest -v tests_common.py
	python3 -m pytest -v tests_common.py
	cat server.log

# -------------------------------------------------------------------------------------
# Deploy
# -------------------------------------------------------------------------------------

deploy: clean_dist
	python setup.py sdist bdist_wheel
	twine upload -u $(PYPI_USERNAME) -p $(PYPI_PASSWORD) dist/*

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
	rm -f $(TESTS_PY)
