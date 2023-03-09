#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import json
import logging
import random
import time
from collections import defaultdict, deque
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import auto, Enum
from pathlib import Path
from typing import Any, NamedTuple, TypedDict

import livestatus

import cmk.utils.store as store
import cmk.utils.version as cmk_version
from cmk.utils.licensing.export import (
    LicenseUsageExtensions,
    LicenseUsageReportVersion,
    LicenseUsageReportVersionError,
    LicenseUsageSample,
    RawLicenseUsageExtensions,
    RawLicenseUsageSample,
)
from cmk.utils.licensing.helper import hash_site_id, init_logging, load_instance_id, rot47
from cmk.utils.paths import licensing_dir
from cmk.utils.site import omd_site

CLOUD_SERVICE_PREFIXES = {"aws", "azure", "gcp"}


class RawLicenseUsageReport(TypedDict):
    VERSION: str
    history: list[RawLicenseUsageSample]


#   .--update--------------------------------------------------------------.
#   |                                   _       _                          |
#   |                   _   _ _ __   __| | __ _| |_ ___                    |
#   |                  | | | | '_ \ / _` |/ _` | __/ _ \                   |
#   |                  | |_| | |_) | (_| | (_| | ||  __/                   |
#   |                   \__,_| .__/ \__,_|\__,_|\__\___|                   |
#   |                        |_|                                           |
#   '----------------------------------------------------------------------'

_LICENSE_LABEL_NAME = "cmk/licensing"
_LICENSE_LABEL_EXCLUDE = "excluded"


def try_update_license_usage(logger: logging.Logger) -> None:
    """Update the license usage history

    If a sample could not be created (due to livestatus errors) then the update process will be
    skipped. This is important for checking the mtime of the history file during activate changes.

    The history has a max. length of 400 (days)."""
    sample = _create_sample()

    report_filepath = get_license_usage_report_filepath()
    licensing_dir.mkdir(parents=True, exist_ok=True)
    next_run_filepath = licensing_dir / "next_run"

    with store.locked(next_run_filepath), store.locked(report_filepath):
        now = datetime.now()

        if now.timestamp() < _get_next_run_ts(next_run_filepath):
            return

        history = load_license_usage_history(report_filepath)
        history.add_sample(sample)
        _save_license_usage_report(
            report_filepath,
            RawLicenseUsageReport(
                VERSION=LicenseUsageReportVersion,
                history=history.for_report(),
            ),
        )

        store.save_text_to_file(next_run_filepath, rot47(str(_create_next_run_ts(now))))


def _create_sample() -> LicenseUsageSample:
    if not (instance_id := load_instance_id()):
        raise ValueError()

    sample_time = int(
        datetime.utcnow()
        .replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
        .timestamp()
    )

    hosts_counter = _get_hosts_counter()
    shadow_hosts_counter = _get_shadow_hosts_counter()
    services_counter = _get_services_counter()
    cloud_counter = _get_cloud_counter()

    general_infos = cmk_version.get_general_version_infos()
    extensions = _load_extensions()

    return LicenseUsageSample(
        instance_id=instance_id,
        site_hash=hash_site_id(omd_site()),
        version=cmk_version.omd_version(),
        edition=general_infos["edition"],
        platform=general_infos["os"],
        is_cma=cmk_version.is_cma(),
        num_hosts=hosts_counter.included,
        num_hosts_cloud=cloud_counter.hosts,
        num_hosts_excluded=hosts_counter.excluded,
        num_shadow_hosts=shadow_hosts_counter,
        num_services=services_counter.included,
        num_services_cloud=cloud_counter.services,
        num_services_excluded=services_counter.excluded,
        sample_time=sample_time,
        timezone=time.localtime().tm_zone,
        extension_ntop=extensions.ntop,
    )


class EntityCounter(NamedTuple):
    included: int
    excluded: int


@dataclass
class CCECounter:
    hosts: int
    services: int


def _get_hosts_counter() -> EntityCounter:
    included_num_hosts, excluded_num_hosts = _get_stats_from_livestatus(
        (
            "GET hosts\n"
            "Stats: host_labels != '{label_name}' '{label_value}'\n"
            "Stats: host_labels = '{label_name}' '{label_value}'\n"
        ).format(
            label_name=_LICENSE_LABEL_NAME,
            label_value=_LICENSE_LABEL_EXCLUDE,
        )
    )

    return EntityCounter(
        included=included_num_hosts,
        excluded=excluded_num_hosts,
    )


