"""Tests for next/prev message navigation."""

import os
import re
from rust_test_common import *


class TestMessageOrder(TestBase):

    def setUp(self):
        super(TestMessageOrder, self).setUp()
        # Set a base version for these tests.
        version = util.get_rustc_version(sublime.active_window(), plugin_path)
        if semver.match(version, '<1.18.0'):
            self.skipTest('Tests require rust 1.18 or newer.')

        # Make it so that the build target is automatically determined from
        # the active view so each test doesn't have to specify it.
        window = sublime.active_window()
        pkg = os.path.normpath(os.path.join(plugin_path,
            'tests/message-order'))
        window.run_command('cargo_set_target', {'target': 'auto',
                                                'variant': 'build',
                                                'package': pkg})

    def test_message_order(self):
        """Test message order.

        This opens a file and runs the build command on it.  It then verifies
        that next/prev message goes to the correct message in order.

        The files are annotated with comments to indicate where each message
        should appear and in which order.  The annotations should look like:

            /*ERR 1*/
            /*WARN 2*/

        The number is the order the message should appear.
        """
        to_test = [
            ('examples/ex_warning1.rs',
                'examples/warning1.rs', 'examples/warning2.rs'),
            ('tests/test_all_levels.rs',),
        ]
        for paths in to_test:
            rel_paths = [os.path.join('tests/message-order', path)
                for path in paths]
            messages = self._collect_message_order(rel_paths)
            self.assertTrue(messages)
            self._with_open_file(rel_paths[0], self._test_message_order,
                messages=messages)

    def _test_message_order(self, view, messages):
        self._cargo_clean(view)
        window = view.window()
        self._run_build_wait()

        def check_sequence(direction):
            omsgs = messages if direction == 'next' else reversed(messages)
            for levels in ('all', 'error', 'warning'):
                # Run through all messages twice to verify it starts again.
                for _ in range(2):
                    for next_filename, next_level, next_row_col in omsgs:
                        if (levels == 'error' and next_level != 'ERR') or \
                           (levels == 'warning' and next_level != 'WARN'):
                            continue
                        window.run_command('rust_' + direction + '_message',
                            {'levels': levels})
                        next_view = window.active_view()
                        self.assertEqual(next_view.file_name(), next_filename)
                        region = next_view.sel()[0]
                        rowcol = next_view.rowcol(region.begin())
                        self.assertEqual(rowcol, next_row_col)

        check_sequence('next')
        # Reset back to first.
        window.run_command('rust_next_message')
        # Run backwards twice, too.
        check_sequence('prev')
        # Test starting backwards.
        window.focus_view(view)
        self._cargo_clean(view)
        self._run_build_wait()
        check_sequence('prev')

    def _collect_message_order(self, paths):
        """Scan test files for comments that indicate the order of messages.

        :param paths: List of paths relative to the plugin.

        :returns: Returns a list in order of tuples (path, level, (row, col)).
        """
        result = []
        for path in paths:
            self._with_open_file(path, self._collect_message_order_view,
                result=result)
        # Sort the result.
        result.sort()
        # Verify that the markup was entered correctly.
        self.assertEqual([x[0] for x in result],
            list(range(1, len(result) + 1)))
        # Strip the sequence number.
        return [x[1:] for x in result]

    def _collect_message_order_view(self, view, result):
        pattern = r'/\*(ERR|WARN) ([0-9]+)\*/'
        regions = view.find_all(pattern)
        for region in regions:
            text = view.substr(region)
            m = re.match(pattern, text)
            rowcol = view.rowcol(region.end())
            result.append((int(m.group(2)), view.file_name(),
                m.group(1), rowcol))

    def test_no_messages(self):
        self._with_open_file('tests/message-order/examples/ex_no_messages.rs',
            self._test_no_messages)

    def _test_no_messages(self, view):
        self._cargo_clean(view)
        window = view.window()
        self._run_build_wait()
        # Verify command does nothing.
        for direction in ('next', 'prev'):
            window.run_command('rust_' + direction + '_message')
            active = window.active_view()
            self.assertEqual(active, view)
            sel = active.sel()[0]
            self.assertEqual((sel.a, sel.b), (0, 0))
