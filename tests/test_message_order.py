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
        window.run_command('cargo_set_target', {'target': 'auto',
                                                'variant': 'test',
                                                'package': pkg})

    def test_message_order(self):
        """Test message order.

        This opens a file and runs the build command on it.  It then verifies
        that next/prev message goes to the correct message in order.

        The files are annotated with comments to indicate where each message
        should appear and in which order.  The annotations should look like:

            /*ERR 1 "build_output_selection_inline" "build_output_selection_raw"*/
            /*WARN 1 "build_output_selection_inline" "build_output_selection_raw"*/

        The number is the order the message should appear.  Two numbers can be
        specified separated with a comma, where the second number is the
        "unsorted" sequence (the order the message is emitted from rustc).
        """
        to_test = [
            ('build', 'examples/ex_warning1.rs',
                'examples/warning1.rs', 'examples/warning2.rs'),
            ('build', 'tests/test_all_levels.rs',),
            ('test', 'tests/test_test_output.rs',),
        ]
        for command, *paths in to_test:
            rel_paths = [os.path.join('tests/message-order', path)
                for path in paths]
            sorted_msgs, unsorted_msgs = self._collect_message_order(rel_paths)
            self.assertTrue(sorted_msgs)
            self.assertTrue(unsorted_msgs)
            self._with_open_file(rel_paths[0], self._test_message_order,
                messages=sorted_msgs, inline=True, command=command)
            self._with_open_file(rel_paths[0],
                self._test_message_order, messages=unsorted_msgs,
                inline=False, command=command)

    def _test_message_order(self, view, messages, inline, command):
        self._override_setting('show_errors_inline', inline)
        self._cargo_clean(view)
        window = view.window()
        self._run_build_wait(command)

        to_close = []

        def check_sequence(direction):
            omsgs = messages if direction == 'next' else reversed(messages)
            levels = ('all', 'error', 'warning') if inline else ('all',)
            times = 2 if inline else 1
            for level in levels:
                # Run through all messages twice to verify it starts again.
                for _ in range(times):
                    for (next_filename, next_level, next_row_col,
                         inline_highlight, raw_highlight) in omsgs:
                        if inline and (
                           (level == 'error' and next_level != 'ERR') or
                           (level == 'warning' and next_level != 'WARN')):
                            continue
                        window.run_command('rust_' + direction + '_message',
                            {'levels': level})
                        # Sublime doesn't always immediately move the active
                        # view when 'next_result' is called, so give it a
                        # moment to update.
                        time.sleep(0.1)
                        next_view = window.active_view()
                        to_close.append(next_view)
                        self.assertEqual(next_view.file_name(), next_filename)
                        region = next_view.sel()[0]
                        rowcol = next_view.rowcol(region.begin())
                        self.assertEqual(rowcol, next_row_col)
                        # Verify the output panel is highlighting the correct
                        # thing.
                        build_panel = window.find_output_panel(
                            plugin.rust.opanel.PANEL_NAME)
                        panel_text = build_panel.substr(build_panel.sel()[0])
                        if inline:
                            self.assertEqual(panel_text, inline_highlight)
                        else:
                            self.assertEqual(panel_text, raw_highlight)

        check_sequence('next')
        if inline:
            # Reset back to first.
            window.run_command('rust_next_message')
            # Run backwards twice, too.
            check_sequence('prev')
            # Test starting backwards.
            window.focus_view(view)
            self._cargo_clean(view)
            self._run_build_wait(command)
            check_sequence('prev')

        for close_view in to_close:
            if close_view.window():
                window.focus_view(close_view)
                window.run_command('close_file')

    def _collect_message_order(self, paths):
        """Scan test files for comments that indicate the order of messages.

        :param paths: List of paths relative to the plugin.

        :returns: Returns a tuple of two lists.  The first list is the sorted
            order of messages.  The first list is the unsorted order of
            messages.  Each list has tuples (path, level, (row, col),
            inline_highlight, raw_highlight).
        """
        result = []
        for path in paths:
            self._with_open_file(path, self._collect_message_order_view,
                result=result)
        # Sort the result.
        sorted_result = sorted(result, key=lambda x: x[0])
        unsorted_result = sorted(result, key=lambda x: x[1])
        # Verify that the markup was entered correctly.
        self.assertEqual([x[0] for x in sorted_result],
            list(range(1, len(sorted_result) + 1)))
        # Strip the sequence number.
        return ([x[2:] for x in sorted_result],
                [x[2:] for x in unsorted_result])

    def _collect_message_order_view(self, view, result):
        pattern = r'/\*(ERR|WARN) ([0-9,]+) "([^"]+)"(?: "([^"]+)")?\*/'
        regions = view.find_all(pattern)

        def path_fixup(p):
            if sys.platform == 'win32':
                return p.replace('/', '\\')
            else:
                return p

        for region in regions:
            text = view.substr(region)
            m = re.match(pattern, text)
            rowcol = view.rowcol(region.end())
            if ',' in m.group(2):
                sort_index, unsorted = map(int, m.group(2).split(','))
            else:
                sort_index = int(m.group(2))
                unsorted = sort_index
            inline_highlight = path_fixup(m.group(3))
            if m.group(4):
                raw_highlight = path_fixup(m.group(4))
            else:
                raw_highlight = inline_highlight
            result.append((sort_index, unsorted, view.file_name(),
                m.group(1), rowcol, inline_highlight, raw_highlight))

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
