#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable

import pytest

import cmk.utils.debug
from cmk.utils.type_defs import HostName, SectionName

from cmk.checkers import crash_reporting
from cmk.checkers.host_sections import HostSections
from cmk.checkers.type_defs import AgentRawDataSection

from cmk.base.agent_based.data_provider import SectionsParser
from cmk.base.api.agent_based.register.section_plugins import trivial_section_factory
from cmk.base.api.agent_based.type_defs import AgentParseFunction


def _section(name: str, parse_function: Callable) -> tuple[SectionName, AgentParseFunction]:
    """create a simple section for testing"""
    section = trivial_section_factory(SectionName(name))
    return section.name, parse_function


class TestSectionsParser:
    @pytest.fixture
    def sections_parser(self) -> SectionsParser:
        return SectionsParser(
            host_sections=HostSections[AgentRawDataSection](
                sections={
                    SectionName("one"): [],
                    SectionName("two"): [],
                }
            ),
            host_name=HostName("only-neede-for-crash-reporting"),
        )

    @staticmethod
    def test_parse_function_called_once(sections_parser: SectionsParser) -> None:
        counter = iter((1,))
        section_name, parse_function = _section("one", lambda x: next(counter))

        _ = sections_parser.parse(section_name, parse_function)
        parsing_result = sections_parser.parse(section_name, parse_function)

        assert parsing_result is not None
        assert parsing_result.data == 1

    @staticmethod
    def test_parsing_errors(  # type:ignore[no-untyped-def]
        monkeypatch, sections_parser: SectionsParser
    ) -> None:

        monkeypatch.setattr(
            crash_reporting,
            "create_section_crash_dump",
            lambda **kw: "crash dump msg",
        )
        # Debug mode raises instead of creating the crash report that we want here.
        cmk.utils.debug.disable()
        section_name, parse_function = _section("one", lambda x: 1 / 0)

        assert sections_parser.parse(section_name, parse_function) is None
        assert len(sections_parser.parsing_errors) == 1
        assert sections_parser.parsing_errors[0].startswith(
            "Parsing of section one failed - please submit a crash report! (Crash-ID: "
        )

    @staticmethod
    def test_parse(sections_parser: SectionsParser) -> None:
        parsed_data = object()
        section_name, parse_function = _section("one", lambda x: parsed_data)
        parsing_result = sections_parser.parse(section_name, parse_function)

        assert parsing_result is not None
        assert parsing_result.data is parsed_data
        assert parsing_result.cache_info is None

    @staticmethod
    def test_disable(sections_parser: SectionsParser) -> None:
        section_name, parse_function = _section("one", lambda x: 42)
        sections_parser.disable([section_name])

        assert sections_parser.parse(section_name, parse_function) is None

    @staticmethod
    def test_parse_missing_section(sections_parser: SectionsParser) -> None:
        section_name, parse_function = _section(
            "missing_section", lambda x: 42
        )  # function does not matter

        assert sections_parser.parse(section_name, parse_function) is None

    @staticmethod
    def test_parse_section_returns_none(sections_parser: SectionsParser) -> None:
        section_name, parse_function = _section("one", lambda x: None)

        assert sections_parser.parse(section_name, parse_function) is None
