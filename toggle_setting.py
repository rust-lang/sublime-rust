import sublime, sublime_plugin

class ToggleRustSyntaxSettingCommand(sublime_plugin.TextCommand):

    def run(self, setting):
        # Grab the setting and reserse it
        current_state = self.view.settings().get('rust_syntax_checking')
        if (current_state):
            self.view.settings().set('rust_syntax_checking', False)
        else:
            self.view.settings().set('rust_syntax_checking', True)
