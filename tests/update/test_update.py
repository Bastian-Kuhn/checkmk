#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
from pathlib import Path

from faker import Faker

from tests.testlib.site import Site
from tests.testlib.utils import current_base_branch_name
from tests.testlib.version import CMKVersion, version_from_env

from tests.composition.controller_site_interactions.common import (
    register_controller,
    wait_until_host_receives_data,
)

from cmk.utils.version import Edition

from .conftest import (
    get_host_data,
    get_services_with_status,
    get_site_status,
    logger_services_crit,
    logger_services_ok,
    logger_services_warn,
    reschedule_services,
    update_config,
    update_site,
)

logger = logging.getLogger(__name__)


def test_update(test_setup: tuple[Site, bool], agent_ctl: Path) -> None:
    test_site, interactive_mode = test_setup
    base_version = test_site.version

    # create a new host and perform a service discovery
    hostname = f"test-update-{Faker().first_name()}"
    logger.info("Creating new host: %s", hostname)

    test_site.openapi.create_host(
        hostname=hostname,
        attributes={
            "ipaddress": "127.0.0.1",
            "tag_criticality": "test",
        },
        bake_agent=True,
    )
    test_site.activate_changes_and_wait_for_core_reload()

    register_controller(agent_ctl, test_site, hostname)
    wait_until_host_receives_data(test_site, hostname)

    logger.info("Discovering services and waiting for completion...")
    test_site.openapi.discover_services_and_wait_for_completion(
        hostname, cmk_version=base_version.version
    )
    test_site.openapi.activate_changes_and_wait_for_completion()
    reschedule_services(test_site, hostname)

    # get baseline monitoring data
    base_data_host = get_host_data(test_site, hostname)

    # TODO: 'Interface 2' service is not found after the update. Investigate: CMK-13495
    interface_2_service = "Interface 2"
    if interface_2_service in base_data_host:
        base_data_host.pop("Interface 2")

    base_ok_services = get_services_with_status(base_data_host, "OK")
    base_pend_services = get_services_with_status(base_data_host, "PEND")
    base_warn_services = get_services_with_status(base_data_host, "WARN")
    base_crit_services = get_services_with_status(base_data_host, "CRIT")

    assert len(base_ok_services) > 0
    assert len(base_pend_services) == 0

    logger_services_ok("base", base_ok_services)
    if len(base_warn_services) > 0:
        logger_services_warn("base", base_warn_services)
    if len(base_crit_services) > 0:
        logger_services_crit("base", base_crit_services)

    target_version = version_from_env(
        fallback_version_spec=CMKVersion.DAILY,
        fallback_edition=Edition.CEE,
        fallback_branch=current_base_branch_name(),
    )

    target_site = update_site(test_site, target_version, interactive=interactive_mode)

    # Triggering cmk config update
    update_config_result = update_config(target_site)

    assert update_config_result == 0, "Updating the configuration failed unexpectedly!"

    # get the service status codes and check them
    assert get_site_status(target_site) == "running", "Invalid service status after updating!"

    logger.info("Successfully tested updating %s>%s!", base_version.version, target_version.version)

    logger.info("Discovering services and waiting for completion...")
    target_site.openapi.discover_services_and_wait_for_completion(hostname)
    target_site.openapi.activate_changes_and_wait_for_completion()
    reschedule_services(target_site, hostname)

    # get update monitoring data
    target_data_host = get_host_data(target_site, hostname)

    target_ok_services = get_services_with_status(target_data_host, "OK")
    target_pend_services = get_services_with_status(target_data_host, "PEND")
    target_warn_services = get_services_with_status(target_data_host, "WARN")
    target_crit_services = get_services_with_status(target_data_host, "CRIT")

    assert len(target_pend_services) == 0

    logger_services_ok("target", target_ok_services)
    if len(target_warn_services) > 0:
        logger_services_warn("target", target_warn_services)
    if len(target_crit_services) > 0:
        logger_services_crit("target", target_crit_services)

    err_msg = (
        f"The following services were found in base-version but not in target-version: "
        f"{[service for service in base_data_host if service not in target_data_host]}"
    )
    assert len(target_data_host) >= len(base_data_host), err_msg

    err_msg = (
        f"The following services were `OK` in base-version but not in target-version: "
        f"{[service for service in base_ok_services if service not in target_ok_services]}"
    )
    assert set(base_ok_services).issubset(set(target_ok_services)), err_msg
