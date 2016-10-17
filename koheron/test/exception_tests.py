# Exception tests
# A new session is opened and closed for each test since
# they missread the reception buffer.

import os
import sys
import pytest

sys.path = [".."] + sys.path
from koheron import KoheronClient, command, ConnectionError

class ExceptionTests:
    def __init__(self, client):
        self.client = client

    @command()
    def ret_type_exception(self):
        return self.client.recv_uint32() # Instead of bool

    @command(funcname='ret_type_exception')
    def ret_type_exception_tuple(self):
        return self.client.recv_tuple('II') # Instead of bool

    @command(funcname='ret_type_exception')
    def ret_type_exception_string(self):
        return self.client.recv_string() # Instead of bool

    @command()
    def std_vector_exception(self):
        return self.client.recv_vector(dtype='float32') # Instead of uint32

    @command()
    def std_array_type_exception(self):
        return self.client.recv_array(shape=10, dtype='uint32') # Instead of float

    @command()
    def std_array_size_exception(self):
        return self.client.recv_array(shape=20, dtype='float32') # Instead of 10

    @command()
    def std_tuple_exception(self):
        return self.client.recv_uint32() # Instead of tuple

port = int(os.getenv('PYTEST_PORT', '36000'))

def test_tcp_connect_fail_exception():
    with pytest.raises(ConnectionError) as excinfo:
        client = KoheronClient('127.0.0.1', 3600) # Instead of 36000
    assert str(excinfo.value) == 'Failed to connect to 127.0.0.1:3600 : [Errno 111] Connection refused'

def test_unix_connect_fail_exception():
    with pytest.raises(ConnectionError) as excinfo:
        client = KoheronClient(unixsock='dummy/path')
    assert str(excinfo.value) == 'Failed to connect to unix socket address dummy/path'

@pytest.mark.parametrize('port', [port])
def test_invalid_number_arguments_exception(port):
    client = KoheronClient('127.0.0.1', port)
    tests = ExceptionTests(client)
    with pytest.raises(ValueError) as excinfo:
        tests.ret_type_exception(42) # Musn't take a parameter
    assert str(excinfo.value) == 'Invalid number of arguments. Expected 0 but received 1.'

@pytest.mark.parametrize('port', [port])
def test_ret_type_exception(port):
    client = KoheronClient('127.0.0.1', port)
    tests = ExceptionTests(client)
    with pytest.raises(TypeError) as excinfo:
        tests.ret_type_exception()
    assert str(excinfo.value) == 'ExceptionTests::ret_type_exception returns a bool.'

@pytest.mark.parametrize('port', [port])
def test_ret_type_exception_tuple(port):
    client = KoheronClient('127.0.0.1', port)
    tests = ExceptionTests(client)
    with pytest.raises(TypeError) as excinfo:
        tests.ret_type_exception_tuple()
    assert str(excinfo.value) == 'ExceptionTests::ret_type_exception returns a bool not a std::tuple.'

@pytest.mark.parametrize('port', [port])
def test_ret_type_exception_string(port):
    client = KoheronClient('127.0.0.1', port)
    tests = ExceptionTests(client)
    with pytest.raises(TypeError) as excinfo:
        tests.ret_type_exception_string()
    assert str(excinfo.value) == 'ExceptionTests::ret_type_exception returns a bool.'

@pytest.mark.parametrize('port', [port])
def test_std_vector_exception(port):
    client = KoheronClient('127.0.0.1', port)
    tests = ExceptionTests(client)
    with pytest.raises(TypeError) as excinfo:
        tests.std_vector_exception()
    assert str(excinfo.value) == 'ExceptionTests::std_vector_exception expects elements of type uint32_t.'

@pytest.mark.parametrize('port', [port])
def test_std_array_type_exception(port):
    client = KoheronClient('127.0.0.1', port)
    tests = ExceptionTests(client)
    with pytest.raises(TypeError) as excinfo:
        tests.std_array_type_exception()
    assert str(excinfo.value) == 'ExceptionTests::std_array_type_exception expects elements of type float.'

@pytest.mark.parametrize('port', [port])
def test_std_array_size_exception(port):
    client = KoheronClient('127.0.0.1', port)
    tests = ExceptionTests(client)
    with pytest.raises(ValueError) as excinfo:
        tests.std_array_size_exception()
    assert str(excinfo.value) == 'ExceptionTests::std_array_size_exception expects 10 elements.'

@pytest.mark.parametrize('port', [port])
def test_std_tuple_exception(port):
    client = KoheronClient('127.0.0.1', port)
    tests = ExceptionTests(client)
    with pytest.raises(TypeError) as excinfo:
        tests.std_tuple_exception()
    assert str(excinfo.value) == 'ExceptionTests::std_tuple_exception returns a std::tuple<unsigned int, float>.'
