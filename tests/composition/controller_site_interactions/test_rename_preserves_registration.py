#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from tests.testlib.openapi_session import UnexpectedResponse
from tests.testlib.site import Site

from cmk.utils.type_defs import HostName

from .common import controller_status_json, register_controller


def _test_rename_preserves_registration(
    *,
    central_site: Site,
    registration_site: Site,
    agent_ctl: Path,
    hostname: HostName,
) -> None:
    response_create = central_site.openapi.create_host(
        hostname=hostname,
        attributes={
            "ipaddress": "127.0.0.1",
            "site": registration_site.id,
        },
    )
    central_site.openapi.activate_changes_and_wait_for_completion()
    register_controller(
        agent_ctl,
        registration_site,
        hostname,
    )

    new_hostname = HostName(f"{hostname}-renamed")
    response_rename = central_site.openapi.put(
        f"objects/host_config/{hostname}/actions/rename/invoke",
        headers={
            "If-Match": f'{response_create.headers["ETag"]}',
            "Content-Type": "application/json",
        },
        json={"new_name": new_hostname},
    )
    if not response_rename.ok:
        raise UnexpectedResponse.from_response(response_rename)
    central_site.openapi.activate_changes_and_wait_for_completion()

    controller_status = controller_status_json(agent_ctl)
    try:
        assert HostName(controller_status["connections"][0]["remote"]["host_name"]) == new_hostname
    except Exception as e:
        raise Exception(
            f"Checking if controller sees renaming failed. Status output:\n{controller_status}"
        ) from e


def test_rename_preserves_registration_central(
    central_site: Site,
    agent_ctl: Path,
) -> None:
    _test_rename_preserves_registration(
        central_site=central_site,
        registration_site=central_site,
        agent_ctl=agent_ctl,
        hostname=HostName("central"),
    )


def test_rename_preserves_registration_remote(
    central_site: Site,
    remote_site: Site,
    agent_ctl: Path,
) -> None:
    _test_rename_preserves_registration(
        central_site=central_site,
        registration_site=remote_site,
        agent_ctl=agent_ctl,
        hostname=HostName("remote"),
    )
