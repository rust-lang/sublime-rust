"""Tests for toggle command."""


from rust_test_common import *


class TestToggle(TestBase):

    def test_toggle(self):
        window = sublime.active_window()
        self.assertEqual(
            util.get_setting('rust_syntax_checking', True),
            True)
        window.run_command('toggle_rust_syntax_setting')
        self.assertEqual(
            util.get_setting('rust_syntax_checking', True),
            False)
        window.run_command('toggle_rust_syntax_setting')
        self.assertEqual(
            util.get_setting('rust_syntax_checking', True),
            True)
