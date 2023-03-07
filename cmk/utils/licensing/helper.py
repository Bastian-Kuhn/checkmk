#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import hashlib
import logging
from pathlib import Path
from uuid import UUID

import livestatus

from cmk.utils.paths import log_dir, omd_root


def init_logging() -> logging.Logger:
    formatter = logging.Formatter("%(asctime)s [%(levelno)s] [%(name)s %(process)d] %(message)s")

    handler = logging.FileHandler(filename=Path(log_dir, "licensing.log"), encoding="utf-8")
    handler.setFormatter(formatter)

    logger = logging.getLogger()
    del logger.handlers[:]  # Remove all previously existing handlers
    logger.addHandler(handler)

    return logger


def _get_instance_id_filepath() -> Path:
    return Path(omd_root, "etc/omd/instance_id")


def load_instance_id() -> UUID | None:
    try:
        with _get_instance_id_filepath().open("r", encoding="utf-8") as fp:
            return UUID(fp.read())
    except (FileNotFoundError, ValueError):
        return None


def hash_site_id(site_id: livestatus.SiteId) -> str:
    # We have to hash the site ID because some sites contain project names.
    # This hash also has to be constant because it will be used as an DB index.
    h = hashlib.new("sha256")
    h.update(str(site_id).encode("utf-8"))
    return h.hexdigest()


def rot47(input_str: str) -> str:
    return "".join(_rot47_char(c) for c in input_str)


def _rot47_char(c: str) -> str:
    ord_c = ord(c)
    return chr(33 + ((ord_c + 14) % 94)) if 33 <= ord_c <= 126 else c
