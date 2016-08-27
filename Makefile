
TMP = tmp

SERVER_URL = https://github.com/Koheron/koheron-server.git
SERVER_BRANCH = master
SERVER_DIR = $(TMP)/koheron-server
SERVER_PYTEST = $(SERVER_DIR)/tests/tests.py
SERVER_BIN = $(SERVER_DIR)/tmp/kserverd
SERVER_VENV = $(SERVER_DIR)/koheron_server_venv

.PHONY: test test_common start_server deploy clean_dist clean

test: start_server
	cp $(SERVER_PYTEST) ./tests.py
	PYTEST_UNIXSOCK=/tmp/kserver_local.sock python -m pytest -v tests.py
	PYTEST_UNIXSOCK=/tmp/kserver_local.sock python3 -m pytest -v tests.py

test_common:
	python -m pytest -v tests_common.py
	python3 -m pytest -v tests_common.py
	cat server.log
	
deploy: clean_dist
	python setup.py sdist bdist_wheel
	twine upload dist/*

clean_dist:
	rm -rf build
	rm -rf dist
	rm -rf koheron.egg-info

clean: clean_dist
	rm -rf $(TMP)
	rm -f ./tests.py

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