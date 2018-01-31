"""Tests to exercise the on-save syntax checking.

This currently runs on Rust 1.15.
"""


import contextlib
import itertools
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
        message should appear on the previous line.  Immediately following is
        the level of the message:

            //  ^^^^ERR error example
            //  ^^^^WARN warning example
            //  ^^^^NOTE note example
            //  ^^^^HELP help example
            //  ^^^^MSG message with no level

        Use multiple comments if there are multiple messages.  Example:

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

        For messages that appear at the bottom of the file, use a comment with
        "end-msg:" like this:

            // end-msg: WARN crate `SNAKE` should have a snake case

        If a message starts and ends with a slash, it will match as a regex.

            // ^^^ERR /this is.*a regex/

        You can place restrictions on the message in parenthesis after the
        level (comma separated).  Examples:

            // ^^^ERR(<1.16.0) error msg before 1.16
            // ^^^ERR(>=1.16.0,test) error msg after 1.16, test block only

        The current restrictions are:

        - `no-trans`: This message only appears with no-trans method.
        - `check`: This message only appears with check method.
        - semver: Any semver string to match against the rustc version.
        - `key=value`: Check a configuration value.

        With multiple restrictions, they must all pass.  You can separate
        restrictions with " OR " to combine with Boolean OR:

            // ^^^ERR(check OR test,<1.16.0) checks or test less than 1.16.

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
            ([_altered_settings('rust_syntax_checking_include_tests', [True, False])],
                'error-tests/src/lib.rs'),
            'error-tests/tests/macro-expansion.rs',
            'error-tests/tests/macro-backtrace-println.rs',
            'error-tests/examples/SNAKE.rs',
            ([_altered_settings('rust_syntax_checking_include_tests', [True, False])],
                'error-tests/examples/no_main.rs', 'error-tests/examples/no_main_mod.rs'),
            ('error-tests/tests/remote_note_1.rs', 'error-tests/tests/remote_note_1_mod.rs'),
            'error-tests/tests/macro-expansion-outside-1.rs',
            'error-tests/tests/macro-expansion-outside-2.rs',
            ('error-tests/tests/macro-expansion-inside-1.rs', 'error-tests/tests/macro_expansion_inside_mod1.rs'),
            ('error-tests/tests/macro-expansion-inside-2.rs', 'error-tests/tests/macro_expansion_inside_mod2.rs'),
            ('error-tests/tests/error_across_mod.rs', 'error-tests/tests/error_across_mod_f.rs'),
            'error-tests/tests/derive-error.rs',
            'error-tests/tests/test_new_lifetime_message.rs',
            # Workspace tests.
            'workspace/workspace1/src/lib.rs',
            'workspace/workspace1/src/anothermod/mod.rs',
            'workspace/workspace2/src/lib.rs',
            'workspace/workspace2/src/somemod.rs',
        ]

        # Configure different permutations of settings to test for each file.
        methods = ['no-trans']
        if semver.match(self.rustc_version, '>=1.16.0'):
            methods.append('check')
        else:
            print('Skipping check, need rust >= 1.16.')
        setups = [_altered_settings('rust_syntax_checking_method', methods)]

        if semver.match(self.rustc_version, '>=1.19.0'):
            # -Zno-trans now requires nightly
            self._override_setting('cargo_build', {
                'variants': {
                    'no-trans': {
                        'toolchain': 'nightly'
                    }
                }
            })

        for paths in to_test:
            if not isinstance(paths, tuple):
                paths = (paths,)
            if isinstance(paths[0], str):
                extra_setups = []
            else:
                extra_setups = paths[0]
                paths = paths[1:]
            paths = [os.path.join('tests', p) for p in paths]
            self._with_open_file(paths[0], self._test_messages,
                setups=setups + extra_setups, extra_paths=paths[1:])

    def test_clippy_messages(self):
        """Test clippy messages."""
        to_test = [
            'tests/error-tests/examples/clippy_ex.rs',
        ]
        setups = [[AlteredSetting('rust_syntax_checking_method', 'clippy')]]
        for path in to_test:
            self._with_open_file(path, self._test_messages, setups=setups)

    def _test_messages(self, view, setups=None, extra_paths=()):
        # Capture all calls to Sublime to add phantoms and regions.
        # These are keyed by filename.
        phantoms = {}
        view_regions = {}

        def collect_phantoms(v, key, region, content, layout, on_navigate):
            ps = phantoms.setdefault(v.file_name(), [])
            ps.append((region, content))

        def collect_regions(v, key, regions, scope, icon, flags):
            rs = view_regions.setdefault(v.file_name(), [])
            rs.extend(regions)

        m = plugin.rust.messages
        orig_add_phantom = m._sublime_add_phantom
        orig_add_regions = m._sublime_add_regions
        m._sublime_add_phantom = collect_phantoms
        m._sublime_add_regions = collect_regions

        # Trigger the generation of messages.
        try:
            for setup in itertools.product(*setups):
                with contextlib.ExitStack() as stack:
                    for ctx in setup:
                        stack.enter_context(ctx)
                    self._test_messages2(view, phantoms, view_regions, extra_paths, setup)
                phantoms.clear()
                view_regions.clear()
        finally:
            m._sublime_add_phantom = orig_add_phantom
            m._sublime_add_regions = orig_add_regions

    def _test_messages2(self, view, phantoms, regions, extra_paths, setup):
        e = plugin.SyntaxCheckPlugin.RustSyntaxCheckEvent()
        # Force Cargo to recompile.
        self._cargo_clean(view)
        # os.utime(view.file_name())  1 second resolution is not enough
        e.on_post_save(view)
        # Wait for it to finish.
        self._get_rust_thread().join()
        self._test_messages_check(view, phantoms, regions, setup)

        def extra_check(view):
            # on_load is disabled during tests, do it manually.
            plugin.rust.messages.show_messages_for_view(view)
            self._test_messages_check(view, phantoms, regions, setup)

        # Load any other views that are expected to have messages.
        for path in extra_paths:
            self._with_open_file(path, extra_check)

    def _test_messages_check(self, view, phantoms, regions, setup):
        phantoms = phantoms.get(view.file_name(), [])
        regions = regions.get(view.file_name(), [])
        expected_messages = self._collect_expected_regions(view)

        # Refresh based on the toolchain used.
        window = sublime.active_window()
        manifest_path = util.find_cargo_manifest(view.file_name())
        cs = cargo_settings.CargoSettings(window)
        cs.load()
        method = util.get_setting('rust_syntax_checking_method')
        toolchain = cs.get_computed(manifest_path, method, None, 'toolchain')
        self.rustc_version = util.get_rustc_version(window, manifest_path,
            toolchain=toolchain)

        def do_check(check):
            if check == 'check':
                # This message only shows up in check.
                return method == 'check'
            elif check == 'no-trans':
                # This message only shows up in no-trans.
                return method == 'no-trans'
            elif check == 'nightly':
                # This message only shows on nightly.
                return 'nightly' in self.rustc_version
            elif re.match('[<>=!0-9]', check):
                return semver.match(self.rustc_version, check)
            elif '=' in check:
                key, value = check.split('=')
                if value == 'True':
                    value = True
                elif value == 'False':
                    value = False
                return util.get_setting(key) == value
            else:
                raise ValueError(check)

        def restriction_check(restrictions):
            if not restrictions:
                return True
            ors = restrictions[1:-1].split(' OR ')
            for conj in ors:
                checks = conj.split(',')
                for check in checks:
                    if not do_check(check):
                        break
                else:
                    return True
            return False

        region_set = {(r.begin(), r.end()) for r in regions}

        # Check phantoms.
        for emsg_info in expected_messages:
            if not emsg_info['message']:
                # This is a region-only highlight.
                continue
            if restriction_check(emsg_info['restrictions']):
                for i, (region, content) in enumerate(phantoms):
                    content = unescape(content)
                    # Phantom regions only apply to the last row.
                    r_row, _ = view.rowcol(region.end())
                    emsg_row, _ = view.rowcol(emsg_info['end'])
                    if r_row == emsg_row:
                        emsg = emsg_info['message']
                        if emsg.startswith('/') and emsg.endswith('/'):
                            match = bool(re.search(emsg[1:-1], content, re.S))
                        else:
                            match = emsg in content
                        if match:
                            self.assertIn(emsg_info['level'], content)
                            break
                else:
                    raise AssertionError('Did not find expected message "%s:%s" for region %r:%r for file %r\nsetup=%s\nversion=%s\nAvailable phantoms=%r' % (
                        emsg_info['level'], emsg_info['message'],
                        emsg_info['begin'], emsg_info['end'],
                        view.file_name(), _setup_debug(setup), self.rustc_version, phantoms))
                del phantoms[i]
        if len(phantoms):
            raise AssertionError('Got extra phantoms for %r\nsetup=%s\nversion=%s\n%r' % (
                view.file_name(), _setup_debug(setup), self.rustc_version, phantoms))

        # Check regions.
        found_regions = set()

        for emsg_info in expected_messages:
            if restriction_check(emsg_info['restrictions']):
                r = (emsg_info['begin'], emsg_info['end'])
                if r in region_set:
                    found_regions.add(r)
                else:
                    raise AssertionError('Did not find expected region %r,%r for file %r\nsetup=%s\nversion=%s\nActual regions=%r' % (
                        emsg_info['begin'], emsg_info['end'], view.file_name(),
                        _setup_debug(setup), self.rustc_version, region_set))
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
            'MSG': '',
        }
        # Multi-line spans.
        region_map = {}  # Map the last row number to a (begin,end) region.
        pattern = r'(?s)/\*BEGIN\*/(.*?)/\*END\*/'
        regions = view.find_all(pattern)
        for region in regions:
            row = view.rowcol(region.end())[0]
            region_map[row] = (region.begin() + 9, region.end() - 7)

        # Tilde identifies the message for the multi-line span just above.
        pattern = r'// *~(WARN|ERR|HELP|NOTE|MSG)(\([^)]+\))? (.+)'
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
                'level': msg_level_text[m.group(1)],
                'restrictions': m.group(2),
                'message': m.group(3)
            })

        # Single-line spans.
        last_line = None
        last_line_offset = 1
        pattern = r'//( *)(\^+)(WARN|ERR|HELP|NOTE|MSG)(\([^)]+\))?(?: (.+))?'
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
                'level': msg_level_text[m.group(3)],
                'restrictions': m.group(4),
                'message': m.group(5)
            })

        # Messages that appear at the end of the file.
        pattern = r'// *end-msg: *(WARN|ERR|HELP|NOTE|MSG)(\([^)]+\))? (.+)'
        regions = view.find_all(pattern)
        for region in regions:
            text = view.substr(region)
            m = re.match(pattern, text)
            result.append({
                'begin': view.size(),
                'end': view.size(),
                'level': msg_level_text[m.group(1)],
                'restrictions': m.group(2),
                'message': m.group(3),
            })

        return result


def _altered_settings(name, values):
    return [AlteredSetting(name, value) for value in values]


def _setup_debug(setup):
    return '\n' + '\n'.join(['    ' + str(s) for s in setup])
