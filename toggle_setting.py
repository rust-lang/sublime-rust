import sublime, sublime_plugin

class ToggleRustSyntaxSettingCommand(sublime_plugin.TextCommand):

    def run(self, setting):
        # Grab the setting and reserse it
        current_state = self.view.settings().get('rust_syntax_checking')
        self.view.settings().set('rust_syntax_checking', not current_state)
        self.view.window().status_message("Rust syntax checking is now " + ("inactive" if current_state else "active"))