def _get_shadow_hosts_counter() -> int:
    "Shadow objects: 0: active, 1: passive, 2: shadow"
    return int(livestatus.LocalConnection().query("GET hosts\nStats: check_type = 2")[0][0])


def _get_services_counter() -> EntityCounter:
    included_num_services, excluded_num_services = _get_stats_from_livestatus(
        (
            "GET services\n"
            "Stats: host_labels != '{label_name}' '{label_value}'\n"
            "Stats: service_labels != '{label_name}' '{label_value}'\n"
            "StatsAnd: 2\n"
            "Stats: host_labels = '{label_name}' '{label_value}'\n"
            "Stats: service_labels = '{label_name}' '{label_value}'\n"
            "StatsOr: 2\n"
        ).format(
            label_name=_LICENSE_LABEL_NAME,
            label_value=_LICENSE_LABEL_EXCLUDE,
        )
    )

    return EntityCounter(
        included=included_num_services,
        excluded=excluded_num_services,
    )


def _get_from_livestatus(query: str) -> Sequence[Sequence[Any]]:
    return livestatus.LocalConnection().query(query)


def _get_stats_from_livestatus(query: str) -> tuple[int, int]:
    stats = _get_from_livestatus(query)[0]
    return int(stats[0]), int(stats[1])


def _get_services_from_livestatus() -> Sequence[Sequence[Any]]:
    query_table = "services"
    query_columns = "host_name service_check_command"
    query = (
        f"GET {query_table}"
        f"\nColumns: {query_columns}"
        f"\nFilter: host_labels != '{_LICENSE_LABEL_NAME}' '{_LICENSE_LABEL_EXCLUDE}'"
        f"\nFilter: service_labels != '{_LICENSE_LABEL_NAME}' '{_LICENSE_LABEL_EXCLUDE}'"
    )
    return _get_from_livestatus(query)


def _parse_services_livestatus_response(response: Sequence[Sequence[Any]]) -> CCECounter:
    def contains_cloud_service(services: Sequence[str]) -> bool:
        return any(service.startswith(tuple(CLOUD_SERVICE_PREFIXES)) for service in services)

    services_per_host = defaultdict(list)
    for result in response:
        services_per_host[result[0]].append(result[1].removeprefix("check_mk-"))

    cloud_services = {
        host: len(services)
        for host, services in services_per_host.items()
        if contains_cloud_service(services)
    }
    return CCECounter(hosts=len(cloud_services), services=sum(cloud_services.values()))


def _get_cloud_counter() -> CCECounter:
    response = _get_services_from_livestatus()
    return _parse_services_livestatus_response(response)


def _get_next_run_ts(next_run_filepath: Path) -> int:
    return int(rot47(store.load_text_from_file(next_run_filepath, default="_")))


def _create_next_run_ts(now: datetime) -> int:
    """The next run time is randomly set to the next day between 8 am and 4 pm."""
    eight_am_tdy = datetime(now.year, now.month, now.day, 8, 0, 0)
    start = eight_am_tdy + timedelta(days=1)
    end = start + timedelta(hours=8)
    return random.randrange(int(start.timestamp()), int(end.timestamp()), 600)


def get_license_usage_report_filepath() -> Path:
    return licensing_dir / "history.json"


def _save_license_usage_report(report_filepath: Path, raw_report: RawLicenseUsageReport) -> None:
    store.save_bytes_to_file(
        report_filepath,
        _serialize_dump(raw_report),
    )


def load_license_usage_history(report_filepath: Path) -> LocalLicenseUsageHistory:
    if not isinstance(
        raw_report := deserialize_dump(
            store.load_bytes_from_file(
                report_filepath,
                default=b"{}",
            )
        ),
        dict,
    ):
        raise TypeError()

    if not raw_report.get("history"):
        return LocalLicenseUsageHistory([])

    return LocalLicenseUsageHistory.parse(raw_report, hash_site_id(omd_site()))


# .
#   .--history-------------------------------------------------------------.
#   |                   _     _     _                                      |
#   |                  | |__ (_)___| |_ ___  _ __ _   _                    |
#   |                  | '_ \| / __| __/ _ \| '__| | | |                   |
#   |                  | | | | \__ \ || (_) | |  | |_| |                   |
#   |                  |_| |_|_|___/\__\___/|_|   \__, |                   |
#   |                                             |___/                    |
#   '----------------------------------------------------------------------'


