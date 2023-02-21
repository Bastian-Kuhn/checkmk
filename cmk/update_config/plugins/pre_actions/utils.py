#!/usr/bin/env python3
# Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum
import sys
from pathlib import Path

from cmk.utils import paths
from cmk.utils.packaging import disable, Installer, PackageID, PathConfig

# It's OK to import centralized config load logic
import cmk.ec.export as ec  # pylint: disable=cmk-module-layer-violation

_PATH_CONFIG = PathConfig(
    local_root=paths.local_root,
    mkp_rule_pack_dir=ec.mkp_rule_pack_dir(),
    agent_based_plugins_dir=paths.local_agent_based_plugins_dir,
    checks_dir=paths.local_checks_dir,
    inventory_dir=paths.local_inventory_dir,
    check_manpages_dir=paths.local_check_manpages_dir,
    agents_dir=paths.local_agents_dir,
    notifications_dir=paths.local_notifications_dir,
    gui_plugins_dir=paths.local_gui_plugins_dir,
    web_dir=paths.local_web_dir,
    pnp_templates_dir=paths.local_pnp_templates_dir,
    doc_dir=paths.local_doc_dir,
    locale_dir=paths.local_locale_dir,
    bin_dir=paths.local_bin_dir,
    lib_dir=paths.local_lib_dir,
    mib_dir=paths.local_mib_dir,
    alert_handlers_dir=paths.local_alert_handlers_dir,
)


class ConflictMode(enum.StrEnum):
    ASK = "ask"
    INSTALL = "install"
    KEEP_OLD = "keepold"
    ABORT = "abort"


def disable_incomp_mkp(
    conflict_mode: ConflictMode,
    module_name: str,
    error: BaseException,
    package_id: PackageID,
    installer: Installer,
) -> bool:
    if conflict_mode in (ConflictMode.INSTALL, ConflictMode.KEEP_OLD) or (
        conflict_mode is ConflictMode.ASK
        and input(
            "Incompatible file '%s' of extension package '%s %s'\n"
            "Error: %s\n\n"
            "You can abort the update process (A) or disable the "
            "extension package (d) and continue the update process.\n"
            "Abort the update process? [A/d] \n"
            % (module_name, package_id.name, package_id.version, error),
        ).lower()
        in ["d", "disable"]
    ):
        disable(
            installer,
            _PATH_CONFIG,
            package_id.name,
            package_id.version,
        )
        sys.stdout.write(
            "Disabled extension package: %s %s\n" % (package_id.name, package_id.version)
        )
        return True
    return False


def continue_on_incomp_local_file(
    conflict_mode: ConflictMode,
    module_name: str,
    error: BaseException,
) -> bool:
    if conflict_mode in (ConflictMode.INSTALL, ConflictMode.KEEP_OLD) or (
        conflict_mode is ConflictMode.ASK
        and input(
            "Incompatible local file '%s'.\n"
            "Error: %s\n\n"
            "You can abort the update process (A) and try to fix "
            "the incompatibilities or continue the update (c).\n\n"
            "Abort the update process? [A/c] \n" % (module_name, error)
        ).lower()
        in ["c", "continue"]
    ):
        return True
    return False


def get_installer_and_package_map() -> tuple[Installer, dict[Path, PackageID]]:
    installer = Installer(paths.installed_packages_dir)
    installed_files_package_map = {
        Path(_PATH_CONFIG.get_path(part)).resolve() / file: manifest.id
        for manifest in installer.get_installed_manifests()
        for part, files in manifest.files.items()
        for file in files
    }
    return installer, installed_files_package_map
