
TMP = tmp

TCP_SERVER_URL = https://github.com/Koheron/koheron-server.git
TCP_SERVER_DIR = $(TMP)/koheron-server
TCP_SERVER = $(TCP_SERVER_DIR)/tmp/kserverd
TCP_SERVER_BRANCH = master
SERVER_CONFIG = config/config_local.yaml

.PHONY: test test_common start_server_local deploy clean_dist clean

test: test.py start_server_local
	PYTEST_UNIXSOCK=/tmp/kserver_local.sock py.test -v test.py

test_common:
	$(TCP_SERVER) -c config/kserver_local.conf
	py.test -v tests_common.py
	cat server.log

start_server_local: $(TCP_SERVER)
	nohup $(TCP_SERVER) -c $(TCP_SERVER_DIR)/config/kserver_local.conf > /dev/null 2> server.log &
	
deploy: clean_dist
	python setup.py sdist bdist_wheel
	twine upload dist/*

clean_dist:
	rm -rf build
	rm -rf dist
	rm -rf koheron.egg-info

clean: clean_dist
	rm -rf $(TMP)

$(TCP_SERVER_DIR):
	git clone $(TCP_SERVER_URL) $(TCP_SERVER_DIR)
	cd $(TCP_SERVER_DIR) && git checkout $(TCP_SERVER_SHA)

$(TCP_SERVER): $(TCP_SERVER_DIR)
	make -C $(TCP_SERVER_DIR) CONFIG=$(SERVER_CONFIG)