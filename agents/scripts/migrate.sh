#!/bin/sh
# Copyright (C) 2024 Checkmk GmbH - License: Checkmk Enterprise License
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

: "${MK_INSTALLDIR:=""}"
: "${OLD_MK_VARDIR:="/var/lib/check_mk_agent"}"
: "${OLD_HOMEDIR:="/var/lib/cmk-agent"}"

usage() {
    cat >&2 <<HERE
Usage: ${0}
Do necessary migration steps that are not covered by normal package manager mechanisms on agent update
HERE
    exit 1
}

main() {
    [ -n "${MK_INSTALLDIR}" ] && migrate_runtime_dir "${OLD_MK_VARDIR}" "${MK_INSTALLDIR}/runtime"
    [ -n "${MK_INSTALLDIR}" ] && migrate_controller_registration "${OLD_HOMEDIR}" "${MK_INSTALLDIR}/runtime/controller"
}

migrate_runtime_dir() {
    old_runtime_dir="$1"
    new_runtime_dir="$2"

    [ -e "${old_runtime_dir}" ] && [ -e "${new_runtime_dir}" ] && [ "${old_runtime_dir}" != "${new_runtime_dir}" ] && {
        printf "Found runtime directory from previous agent installation at %s, migrating all runtime files to %s\n" "${old_runtime_dir}" "${new_runtime_dir}"
        mv -f "${old_runtime_dir}"/* "${new_runtime_dir}"
        rm -r "${old_runtime_dir}"
    }
}

migrate_controller_registration() {
    old_homedir="$1"
    new_homedir="$2"
    old_registry="${old_homedir}/registered_connections.json"
    new_registry="${new_homedir}/registered_connections.json"
    [ -e "${old_registry}" ] && [ ! -e "${new_registry}" ] && {
        printf "Found agent controller registered connections at legacy home directory %s, migrating to %s.\n" "${old_homedir}" "${new_homedir}"
        mv "${old_registry}" "${new_homedir}"
        rm -r "${old_homedir}"
    }
}

main "$@"
