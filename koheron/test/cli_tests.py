#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import pytest
import click
from click.testing import CliRunner

from .. import cli

def test_sdk_install():
    runner = CliRunner()
    result = runner.invoke(cli.sdk, ['--path=/tmp/koheron', '--version=reorg_drivers', 'install'])
    assert result.exit_code == 0