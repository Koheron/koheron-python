
.PHONY: test deploy clean_dist

test: test.py
	PYTEST_UNIXSOCK=/tmp/kserver_local.sock py.test -v test.py 
	
deploy: clean_dist
	python setup.py sdist bdist_wheel
	twine upload dist/*

clean_dist:
	rm -rf build
	rm -rf dist
	rm -rf koheron.egg-info