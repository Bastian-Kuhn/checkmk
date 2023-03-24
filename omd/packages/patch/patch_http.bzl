load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

PATCH_VERSION = "2.7.6"

def patch():
    http_archive(
        name = "patch",
        urls = ["https://ftp.gnu.org/gnu/patch/patch-" + PATCH_VERSION + ".tar.gz", "https://fossies.org/linux/misc/patch-" + PATCH_VERSION + ".tar.xz"],
        sha256 = sha256,
        patches = [
                   '//packages/patch/patches:ed-style-01-missing-input-files.patch.dif',
                   '//packages/patch/patches:ed-style-02-fix-arbitrary-command-execution.patch.dif',
                   '//packages/patch/patches:ed-style-03-update-test-Makefile.patch.dif',
                   '//packages/patch/patches:ed-style-04-invoke-ed-directly.patch.dif',
                   '//packages/patch/patches:ed-style-05-minor-cleanups.patch.dif',
                   '//packages/patch/patches:ed-style-06-fix-test-failure.patch.dif',
                   '//packages/patch/patches:ed-style-07-dont-leak-tmp-file.patch.dif',
                   '//packages/patch/patches:ed-style-08-dont-leak-tmp-file-multi.patch.dif',
                   '//packages/patch/patches:fix-segfault-mangled-rename.patch.dif',
        ],
        patch_args = ["-p1"],
        patch_tool = "patch",
        build_file = '@omd_packages//packages/patch:BUILD.patch',
        strip_prefix = 'patch-' + PATCH_VERSION,
    )
