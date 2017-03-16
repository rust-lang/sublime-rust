"""Tests to exercise the on-save syntax checking.

This currently runs on Rust 1.15.
"""


import re
from rust_test_common import *


class TestSyntaxCheck(TestBase):

    def test_messages(self):
        """Test message generation.

        Each of the listed files has comments that annotate where a message
        should appear. The carets in front indicate the number of lines above
        the comment where the last line of the message is.  This allows for
        multiple messages to be on the same line.  For example:
            // ^ERR expected 1 parameter
            // ^^ERR this function takes 1 parameter

        These tests are somewhat fragile, as new versions of Rust change the
        formatting of messages.  Hopefully these examples are relatively
        stable for now.
        """
        self.rustc_version = util.get_rustc_version(sublime.active_window(),
                                                    plugin_path)

        to_test = [
            'multi-targets/src/lib.rs',
            'multi-targets/src/lmod1.rs',
            'multi-targets/src/altmain.rs',
            'multi-targets/tests/common/helpers.rs',
            'error-tests/benches/bench_err.rs',
            # "children" without spans
            'error-tests/tests/arg-count-mismatch.rs',
            # "children" with spans
            'error-tests/tests/binop-mul-bool.rs',
            # This is currently broken (-Zno-trans does not produce errors).
            # 'error-tests/tests/const-err.rs',
            # Macro-expansion test.
            'error-tests/tests/dead-code-ret.rs',
            # "code" test
            'error-tests/tests/E0005.rs',
            # unicode in JSON
            'error-tests/tests/test_unicode.rs',
            # message with suggestion
            'error-tests/tests/cast-to-unsized-trait-object-suggestion.rs',
            # error in a cfg(test) section
            'error-tests/src/lib.rs',
            # Workspace tests.
            'workspace/workspace1/src/lib.rs',
            'workspace/workspace1/src/anothermod/mod.rs',
            'workspace/workspace2/src/lib.rs',
            'workspace/workspace2/src/somemod.rs',
        ]
        for path in to_test:
            path = os.path.join('tests', path)
            self._with_open_file(path, self._test_messages)

    def _test_messages(self, view):
        # Trigger the generation of messages.
        phantoms = []
        regions = []

        def collect_phantoms(v, key, region, content, layout, on_navigate):
            if v == view:
                phantoms.append((region, content))

        def collect_regions(v, key, regions, scope, icon, flags):
            if v == view:
                regions.extend(regions)

        m = plugin.rust.messages
        orig_add_phantom = m._sublime_add_phantom
        orig_add_regions = m._sublime_add_regions
        m._sublime_add_phantom = collect_phantoms
        m._sublime_add_regions = collect_regions
        try:
            self._test_messages2(view, phantoms, regions)
        finally:
            m._sublime_add_phantom = orig_add_phantom
            m._sublime_add_regions = orig_add_regions

    def _test_messages2(self, view, phantoms, regions):
        e = plugin.SyntaxCheckPlugin.RustSyntaxCheckEvent()
        # Force Cargo to recompile.
        self._cargo_clean(view)
        # os.utime(view.file_name())  1 second resolution is not enough
        e.on_post_save(view)
        # Wait for it to finish.
        self._get_rust_thread().join()
        pattern = '(\^+)(WARN|ERR|HELP|NOTE)(\([^)]+\))? (.+)'
        expected_messages = view.find_all(pattern)
        for emsg_r in expected_messages:
            row, col = view.rowcol(emsg_r.begin())
            text = view.substr(emsg_r)
            m = re.match(pattern, text)
            line_offset = len(m.group(1))
            msg_row = row - line_offset
            msg_type = m.group(2)
            msg_type_text = {
                'WARN': 'warning',
                'ERR': 'error',
                'NOTE': 'note',
                'HELP': 'help',
            }[msg_type]
            semver = m.group(3)
            msg_content = m.group(4)
            if not semver or \
                    plugin.rust.semver.match(self.rustc_version, semver[1:-1]):
                for i, (region, content) in enumerate(phantoms):
                    # python 3.4 can use html.unescape()
                    content = content.replace('&nbsp;', ' ')\
                                     .replace('&amp;', '&')\
                                     .replace('&lt;', '<')\
                                     .replace('&gt;', '>')
                    r_row, r_col = view.rowcol(region.end())
                    print('Checking for %r in %r' % (msg_content, content))
                    if r_row == msg_row and msg_content in content:
                        self.assertIn(msg_type_text, content)
                        break
                else:
                    raise AssertionError('Did not find expected message "%s:%s" on line %r for file %r' % (
                        msg_type, msg_content, msg_row, view.file_name()))
                del phantoms[i]
        if len(phantoms):
            raise AssertionError('Got extra phantoms for %r: %r' % (view.file_name(), phantoms))
