
.PHONY: test test_common deploy clean_dist

test: test.py
	PYTEST_UNIXSOCK=/tmp/kserver_local.sock py.test -v test.py

test_common:
	py.test -v tests_common.py
	
deploy: clean_dist
	python setup.py sdist bdist_wheel
	twine upload dist/*

clean_dist:
	rm -rf build
	rm -rf dist
	rm -rf koheron.egg-info