class LocalLicenseUsageHistory:
    def __init__(self, iterable: Iterable[LicenseUsageSample]) -> None:
        self._samples = deque(iterable, maxlen=400)

    def __iter__(self) -> Iterator[LicenseUsageSample]:
        return iter(self._samples)

    def __len__(self) -> int:
        return len(self._samples)

    @property
    def last(self) -> LicenseUsageSample | None:
        return self._samples[0] if self._samples else None

    def for_report(self) -> list[RawLicenseUsageSample]:
        return [sample.for_report() for sample in self._samples]

    @classmethod
    def parse(cls, raw_report: object, site_hash: str) -> LocalLicenseUsageHistory:
        if not isinstance(raw_report, dict):
            raise TypeError()

        if not raw_report:
            return cls([])

        if not isinstance(version := raw_report.get("VERSION"), str):
            raise LicenseUsageReportVersionError()

        parser = LicenseUsageSample.get_parser(version)
        instance_id = load_instance_id()
        return cls(
            parser(raw_sample, instance_id=instance_id, site_hash=site_hash)
            for raw_sample in raw_report.get("history", [])
        )

    def add_sample(self, sample: LicenseUsageSample) -> None:
        self._samples.appendleft(sample)


# .
#   .--extensions----------------------------------------------------------.
#   |                      _                 _                             |
#   |             _____  _| |_ ___ _ __  ___(_) ___  _ __  ___             |
#   |            / _ \ \/ / __/ _ \ '_ \/ __| |/ _ \| '_ \/ __|            |
#   |           |  __/>  <| ||  __/ | | \__ \ | (_) | | | \__ \            |
#   |            \___/_/\_\\__\___|_| |_|___/_|\___/|_| |_|___/            |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def _get_extensions_filepath() -> Path:
    return licensing_dir / "extensions.json"


def save_extensions(extensions: LicenseUsageExtensions) -> None:
    licensing_dir.mkdir(parents=True, exist_ok=True)
    extensions_filepath = _get_extensions_filepath()

    with store.locked(extensions_filepath):
        store.save_bytes_to_file(
            extensions_filepath,
            _serialize_dump(extensions.for_report()),
        )


def _load_extensions() -> LicenseUsageExtensions:
    extensions_filepath = _get_extensions_filepath()
    with store.locked(extensions_filepath):
        raw_extensions = deserialize_dump(
            store.load_bytes_from_file(
                extensions_filepath,
                default=b"{}",
            )
        )
    return LicenseUsageExtensions.parse(raw_extensions)


# .
#   .--helper--------------------------------------------------------------.
#   |                    _          _                                      |
#   |                   | |__   ___| |_ __   ___ _ __                      |
#   |                   | '_ \ / _ \ | '_ \ / _ \ '__|                     |
#   |                   | | | |  __/ | |_) |  __/ |                        |
#   |                   |_| |_|\___|_| .__/ \___|_|                        |
#   |                                |_|                                   |
#   '----------------------------------------------------------------------'


def _serialize_dump(dump: RawLicenseUsageReport | RawLicenseUsageExtensions) -> bytes:
    return rot47(json.dumps(dump)).encode("utf-8")


def deserialize_dump(raw_dump: bytes) -> object:
    dump_str = rot47(raw_dump.decode("utf-8"))

    try:
        dump = json.loads(dump_str)
    except json.decoder.JSONDecodeError:
        return {}

    if isinstance(dump, dict):
        return dump

    return {}


class LicenseUsageReportValidity(Enum):
    older_than_five_days = auto()
    older_than_three_days = auto()
    recent_enough = auto()


def get_license_usage_report_validity() -> LicenseUsageReportValidity:
    report_filepath = get_license_usage_report_filepath()

    with store.locked(report_filepath):
        if report_filepath.stat().st_size == 0:
            try_update_license_usage(init_logging())
            return LicenseUsageReportValidity.recent_enough

        age = time.time() - report_filepath.stat().st_mtime
        if age >= 432000:
            # crit if greater than five days: block activate changes
            return LicenseUsageReportValidity.older_than_five_days

        if age >= 259200:
            # warn if greater than three days: warn during activating changes
            return LicenseUsageReportValidity.older_than_three_days

    return LicenseUsageReportValidity.recent_enough
