#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Mapping
from typing import NamedTuple

import cmk.utils.paths
from cmk.utils.auto_queue import AutoQueue
from cmk.utils.log import console
from cmk.utils.structured_data import StructuredDataNode, TreeOrArchiveStore, UpdateResult
from cmk.utils.type_defs import (
    EVERYTHING,
    HostName,
    HWSWInventoryParameters,
    InventoryPluginName,
    SectionName,
)

from cmk.checkers import FetcherFunction, ParserFunction, SummarizerFunction
from cmk.checkers.checkresults import ActiveCheckResult

from cmk.base.api.agent_based.inventory_classes import InventoryPlugin
from cmk.base.api.agent_based.type_defs import SectionPlugin
from cmk.base.config import ConfigCache

from ._inventory import check_inventory_tree

__all__ = ["execute_active_check_inventory"]


def execute_active_check_inventory(
    host_name: HostName,
    *,
    config_cache: ConfigCache,
    fetcher: FetcherFunction,
    parser: ParserFunction,
    summarizer: SummarizerFunction,
    section_plugins: Mapping[SectionName, SectionPlugin],
    inventory_plugins: Mapping[InventoryPluginName, InventoryPlugin],
    inventory_parameters: Callable[[HostName, InventoryPlugin], dict[str, object]],
    parameters: HWSWInventoryParameters,
) -> ActiveCheckResult:
    tree_or_archive_store = TreeOrArchiveStore(
        cmk.utils.paths.inventory_output_dir,
        cmk.utils.paths.inventory_archive_dir,
    )
    old_tree = tree_or_archive_store.load(host_name=host_name)

    result = check_inventory_tree(
        host_name,
        fetcher=fetcher,
        parser=parser,
        summarizer=summarizer,
        config_cache=config_cache,
        inventory_parameters=inventory_parameters,
        section_plugins=section_plugins,
        inventory_plugins=inventory_plugins,
        run_plugin_names=EVERYTHING,
        parameters=parameters,
        old_tree=old_tree,
    )

    if result.no_data_or_files:
        AutoQueue(cmk.utils.paths.autoinventory_dir).add(host_name)

    if not (result.processing_failed or result.no_data_or_files):
        save_tree_actions = _get_save_tree_actions(
            old_tree=old_tree,
            inventory_tree=result.inventory_tree,
            update_result=result.update_result,
        )
        if save_tree_actions.do_remove:
            tree_or_archive_store.remove(host_name=host_name)
        # The order of archive or save is important:
        if save_tree_actions.do_archive:
            tree_or_archive_store.archive(host_name=host_name)
        if save_tree_actions.do_save:
            tree_or_archive_store.save(host_name=host_name, tree=result.inventory_tree)

    return result.check_result


class _SaveTreeActions(NamedTuple):
    do_remove: bool
    do_archive: bool
    do_save: bool


def _get_save_tree_actions(
    *,
    old_tree: StructuredDataNode,
    inventory_tree: StructuredDataNode,
    update_result: UpdateResult,
) -> _SaveTreeActions:
    if inventory_tree.is_empty():
        # Remove empty inventory files. Important for host inventory icon
        console.verbose("No inventory tree.\n")
        return _SaveTreeActions(do_remove=True, do_archive=False, do_save=False)

    if old_tree.is_empty():
        console.verbose("New inventory tree.\n")
        return _SaveTreeActions(do_remove=False, do_archive=False, do_save=True)

    if has_changed := (not old_tree.is_equal(inventory_tree)):
        console.verbose("Inventory tree has changed. Add history entry.\n")

    if update_result.save_tree:
        console.verbose(f"Updated inventory tree ({update_result.reason or ''}).\n")

    return _SaveTreeActions(
        do_remove=False,
        do_archive=has_changed,
        do_save=(has_changed or update_result.save_tree),
    )
