import sublime, sublime_plugin
import subprocess
import os
import html
import json

class rustPluginSyntaxCheckEvent(sublime_plugin.EventListener):

    def on_post_save_async(self, view):
        # Are we in rust scope and is it switched on?
        # We use phantoms which were added in 3118
        if int(sublime.version()) < 3118:
            return
        
        settings = view.settings()
        enabled = settings.get('rust_syntax_checking')
        if enabled and "source.rust" in view.scope_name(0):
            file_name = os.path.abspath(view.file_name())
            file_dir = os.path.dirname(file_name)
            os.chdir(file_dir)
            # shell=True is needed to stop the window popping up, although it looks like this is needed:
            # http://stackoverflow.com/questions/3390762/how-do-i-eliminate-windows-consoles-from-spawned-processes-in-python-2-7
            # We only care about stderr
            cargo_command = self.cargo_rustc_command(file_name, settings)
            cargoRun = subprocess.Popen(cargo_command,
                shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE,
                universal_newlines = True
            )
            output = cargoRun.communicate()
            if output[1].startswith('error'):
                print(output[1])
                return

            for view in view.window().views(): 
                view.erase_phantoms('buildErrorLine')

            for line in output[1].split('\n'):
                if line == '' or line[0] != '{':
                    continue
                info = json.loads(line)
                # Can't show without spans
                if len(info['spans']) == 0:
                    continue
                self.add_error_phantom(view.window(), info, settings)

        # If the user has switched OFF the plugin, remove any phantom lines
        elif not enabled:
            for view in view.window().views(): 
                view.erase_phantoms('buildErrorLine')

    def cargo_rustc_command(self, file_name, settings):
        command = 'cargo rustc {target} -- -Zno-trans -Zunstable-options --error-format=json'
        target = ''
        for project in settings.get('projects', {}).values(): 
            src_root = os.path.join(project.get('root', ''), 'src')
            if not file_name.startswith(src_root):
                continue
            targets = project.get('targets', {})
            for tfile, tcmd in targets.items():
                if file_name == os.path.join(src_root, tfile):
                    target = tcmd
                    break
            else:
                target = targets.get('_default', '')
        return command.replace('{target}', target)


    def add_error_phantom(self, window, info, settings):
        msg = info['message']
        error_colour = settings.get('rust_syntax_error_color')
        warning_colour = settings.get('rust_syntax_warning_color')
        
        if error_colour is None:
            base_color = "var(--redish)" # Error color
        else:
            base_color = error_colour
        
        if info['level'] != "error":
            # Warning color
            if warning_colour is None:
                base_color = "var(--yellowish)"
            else:
                base_color = warning_colour
                

        for span in info['spans']:
            view = window.find_open_file(os.path.realpath(span['file_name']))
            if not view:
                continue

            color = base_color
            char = "^"
            if not span['is_primary']:
                # Non-primary spans are normally additional
                # information to help understand the error.
                color = "var(--foreground)"
                char = "-"
            # Sublime text is 0 based whilst the line/column info from
            # rust is 1 based.
            area = sublime.Region(
                view.text_point(span['line_start'] - 1, span['column_start'] - 1),
                view.text_point(span['line_end'] - 1, span['column_end'] - 1)
            )

            underline = char * (span['column_end'] - span['column_start'])
            label = span['label']
            if not label:
                label = ''

            view.add_phantom(
                'buildErrorLine', area,
                "<span style=\"color:{}\">{} {}</span>"
                .format(color, underline, html.escape(label, quote=False)),
                sublime.LAYOUT_BELOW
            )
            if span['is_primary']:
                view.add_phantom(
                    'buildErrorLine', area,
                    "<span style=\"color:{}\">{}</span>"
                    .format(color,  html.escape(msg, quote=False)),
                    sublime.LAYOUT_BELOW
                )
