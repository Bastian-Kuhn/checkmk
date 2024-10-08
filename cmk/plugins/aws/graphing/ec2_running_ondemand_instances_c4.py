#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import graphs, metrics, Title

UNIT_NUMBER = metrics.Unit(metrics.DecimalNotation(""), metrics.StrictPrecision(2))

metric_aws_ec2_running_ondemand_instances_c4_2xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c4.2xlarge",
    title=Title("Total running on-demand c4.2xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_YELLOW,
)

metric_aws_ec2_running_ondemand_instances_c4_4xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c4.4xlarge",
    title=Title("Total running on-demand c4.4xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_BLUE,
)

metric_aws_ec2_running_ondemand_instances_c4_8xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c4.8xlarge",
    title=Title("Total running on-demand c4.8xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.LIGHT_PURPLE,
)

metric_aws_ec2_running_ondemand_instances_c4_large = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c4.large",
    title=Title("Total running on-demand c4.large instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.ORANGE,
)

metric_aws_ec2_running_ondemand_instances_c4_xlarge = metrics.Metric(
    name="aws_ec2_running_ondemand_instances_c4.xlarge",
    title=Title("Total running on-demand c4.xlarge instances"),
    unit=UNIT_NUMBER,
    color=metrics.Color.DARK_YELLOW,
)

graph_aws_ec2_running_ondemand_instances_c4 = graphs.Graph(
    name="aws_ec2_running_ondemand_instances_c4",
    title=Title("Total running on-demand instances of type c4"),
    compound_lines=[
        "aws_ec2_running_ondemand_instances_c4.2xlarge",
        "aws_ec2_running_ondemand_instances_c4.4xlarge",
        "aws_ec2_running_ondemand_instances_c4.8xlarge",
        "aws_ec2_running_ondemand_instances_c4.large",
        "aws_ec2_running_ondemand_instances_c4.xlarge",
    ],
    optional=[
        "aws_ec2_running_ondemand_instances_c4.2xlarge",
        "aws_ec2_running_ondemand_instances_c4.4xlarge",
        "aws_ec2_running_ondemand_instances_c4.8xlarge",
        "aws_ec2_running_ondemand_instances_c4.large",
        "aws_ec2_running_ondemand_instances_c4.xlarge",
    ],
)
