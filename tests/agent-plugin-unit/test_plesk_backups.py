#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys

import pytest


def test_import_module(capfd) -> None:  # type:ignore[no-untyped-def]
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        if sys.version_info[0] == 2:
            import agents.plugins.plesk_backups_2  # pylint: disable=syntax-error,unused-import  # noqa: F401
        else:
            import agents.plugins.plesk_backups  # pylint: disable=unused-import  # noqa: F401
    out, _ = capfd.readouterr()
    # PY2 vs PY3: No module named 'MySQLdb' vs No module named MySQLdb
    out = out.replace("'", "")
    assert (
        out
        == "<<<plesk_backups>>>\nNo module named MySQLdb. Please install missing module via pip install <module>."
    )
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 0
