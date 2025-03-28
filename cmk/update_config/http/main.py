#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
import dataclasses
import sys

import pydantic

from cmk.utils.redis import disable_redis

from cmk.gui.main_modules import load_plugins
from cmk.gui.session import SuperUserContext
from cmk.gui.utils import gen_id
from cmk.gui.utils.script_helpers import gui_context
from cmk.gui.watolib.rulesets import AllRulesets, Rule, Ruleset
from cmk.gui.wsgi.blueprints.global_vars import set_global_vars

from cmk.update_config.http.conflicts import detect_conflicts, MigratableValue
from cmk.update_config.http.migrate import migrate


class Args(pydantic.BaseModel):
    write: bool = False


def parse_arguments() -> Args:
    parser = argparse.ArgumentParser(prog="cmk-migrate-http")
    subparser = parser.add_subparsers(dest="command", required=True)

    parser_migrate = subparser.add_parser("migrate", help="Migrate command")
    parser_migrate.add_argument("--write", action="store_true", help="persist changes on disk")
    return Args.model_validate(vars(parser.parse_args()))


def _new_migrated_rules(ruleset_v1: Ruleset, ruleset_v2: Ruleset) -> None:
    for folder, rule_index, rule_v1 in ruleset_v1.get_rules():
        if _migrated_rule(rule_v1.id, ruleset_v2) is None:
            value = detect_conflicts(rule_v1.value)
            sys.stdout.write(f"Rule: {folder}, {rule_index}\n")
            if not isinstance(value, MigratableValue):
                sys.stdout.write(f"Can't migrate: {value.type_}\n")
                continue
            sys.stdout.write("Migrated, new.\n")
            rule_v2 = _migrated_rule(rule_v1.id, ruleset_v2)
            rule_v2 = _construct_v2_rule(rule_v1, value, ruleset_v2)
            ruleset_v2.append_rule(rule_v1.folder, rule_v2)


def _overwrite_migrated_rules(ruleset_v1: Ruleset, ruleset_v2: Ruleset) -> None:
    for folder, rule_index, rule_v2 in ruleset_v2.get_rules():
        if "from_v1" in rule_v2.value:
            sys.stdout.write(f"Overwriting rule: {folder}, {rule_index}\n")
            rule_v1 = _from_v1(rule_v2.value["from_v1"], ruleset_v1)
            if rule_v1 is None:
                sys.stdout.write("Deleted, v1 counter-part no longer exits.\n")
                ruleset_v2.delete_rule(rule_v2)
                continue
            conflict = detect_conflicts(rule_v1.value)
            if not isinstance(conflict, MigratableValue):
                sys.stdout.write("Deleted, v1 counter-part no longer migratable.\n")
                ruleset_v2.delete_rule(rule_v2)
                continue
            sys.stdout.write("Migrated, edited exiting rule.\n")
            new_rule_v2 = rule_v2.clone(preserve_id=True)
            new_rule_v2.value = migrate(rule_v1.id, rule_v1.value)
            ruleset_v2.edit_rule(rule_v2, new_rule_v2)


def _from_v1(rule_v1_id: str, ruleset_v1: Ruleset) -> Rule | None:
    for _folder, _rule_index, rule_v1 in ruleset_v1.get_rules():
        if rule_v1_id == rule_v1.id:
            return rule_v1
    return None


def _migrated_rule(rule_v1_id: str, ruleset_v2: Ruleset) -> Rule | None:
    for _folder, _rule_index, rule_v2 in ruleset_v2.get_rules():
        if rule_v2.value.get("from_v1") == rule_v1_id:
            return rule_v2
    return None


def _construct_v2_rule(rule_v1: Rule, value: MigratableValue, ruleset_v2: Ruleset) -> Rule:
    new_rule_value = migrate(rule_v1.id, rule_v1.value)
    return Rule(
        id_=gen_id(),
        folder=rule_v1.folder,
        ruleset=ruleset_v2,
        conditions=rule_v1.conditions.clone(),
        options=dataclasses.replace(rule_v1.rule_options, disabled=True),
        value=new_rule_value,
        locked_by=None,
    )


def main() -> None:
    args = parse_arguments()
    load_plugins()
    with disable_redis(), gui_context(), SuperUserContext():
        set_global_vars()
        all_rulesets = AllRulesets.load_all_rulesets()
        ruleset_v1 = all_rulesets.get("active_checks:http")
        ruleset_v2 = all_rulesets.get("active_checks:httpv2")
        _overwrite_migrated_rules(ruleset_v1, ruleset_v2)
        _new_migrated_rules(ruleset_v1, ruleset_v2)
        if args.write:
            all_rulesets.save()


if __name__ == "__main__":
    main()
