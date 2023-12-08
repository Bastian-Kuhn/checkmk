load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

HEIRLOOMMAILX_VERSION = "12.5"
def heirloommailx():
    http_archive(
        name = "heirloom-mailx",
        urls = [
            "https://ftp.nl.debian.org/debian-archive/debian/pool/main/h/heirloom-mailx/heirloom-mailx_" + HEIRLOOMMAILX_VERSION + ".orig.tar.gz",
            "https://artifacts.lan.tribe29.com/repository/upstream-archives/heirloom-mailx_" + HEIRLOOMMAILX_VERSION + ".orig.tar.gz",
        ],
        sha256 = "015ba4209135867f37a0245d22235a392b8bbed956913286b887c2e2a9a421ad",
        build_file = "@omd_packages//packages/heirloom-mailx:BUILD.bazel",
        patches = [
            '//packages/heirloom-mailx/patches:0001-nail-11.25-config.dif',
            '//packages/heirloom-mailx/patches:0002-mailx-12.3-pager.dif',
            '//packages/heirloom-mailx/patches:0003-mailx-12.5-lzw.dif',
            '//packages/heirloom-mailx/patches:0004-mailx-12.5-fname-null.dif',
            '//packages/heirloom-mailx/patches:0005-mailx-12.5-collect.dif',
            '//packages/heirloom-mailx/patches:0006-mailx-12.5-usage.dif',
            '//packages/heirloom-mailx/patches:0007-mailx-12.5-man-page-fixes.dif',
            '//packages/heirloom-mailx/patches:0008-mailx-12.5-outof-Introduce-expandaddr-flag.dif',
            '//packages/heirloom-mailx/patches:0009-mailx-12.5-fio.c-Unconditionally-require-wordexp-support.dif',
            '//packages/heirloom-mailx/patches:0010-mailx-12.5-globname-Invoke-wordexp-with-WRDE_NOCMD-CVE-2004-277.dif',
            '//packages/heirloom-mailx/patches:0011-mailx-12.5-unpack-Disable-option-processing-for-email-addresses.dif',
            '//packages/heirloom-mailx/patches:0012-mailx-12.5-empty-from.dif',
            '//packages/heirloom-mailx/patches:0013-mailx-12.5-nss-hostname-matching.dif',
            '//packages/heirloom-mailx/patches:0014-mailx-12.5-encsplit.dif',
            '//packages/heirloom-mailx/patches:0015-mailx-12.5-openssl.dif',
            '//packages/heirloom-mailx/patches:0016-mailx-12.5-no-SSLv3.dif',
            '//packages/heirloom-mailx/patches:0017-disable-ssl-and-kerberos.dif',
            '//packages/heirloom-mailx/patches:0018-dont-install-etc-files.dif',
        ],
        patch_args = ["-p1"],
        patch_tool = "patch",
        strip_prefix = "heirloom-mailx-" + HEIRLOOMMAILX_VERSION,
    )
