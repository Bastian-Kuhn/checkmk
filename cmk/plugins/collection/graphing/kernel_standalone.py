#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))

metric_process_creations = metrics.Metric(
    name="process_creations",
    title=Title("Process creations"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.ORANGE,
)

metric_context_switches = metrics.Metric(
    name="context_switches",
    title=Title("Context switches"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.LIGHT_GREEN,
)
