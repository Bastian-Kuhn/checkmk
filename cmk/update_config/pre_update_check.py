#!/usr/bin/env python3
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
""" Pre update checks, executed before any configuration is changed. """

import sys
import traceback
from typing import Literal

from cmk.utils import paths
from cmk.utils.packaging import (
    disable,
    Installer,
    PackageName,
    PackagePart,
    PackageVersion,
    PathConfig,
)
from cmk.utils.packaging._reporter import files_inventory

# It's OK to import centralized config load logic
import cmk.ec.export as ec  # pylint: disable=cmk-module-layer-violation

from cmk.gui import main_modules
from cmk.gui.exceptions import MKUserError
from cmk.gui.session import SuperUserContext
from cmk.gui.utils import get_failed_plugins
from cmk.gui.utils.script_helpers import gui_context
from cmk.gui.watolib.hosts_and_folders import disable_redis
from cmk.gui.watolib.rulesets import RulesetCollection
from cmk.gui.wsgi.blueprints.global_vars import set_global_vars

from cmk.update_config.plugins.actions.rulesets import AllRulesets


def passed_pre_checks(
    conflict_mode: Literal["ask", "install", "keepold", "abort"],
) -> bool:
    return _all_ui_extensions_compatible(conflict_mode) and _all_rulesets_compatible(conflict_mode)


def _all_rulesets_compatible(
    conflict_mode: Literal["ask", "install", "keepold", "abort"],
) -> bool:
    try:
        with disable_redis(), gui_context(), SuperUserContext():
            set_global_vars()
            rulesets = AllRulesets.load_all_rulesets()
    except Exception:
        if conflict_mode in ["install", "keepold"] or (
            conflict_mode == "ask"
            and input(
                "Unknown exception while trying to load rulesets.\n"
                "Error: %s\n\n"
                "You can abort the update process (A) and try to fix "
                "the incompatibilities or try to continue the update (c).\n"
                "Abort update? [A/c]\n" % traceback.format_exc()
            ).lower()
            in ["c", "continue"]
        ):
            return True
        return False

    with disable_redis(), gui_context(), SuperUserContext():
        set_global_vars()
        result = _validate_rule_values(rulesets, conflict_mode)

    return result


def _validate_rule_values(
    all_rulesets: RulesetCollection,
    conflict_mode: Literal["ask", "install", "keepold", "abort"],
) -> bool:
    rulesets_skip = {
        # the valid choices for this ruleset are user-dependent (SLAs) and not even an admin can
        # see all of them
        "extra_service_conf:_sla_config",
    }

    for ruleset in all_rulesets.get_rulesets().values():
        if ruleset.name in rulesets_skip:
            continue

        for folder, index, rule in ruleset.get_rules():
            try:
                ruleset.rulespec.valuespec.validate_value(
                    rule.value,
                    "",
                )
            except MKUserError as excpt:
                if conflict_mode in ["install", "keepold"] or (
                    conflict_mode == "ask"
                    and input(
                        "WARNING: Invalid rule configuration detected\n"
                        "Ruleset: %s\n"
                        "Title: %s\n"
                        "Folder: %s\n"
                        "Rule nr: %s\n"
                        "Exception: %s\n\n"
                        "You can abort the update process (A) and "
                        "try to fix the incompatibilities with a downgrade "
                        "to the version you came from or continue the update.\n"
                        "Abort update? [A/c]\n"
                        % (
                            ruleset.name,
                            ruleset.title(),
                            folder.path() if folder.path() else "main",
                            index + 1,
                            excpt,
                        )
                    ).lower()
                    in ["c", "continue"]
                ):
                    return True
                return False
    return True


def _all_ui_extensions_compatible(
    conflict_mode: Literal["ask", "install", "keepold", "abort"],
) -> bool:
    main_modules.load_plugins()
    installer = Installer(paths.installed_packages_dir)
    path_config = PathConfig(
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
    for mkp in files_inventory(installer, path_config):
        # mkp package file
        if not mkp["part_id"]:
            continue

        for file, error in get_failed_plugins():
            file_path = (
                str(path_config.get_path(PackagePart(mkp["part_id"]))) + "/" + str(mkp["file"])
            )
            if file_path == file:
                # unpackaged files
                if not (package_name := mkp["package"]):
                    if conflict_mode in ["install", "keepold"] or (
                        conflict_mode == "ask"
                        and input(
                            "Incompatible local file '%s'.\n"
                            "Error: %s\n\n"
                            "You can abort the update process (A) and try to fix "
                            "the incompatibilities or continue the update (c).\n\n"
                            "Abort the update process? [A/c] \n" % (mkp["file"], error)
                        ).lower()
                        in ["c", "continue"]
                    ):
                        continue
                    return False

                if conflict_mode in ["install", "keepold"] or (
                    conflict_mode == "ask"
                    and input(
                        "Incompatible file '%s' of extension package '%s'\n"
                        "Error: %s\n\n"
                        "You can abort the update process (A) or disable the "
                        "extension package (d) and continue the update process.\n"
                        "Abort the update process? [A/d] \n" % (mkp["file"], package_name, error),
                    ).lower()
                    in ["d", "disable"]
                ):
                    disable(
                        installer,
                        path_config,
                        PackageName(mkp["package"]),
                        PackageVersion(mkp["version"]),
                    )
                    sys.stdout.write("Disabled extension package: %s" % package_name)
                else:
                    return False
    return True
