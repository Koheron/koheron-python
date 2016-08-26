
TMP = tmp

SERVER_URL = https://github.com/Koheron/koheron-server.git
SERVER_BRANCH = master
SERVER_DIR = $(TMP)/koheron-server
SERVER_BIN = $(SERVER_DIR)/tmp/kserverd
SERVER_VENV = $(SERVER_DIR)/koheron_server_venv

.PHONY: test test_common run_server_local deploy clean_dist clean

test: test.py run_server_local
	PYTEST_UNIXSOCK=/tmp/kserver_local.sock python -m pytest -v test.py

test_common:
	py.test -v tests_common.py
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

run_server_local: $(SERVER_BIN)
	nohup $(SERVER_BIN) -c $(SERVER_DIR)/config/kserver_local.conf > /dev/null 2> server.log &