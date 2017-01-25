#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import pytest
import click
from click.testing import CliRunner

from .. import cli

def test_sdk_install():
    path = '/tmp/koheron'
    version = 'reorg_drivers'
    runner = CliRunner()
    result = runner.invoke(cli.sdk, ['--path=' + path, '--version=' + version, 'install'])
    assert result.exit_code == 0
    assert result.output == 'Koheron SDK version {} successfully installed at {}.\n'.format(version, path)