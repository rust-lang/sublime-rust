"""Tests to exercise the on-save syntax checking.

This currently runs on Rust 1.15.
"""


import re
from rust_test_common import *


class TestSyntaxCheck(TestBase):

    def setUp(self):
        super(TestSyntaxCheck, self).setUp()
        self.rustc_version = util.get_rustc_version(sublime.active_window(),
                                                    plugin_path)

    def test_messages(self):
        """Test message generation.

        Each of the listed files has comments that annotate where a message
        should appear.  Single-line messages use carets to specify where the
        message should appear on the previous line.  Use multiple comments if
        there are multiple messages.  Example:

            //     ^^^^ERR binary operation
            //     ^^^^NOTE an implementation of

        Multi-line messages use a marker to indicate where it starts and ends,
        and then comment lines below starting with ~ specify the messages that
        should appear for that region.  Example:

            /*BEGIN*/struct S {
                recursive: S
            }/*END*/
            // ~ERR recursive type has infinite size
            // ~ERR recursive type
            // ~HELP insert indirection

        You can place restrictions on the message in parenthesis after the
        level (comma separated).  This can be a semver check, or the word
        "test" to indicate that this message only shows up in a cfg(test)
        block.  Examples:

            // ^^^ERR(<1.16.0) error msg before 1.16
            // ^^^ERR(>=1.16.0,test) error msg after 1.16, test block only

        These tests are somewhat fragile, as new versions of Rust change the
        formatting of messages.  Hopefully these examples are relatively
        stable for now.
        """
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
            'error-tests/tests/macro-expansion.rs',
            'error-tests/tests/macro-backtrace-println.rs',
            # Workspace tests.
            'workspace/workspace1/src/lib.rs',
            'workspace/workspace1/src/anothermod/mod.rs',
            'workspace/workspace2/src/lib.rs',
            'workspace/workspace2/src/somemod.rs',
        ]
        methods = ['no-trans']
        if semver.match(self.rustc_version, '>=1.16.0'):
            methods.append('check')
        else:
            print('Skipping check, need rust >= 1.16.')
        if semver.match(self.rustc_version, '>=1.19.0'):
            # -Zno-trans now requires nightly
            self._override_setting('cargo_build', {
                'variants': {
                    'no-trans': {
                        'toolchain': 'nightly'
                    }
                }
            })
        for path in to_test:
            path = os.path.join('tests', path)
            self._with_open_file(path, self._test_messages,
                methods=methods)

    def test_clippy_messages(self):
        """Test clippy messages."""
        to_test = [
            'tests/error-tests/examples/clippy_ex.rs',
        ]
        for path in to_test:
            self._with_open_file(path, self._test_messages, methods=['clippy'])

    def _test_messages(self, view, methods=None):
        # Trigger the generation of messages.
        phantoms = []
        view_regions = []

        def collect_phantoms(v, key, region, content, layout, on_navigate):
            if v == view:
                phantoms.append((region, content))

        def collect_regions(v, key, regions, scope, icon, flags):
            if v == view:
                view_regions.extend(regions)

        m = plugin.rust.messages
        orig_add_phantom = m._sublime_add_phantom
        orig_add_regions = m._sublime_add_regions
        m._sublime_add_phantom = collect_phantoms
        m._sublime_add_regions = collect_regions
        try:
            for method in methods:
                with AlteredSetting('rust_syntax_checking_method', method):
                    self._test_messages2(view, phantoms, view_regions, method)
                phantoms.clear()
                view_regions.clear()
        finally:
            m._sublime_add_phantom = orig_add_phantom
            m._sublime_add_regions = orig_add_regions

    def _test_messages2(self, view, phantoms, regions, method):
        e = plugin.SyntaxCheckPlugin.RustSyntaxCheckEvent()
        # Force Cargo to recompile.
        self._cargo_clean(view)
        # os.utime(view.file_name())  1 second resolution is not enough
        e.on_post_save(view)
        # Wait for it to finish.
        self._get_rust_thread().join()
        expected_messages = self._collect_expected_regions(view)

        # Refresh based on the toolchain used.
        window = sublime.active_window()
        manifest_path = util.find_cargo_manifest(view.file_name())
        cs = cargo_settings.CargoSettings(window)
        cs.load()
        toolchain = cs.get_computed(manifest_path, method, None, 'toolchain')
        self.rustc_version = util.get_rustc_version(window, manifest_path,
            toolchain=toolchain)

        def restriction_check(restrictions):
            if not restrictions:
                return True
            checks = restrictions[1:-1].split(',')
            for check in checks:
                if check == 'test':
                    if method == 'check':
                        # 'cargo check' currently does not handle cfg(test)
                        # blocks (see
                        # https://github.com/rust-lang/cargo/issues/3431)
                        return False
                else:
                    if not semver.match(self.rustc_version, check):
                        return False
            return True

        # Check phantoms.
        for emsg_info in expected_messages:
            if restriction_check(emsg_info['restrictions']):
                for i, (region, content) in enumerate(phantoms):
                    content = unescape(content)
                    # Phantom regions only apply to the last row.
                    r_row, _ = view.rowcol(region.end())
                    emsg_row, _ = view.rowcol(emsg_info['end'])
                    if r_row == emsg_row and emsg_info['message'] in content:
                        self.assertIn(emsg_info['level_text'], content)
                        break
                else:
                    raise AssertionError('Did not find expected message "%s:%s" for region %r:%r for file %r method=%r\nAvailable phantoms=%r' % (
                        emsg_info['level'], emsg_info['message'],
                        emsg_info['begin'], emsg_info['end'],
                        view.file_name(), method, phantoms))
                del phantoms[i]
        if len(phantoms):
            raise AssertionError('Got extra phantoms for %r (method=%s): %r' % (
                view.file_name(), method, phantoms))

        # Check regions.
        found_regions = set()
        region_set = {(r.begin(), r.end()) for r in regions}

        for emsg_info in expected_messages:
            if restriction_check(emsg_info['restrictions']):
                r = (emsg_info['begin'], emsg_info['end'])
                if r in region_set:
                    found_regions.add(r)
                else:
                    raise AssertionError('Did not find expected region %r,%r for file %r method %r\nActual regions=%r' % (
                        emsg_info['begin'], emsg_info['end'], view.file_name(),
                        method, region_set))
        if len(region_set) != len(found_regions):
            extra_regions = region_set - found_regions
            raise AssertionError('Got extra regions for %r: %r' % (
                view.file_name(), extra_regions))

    def _collect_expected_regions(self, view):
        """Scans through the view looking for the markup that tells us where
        error messages should appear.

        Returns a list of dictionaries with info about each message.
        """
        result = []
        msg_level_text = {
            'WARN': 'warning',
            'ERR': 'error',
            'NOTE': 'note',
            'HELP': 'help',
        }
        # Multi-line spans.
        region_map = {}  # Map the last row number to a (begin,end) region.
        pattern = r'(?s)/\*BEGIN\*/(.*?)/\*END\*/'
        regions = view.find_all(pattern)
        for region in regions:
            row = view.rowcol(region.end())[0]
            region_map[row] = (region.begin() + 9, region.end() - 7)

        pattern = r'// *~(WARN|ERR|HELP|NOTE)(\([^)]+\))? (.+)'
        regions = view.find_all(pattern)
        last_line = None  # Used to handle multiple messages on the same line.
        last_line_offset = 1
        for region in regions:
            text = view.substr(region)
            m = re.match(pattern, text)
            row = view.rowcol(region.begin())[0]
            if row - 1 == last_line:
                last_line = row
                row -= last_line_offset
                last_line_offset += 1
            else:
                last_line = row
                last_line_offset = 1
            try:
                actual_region = region_map[row - 1]
            except KeyError:
                raise AssertionError('Invalid test:  %r did not have region on row %r' % (
                    view.file_name(), row - 1))
            result.append({
                'begin': actual_region[0],
                'end': actual_region[1],
                'level': m.group(1),
                'level_text': msg_level_text[m.group(1)],
                'restrictions': m.group(2),
                'message': m.group(3)
            })

        # Single-line spans.
        last_line = None
        last_line_offset = 1
        pattern = r'//( *)(\^+)(WARN|ERR|HELP|NOTE)(\([^)]+\))? (.+)'
        regions = view.find_all(pattern)
        for region in regions:
            text = view.substr(region)
            m = re.match(pattern, text)
            row, col = view.rowcol(region.begin())
            if row - 1 == last_line:
                last_line = row
                row -= last_line_offset
                last_line_offset += 1
            else:
                last_line = row
                last_line_offset = 1
            begin = view.text_point(row - 1, col + 2 + len(m.group(1)))
            end = begin + len(m.group(2))
            result.append({
                'begin': begin,
                'end': end,
                'level': m.group(3),
                'level_text': msg_level_text[m.group(3)],
                'restrictions': m.group(4),
                'message': m.group(5)
            })

        return result
