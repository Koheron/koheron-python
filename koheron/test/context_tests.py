
import sys
import os
import pytest
import re

sys.path = [".."] + sys.path
from koheron import KoheronClient, command, __version__

class UsesContext:
    def __init__(self, client):
        self.client = client

    @command()
    def set_float_from_tests(self, f):
        return self.client.recv_bool()

    @command()
    def is_myself(self):
        return self.client.recv_bool()

port = int(os.getenv('PYTEST_PORT', '36000'))

client = KoheronClient('127.0.0.1', port)
uses_ctx = UsesContext(client)

@pytest.mark.parametrize('uses_ctx', [uses_ctx])
def test_set_float_from_tests(uses_ctx):
    assert uses_ctx.set_float_from_tests(12.5)

@pytest.mark.parametrize('uses_ctx', [uses_ctx])
def test_is_myself(uses_ctx):
    assert uses_ctx.is_myself()