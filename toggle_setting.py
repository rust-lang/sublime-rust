import sublime_plugin
from .rust import (util, messages)


class ToggleRustSyntaxSettingCommand(sublime_plugin.WindowCommand):

    """Toggles on-save checking for the current window."""

    def run(self):
        # Grab the setting and reverse it.
        window = self.window
        current_state = util.get_setting('rust_syntax_checking', True)
        new_state = not current_state
        pdata = window.project_data()
        pdata.setdefault('settings', {})['rust_syntax_checking'] = new_state
        if not new_state:
            messages.clear_messages(window)
        window.status_message("Rust syntax checking is now " + ("inactive" if current_state else "active"))
        window.set_project_data(pdata)

    def is_checked(self):
        return util.get_setting('rust_syntax_checking', True)
