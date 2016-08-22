import sublime, sublime_plugin
import subprocess
import os
import re
import webbrowser

# Requires Sublime Text 3 for the new pop ups API 
is_enabled = sublime.load_settings("Rust.sublime-settings").get("rust_syntax_checking") and sublime.version() != 3113


def is_event_on_gutter(view, event):
    """Determine if a mouse event points to the gutter.

    Because this is inapplicable for empty lines,
    returns `None` to let the caller decide on what do to.
    """
    original_pt = view.window_to_text((event["x"], event["y"]))
    if view.rowcol(original_pt)[1] != 0:
        return False

    # If the line is empty,
    # we will always get the same textpos
    # regardless of x coordinate.
    # Return `None` in this case and let the caller decide.
    if view.line(original_pt).empty():
        return None

    # ST will put the caret behind the first character
    # if we click on the second half of the char.
    # Use view.em_width() / 2 to emulate this.
    adjusted_pt = view.window_to_text((event["x"] + view.em_width() / 2, event["y"]))
    if adjusted_pt != original_pt:
        return False

    return original_pt

  
class rustPluginSyntaxCheckEvent(sublime_plugin.EventListener):

    def __init__(self):
        # This will fetch the line number that failed from the $ cargo run output
        # We could fetch multiple lines but this is a start
        # Lets compile it here so we don't need to compile on every save
        self.lineRegex = re.compile(b"(\w*\.rs):(\d+).*error\:\s(.*)")
        self.errors = {}

    def get_line_number_and_msg(self, output):
        if self.lineRegex.findall(output):
            return self.lineRegex.findall(output)

    def draw_dots_to_screen(self, view, line_num):
        line_num -= 1 # line numbers are zero indexed on the sublime API, so take off 1
        view.add_regions('buildError_dot_' + str(line_num), [view.line(view.text_point(line_num, 0))], 'comment', 'dot', sublime.HIDDEN)

    # Callback for when a link is clicked within a popup
    def on_navigate(self, href):
        webbrowser.open(href)

    # If there's an easier way of doing this please let me know
    def clear_all_regions(self, view):
        # THis is annoying as there's no "get all lines" in the API, so i have to create a region which covers the whole file, then generate an array, so i have a number
        # Once i have that number i can create a for-loop and remove any regions hanging around. It would be nice to just have a clearRegions() method
        total_lines = view.lines(sublime.Region(0, view.size()))
        for i, v in enumerate(total_lines):
            # The lines here will be zero-indexed, so bump up the num
            i = str(i + 1)
            view.erase_regions('buildError_highlight_' + i)
            view.erase_regions('buildError_dot_' + i)


    def on_post_save_async(self, view):
        if "source.rust" in view.scope_name(0) and is_enabled: # Are we in rust scope and is it switched on?
             # reset on every save
            self.errors = {}
            self.clear_all_regions(view)

            os.chdir(os.path.dirname(view.file_name()))
            # shell=True is needed to stop the window popping up, although it looks like this is needed: http://stackoverflow.com/questions/3390762/how-do-i-eliminate-windows-consoles-from-spawned-processes-in-python-2-7
            # We only care about stderr
            cargoRun = subprocess.Popen('cargo rustc -- -Zno-trans', shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            output = cargoRun.communicate()
            results = self.get_line_number_and_msg(output[1]) if len(output) > 1 else False
            if (results):
                # There could be more than 1 error, so traverse through
                for result in results:
                    fileName = result[0].decode('utf-8')
                    view_filename = os.path.basename(view.file_name())
                    line = int(result[1])
                    msg = result[2].decode('utf-8')
                    if (fileName == view_filename and line):
                        self.errors[line] = {}
                        self.errors[line]['msg'] = msg
                        if self.parse_error_message(self.errors[line]['msg']): # Were we able to get a token from this error?
                            token = self.parse_error_message(self.errors[line]['msg'])
                            self.errors[line]['token_region'] = view.find(token, view.text_point(line - 1, 0)) # this converts the token into a region
                            view.add_regions("buildError_highlight_" + str(line), [self.errors[line]['token_region']], 'comment')


                        self.draw_dots_to_screen(view, int(line))

    # This method will try to parse the error message and return the illegal token so the editor can highlight it
    def parse_error_message(self, error_message):
        # Im sure more error matching could be added here, but ill leave it as this for now
        expected_found_regex = re.compile("found `(.*)`")
        type_name_regex = re.compile("name `(.*)`")
        token = False
        if expected_found_regex.search(error_message):
            token = expected_found_regex.search(error_message).group(1)
        elif type_name_regex.search(error_message):
            token = type_name_regex.search(error_message).group(1)

        return token

    def on_text_command(self, view, command_name, args):
        if "source.rust" in view.scope_name(0) and is_enabled:
            if (args and 'event' in args):
                event = args['event']
            else:
                return

            if (is_event_on_gutter(view, event)): 
                line_clicked = view.rowcol(is_event_on_gutter(view, event))[0] + 1
                if line_clicked in self.errors:
                    view.show_popup(self.errors[line_clicked]['msg'])

            clicked_point = view.window_to_text((event["x"], event["y"]))
            clicked_row = view.rowcol(clicked_point)[0] + 1
            if clicked_row in self.errors:
                styled_error_message = re.sub(r'\[(.*)\]$', r'<br /><a href="#\1">\1</a>', self.errors[clicked_row]['msg'])
                view.show_popup(styled_error_message, location=clicked_point, on_navigate=self.on_navigate)
