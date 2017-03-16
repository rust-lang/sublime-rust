import os
import queue
import re
import sys
import time
import unittest
import sublime
from pprint import pprint
# Depends on how you install the plugin.
plugin = sys.modules.get('sublime-rust', sys.modules.get('Rust Enhanced', None))
if not plugin:
    raise ValueError('Couldn\'t find Rust Enhanced plugin.')
plugin_path = tuple(plugin.__path__)[0]
if plugin_path.endswith('.sublime-package'):
    raise ValueError('Cannot run test with compressed package.')

"""Tests to exercise the on-save syntax checking.

This currently runs on Rust 1.15.
"""

# TODO
# - manual config targets

class TestSyntaxCheck(unittest.TestCase):

    def _with_open_file(self, filename, f):
        """Opens filename (relative to the plugin) in a new view, calls
        f(view) to perform the tests.
        """
        window = sublime.active_window()
        path = os.path.join(plugin_path, filename)
        view = window.open_file(path)
        q = queue.Queue()

        def async_test_view():
            try:
                # Wait for view to finish loading.
                for n in range(500):
                    if view.is_loading():
                        time.sleep(0.01)
                    else:
                        break
                else:
                    raise AssertionError('View never loaded.')
                # Run the tests on this view.
                f(view)
            except Exception as e:
                q.put(e)
            else:
                q.put(None)

        try:
            sublime.set_timeout_async(async_test_view, 0)
            msg = q.get()
            if msg:
                raise msg
        finally:
            window.focus_view(view)
            window.run_command('close_file')

    def test_multi_targets(self):
        """Test automatic target detection."""

        expected_targets = [
            # Exact target name matches.
            ('src/lib.rs', [('src/lib.rs', '--lib')]),
            ('src/main.rs', [('src/main.rs', '--bin multi-targets')]),
            ('src/bin/bin1.rs', [('src/bin/bin1.rs', '--bin bin1')]),
            ('src/bin/bin2.rs', [('src/bin/bin2.rs', '--bin bin2')]),
            ('src/altmain.rs', [('src/altmain.rs', '--bin otherbin')]),
            ('examples/ex1.rs', [('examples/ex1.rs', '--example ex1')]),
            ('examples/ex2.rs', [('examples/ex2.rs', '--example ex2')]),
            ('examples/exlib.rs', [('examples/exlib.rs', '--example exlib')]),
            ('tests/test1.rs', [('tests/test1.rs', '--test test1')]),
            ('tests/test2.rs', [('tests/test2.rs', '--test test2')]),
            ('benches/bench1.rs', [('benches/bench1.rs', '--bench bench1')]),
            ('benches/bench2.rs', [('benches/bench2.rs', '--bench bench2')]),
            # Random module in src/, defaults to --lib.
            ('src/lmod1.rs', [('src/lib.rs', '--lib')]),
            # Target failure.  Perhaps this should run rustc directly?
            ('mystery.rs', []),
            ('build.rs', []),
            # Shared module in test, not possible to easily determine which
            # test it belongs to.
            ('tests/common/helpers.rs', [('tests/test1.rs', '--test test1'),
                                         ('tests/test2.rs', '--test test2')]),
            # proc-macro kind
            ('pmacro/src/lib.rs', [('pmacro/src/lib.rs', '--lib')]),

        ]
        for (path, targets) in expected_targets:
            path = os.path.join('tests', 'multi-targets', path)
            targets = [(os.path.normpath(
                os.path.join(plugin_path, 'tests', 'multi-targets', x[0])), x[1]) for x in targets]
            self._with_open_file(path, lambda view: self._test_multi_targets(view, targets))

    def _test_multi_targets(self, view, expected_targets):
        expected_targets.sort()
        # Check the targets match expectation.
        e = plugin.SyntaxCheckPlugin.rustPluginSyntaxCheckEvent()
        targets = e.determine_targets(view.settings(), view.file_name())
        targets.sort()
        self.assertEqual(targets, expected_targets)


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
            # This is currently broken.
            #'error-tests/tests/const-err.rs',
            # Macro-expansion test.
            'error-tests/tests/dead-code-ret.rs',
            # "code" test
            'error-tests/tests/E0005.rs',
            # unicode in JSON
            'error-tests/tests/test_unicode.rs',
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
        cwd = os.path.dirname(view.file_name())
        e = plugin.SyntaxCheckPlugin.rustPluginSyntaxCheckEvent()
        phantoms = []
        regions = []
        def collect_phantoms(v, key, region, content, layout, on_navigate):
            if v == view:
                phantoms.append((region, content))
        def collect_regions(v, key, regions, scope, icon, flags):
            if v == view:
                regions.extend(regions)
        e._add_phantom = collect_phantoms
        e._add_regions = collect_regions
        # Force Cargo to recompile.
        e.run_cargo(['clean'], cwd=cwd)
        # os.utime(view.file_name())  1 second resolution is not enough
        e.on_post_save_async(view)
        pattern = '(\^+)(WARN|ERR|HELP|NOTE) (.+)'
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
            msg_content = m.group(3)
            for i, (region, content) in enumerate(phantoms):
                # python 3.4 can use html.unescape()
                content = content.replace('&nbsp;', ' ')\
                                 .replace('&amp;', '&')\
                                 .replace('&lt;', '<')\
                                 .replace('&gt;', '>')
                r_row, r_col = view.rowcol(region.end())
                if r_row == msg_row and msg_content in content:
                    self.assertIn(msg_type_text, content)
                    break
            else:
                raise AssertionError('Did not find expected message "%s:%s" on line %r for file %r' % (
                    msg_type, msg_content, msg_row, view.file_name()))
            del phantoms[i]
        if len(phantoms):
            raise AssertionError('Got extra phantoms for %r: %r' % (view.file_name(), phantoms))
