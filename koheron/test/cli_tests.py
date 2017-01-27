#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import pytest
import click
from click.testing import CliRunner

from .. import cli
from ..version import __version__

# Server

def test_version():
    runner = CliRunner()
    result = runner.invoke(cli.cli, ['version'])
    assert result.exit_code == 0
    assert result.output == '{}\n'.format(__version__)

def test_devices():
    runner = CliRunner()
    result = runner.invoke(cli.cli, ['--host=127.0.0.1', 'devices'])
    assert result.exit_code == 0
    assert result.output == "{u'Tests': 2, u'UsesContext': 5, u'ExceptionTests': 4, u'KServer': 1, u'Benchmarks': 3}\n"

# SDK

def test_sdk_install():
    path = '/tmp/koheron'
    version = 'develop'
    runner = CliRunner()
    result = runner.invoke(cli.sdk, ['--path=' + path, '--version=' + version, 'install'])
    assert result.exit_code == 0
    assert result.output == 'Koheron SDK version {} successfully installed at {}.\n'.format(version, path)
    assert os.path.exists(path)
    # Check proper cleaning of temporary install files
    assert not os.path.exists('/tmp/koheron-sdk.zip')
    assert not os.path.exists('/tmp/koheron-sdk-tmp')
