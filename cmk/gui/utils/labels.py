#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import enum
import json
from collections.abc import Iterable, Mapping
from typing import Literal, NamedTuple

from livestatus import LivestatusResponse, lqencode, quote_dict, SiteId

import cmk.gui.sites as sites
from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.type_defs import Sequence


class Label(NamedTuple):
    id: str
    value: str
    negate: bool


class LabelType(enum.StrEnum):
    HOST = "host"
    SERVICE = "service"
    ALL = "all"


Labels = Iterable[Label]

# Label group specific types
AndOrNotLiteral = Literal["and", "or", "not"]
LabelGroup = Sequence[tuple[AndOrNotLiteral, str]]
LabelGroups = Sequence[tuple[AndOrNotLiteral, LabelGroup]]

# Labels need to be in the format "<key>:<value>", e.g. "os:windows"
LABEL_REGEX = r"^[^:]+:[^:]+$"


class _LivestatusLabelResponse(NamedTuple):
    host_rows: LivestatusResponse
    service_rows: LivestatusResponse


class _MergedLabels(NamedTuple):
    hosts: dict[SiteId, dict[str, str]]
    services: dict[SiteId, dict[str, str]]


def parse_labels_value(value: str) -> Labels:
    try:
        decoded_labels = json.loads(value or "[]")
    except ValueError as e:
        raise MKUserError(None, _("Failed to parse labels: %s") % e)

    seen: set[str] = set()
    for entry in decoded_labels:
        label_id, label_value = (p.strip() for p in entry["value"].split(":", 1))
        if label_id in seen:
            raise MKUserError(
                None,
                _(
                    "A label key can be used only once per object. "
                    'The Label key "%s" is used twice.'
                )
                % label_id,
            )
        yield Label(label_id, label_value, False)
        seen.add(label_id)


def encode_label_for_livestatus(column: str, label: Label) -> str:
    """
    >>> encode_label_for_livestatus("labels", Label("key", "value", False))
    "Filter: labels = 'key' 'value'"
    """
    return "Filter: {} {} {} {}".format(
        lqencode(column),
        "!=" if label.negate else "=",
        lqencode(quote_dict(label.id)),
        lqencode(quote_dict(label.value)),
    )


def encode_labels_for_livestatus(
    column: str,
    labels: Labels,
) -> str:
    """
    >>> encode_labels_for_livestatus("labels", [Label("key", "value", False), Label("x", "y", False)])
    "Filter: labels = 'key' 'value'\\nFilter: labels = 'x' 'y'\\n"
    >>> encode_labels_for_livestatus("labels", [])
    ''
    """
    if headers := "\n".join(encode_label_for_livestatus(column, label) for label in labels):
        return headers + "\n"
    return ""


def encode_label_groups_for_livestatus(
    column: str,
    label_groups: LabelGroups,
) -> str:
    """
    >>> encode_labels_for_livestatus("labels", [Label("key", "value", False), Label("x", "y", False)])
    "Filter: labels = 'key' 'value'\\nFilter: labels = 'x' 'y'\\n"
    >>> encode_labels_for_livestatus("labels", [])
    ''
    """
    filter_str: str = ""
    is_first_group: bool = True
    group_operator: AndOrNotLiteral
    for group_operator, label_group in label_groups:
        is_first_label: bool = True
        label_operator: AndOrNotLiteral
        for label_operator, label in label_group:
            if not label:
                continue

            label_id, label_val = label.split(":")
            filter_str += (
                encode_label_for_livestatus(column, Label(label_id, label_val, False)) + "\n"
            )
            filter_str += _operator_filter_str(label_operator, is_first_label)
            is_first_label = False

        if not is_first_label:
            filter_str += _operator_filter_str(group_operator, is_first_group)
        is_first_group = False

    return filter_str


# Type of argument operator should be 'Operator'
def _operator_filter_str(operator: AndOrNotLiteral, is_first: bool) -> str:
    if is_first:
        if operator == "not":
            # Negate without And for the first element
            return "Negate:\n"
        # No filter str for and/or for the first element
        return ""
    if operator == "not":
        # Negate with And for non-first elements
        return "Negate:\nAnd: 2\n"
    # "And: 2\n" or "Or: 2\n"
    return f"{operator.title()}: 2\n"


def encode_labels_for_tagify(
    labels: Labels | Iterable[tuple[str, str]]
) -> Iterable[Mapping[str, str]]:
    """
    >>> encode_labels_for_tagify({"key": "value", "x": "y"}.items()) ==  encode_labels_for_tagify([Label("key", "value", False), Label("x", "y", False)])
    True
    """
    return [{"value": "%s:%s" % e[:2]} for e in labels]


def encode_labels_for_http(labels: Labels | Iterable[tuple[str, str]]) -> str:
    """The result can be used in building URLs
    >>> encode_labels_for_http([])
    '[]'
    >>> encode_labels_for_http({"key": "value", "x": "y"}.items())
    '[{"value": "key:value"}, {"value": "x:y"}]'
    """
    return json.dumps(encode_labels_for_tagify(labels))


def label_help_text() -> str:
    return _(
        "Labels need to be in the format <tt>[KEY]:[VALUE]</tt>. For example <tt>cmk/os_family:linux</tt>."
    )


def get_labels_from_config(label_type: LabelType, search_label: str) -> Sequence[tuple[str, str]]:
    # TODO: Until we have a config specific implementation we now use the labels known to the
    # core. This is not optimal, but better than doing nothing.
    # To implement a setup specific search, we need to decide which occurrences of labels we
    # want to search: hosts / folders, rules, ...?
    return get_labels_from_core(label_type, search_label)


def get_labels_from_core(
    label_type: LabelType, search_label: str | None = None
) -> Sequence[tuple[str, str]]:
    all_labels = _get_labels_from_livestatus(label_type)
    if search_label is None:
        return list(all_labels)
    return [
        (ident, value) for ident, value in all_labels if search_label in ":".join([ident, value])
    ]


def _get_labels_from_livestatus(
    label_type: LabelType,
) -> set[tuple[str, str]]:
    if label_type == LabelType.HOST:
        query = "GET hosts\nCache: reload\nColumns: labels\n"
    elif label_type == LabelType.SERVICE:
        query = "GET services\nCache: reload\nColumns: labels\n"
    elif label_type == LabelType.ALL:
        query = "GET labels\nCache: reload\nColumns: name value\n"
    else:
        raise ValueError("Unsupported livestatus query")

    try:
        sites.live().set_auth_domain("labels")
        with sites.only_sites(list(user.authorized_sites().keys())):
            label_rows = sites.live().query(query)
    finally:
        sites.live().set_auth_domain("read")

    if label_type == LabelType.ALL:
        return set((str(label[0]), str(label[1])) for label in label_rows)

    return set((k, v) for row in label_rows for labels in row for k, v in labels.items())
