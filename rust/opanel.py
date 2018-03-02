"""Module displaying build output in a Sublime output panel."""

import sublime

import os
import re
from . import rust_proc, messages, util, semver

# Use the same panel name that Sublime's build system uses so that "Show Build
# Results" will open the same panel.  I don't see any particular reason why
# this would be a problem.  If it is, it's a simple matter of changing this.
PANEL_NAME = 'exec'


def create_output_panel(window, base_dir):
    output_view = window.create_output_panel(PANEL_NAME)
    s = output_view.settings()
    if util.get_setting('show_errors_inline', True):
        # FILENAME:LINE: MESSAGE
        # Two dots to handle Windows DRIVE:
        s.set('result_file_regex', '^[^:]+: (..[^:]*):([0-9]+): (.*)$')
    else:
        build_pattern = '^[ \\t]*-->[ \\t]*([^<\n]*):([0-9]+):([0-9]+)'
        test_pattern = ', ([^,<\n]*\\.[A-z]{2}):([0-9]+)'
        pattern = '(?|%s|%s)' % (build_pattern, test_pattern)
        s.set('result_file_regex', pattern)
    # Used for resolving relative paths.
    s.set('result_base_dir', base_dir)
    s.set('word_wrap', True)  # XXX Or False?
    s.set('line_numbers', False)
    s.set('gutter', False)
    s.set('scroll_past_end', False)
    output_view.assign_syntax('Cargo.sublime-syntax')
    # 'color_scheme'?
    # XXX: Is this necessary?
    # self.window.create_output_panel(PANEL_NAME)
    if util.get_setting('show_panel_on_build', True):
        window.run_command('show_panel', {'panel': 'output.' + PANEL_NAME})
    return output_view


def display_message(window, msg):
    """Utility function for displaying a one-off message (typically an error)
    in a new output panel."""
    v = create_output_panel(window, '')
    _append(v, msg)


def _append(view, text):
    view.run_command('append', {'characters': text,
                                'scroll_to_end': True})


class OutputListener(rust_proc.ProcListener):

    """Listener used for displaying results to a Sublime output panel."""

    # Sublime view used for output.
    output_view = None

    def __init__(self, window, base_path, command_name, rustc_version):
        self.window = window
        self.base_path = base_path
        self.command_name = command_name
        self.rustc_version = rustc_version

    def on_begin(self, proc):
        self.output_view = create_output_panel(self.window, self.base_path)
        self._append('[Running: %s]' % (' '.join(proc.cmd),))

    def on_data(self, proc, data):
        region_start = self.output_view.size()
        self._append(data, nl=False)
        # Check for test errors.
        if self.command_name == 'test':
            # Re-fetch the data to handle things like \t expansion.
            appended = self.output_view.substr(
                sublime.Region(region_start, self.output_view.size()))
            m = re.search(r', ([^,<\n]*\.[A-z]{2}):([0-9]+):([0-9]+)',
                appended)
            if m:
                path = os.path.join(self.base_path, m.group(1))
                if not os.path.exists(path):
                    # Panics outside of the crate display a path to that
                    # crate's source file (such as libcore), which is probably
                    # not available.
                    return
                lineno = int(m.group(2)) - 1
                # Region columns appear to the left, so this is +1.
                col = int(m.group(3))
                # Rust 1.24 changed column numbering to be 1-based.
                if semver.match(self.rustc_version, '>=1.24.0-beta'):
                    col -= 1
                span = ((lineno, col), (lineno, col))
                # +2 to skip ", "
                build_region = sublime.Region(region_start + m.start() + 2,
                                              region_start + m.end())

                # Use callback so the build output window scrolls to this
                # point.
                def on_test_cb(message):
                    message['output_panel_region'] = build_region

                messages.add_message(self.window, path, span, 'error', True,
                    None, None, on_test_cb)

    def on_error(self, proc, message):
        self._append(message)

    def on_json(self, proc, obj):
        if 'message' in obj:
            messages.add_rust_messages(self.window, self.base_path, obj['message'],
                                       None, self.msg_cb)

    def msg_cb(self, message):
        level = message['level']
        region_start = self.output_view.size() + len(level) + 2
        path = message['path']
        if path:
            if self.base_path and path.startswith(self.base_path):
                path = os.path.relpath(path, self.base_path)
            if message['span']:
                highlight_text = '%s:%d' % (path, message['span'][0][0] + 1)
            else:
                highlight_text = path
            self._append('%s: %s: %s' % (level, highlight_text, message['text']))
            region = sublime.Region(region_start,
                                    region_start + len(highlight_text))
        else:
            self._append('%s: %s' % (level, message['text']))
            region = sublime.Region(region_start)
        message['output_panel_region'] = region

    def on_finished(self, proc, rc):
        if rc:
            self._append('[Finished in %.1fs with exit code %d]' % (
                proc.elapsed, rc))
            self._display_debug(proc)
        else:
            self._append('[Finished in %.1fs]' % proc.elapsed)
        messages.messages_finished(self.window)
        # Tell Sublime to find all of the lines with pattern from
        # result_file_regex.
        self.output_view.find_all_results()

    def on_terminated(self, proc):
        self._append('[Build interrupted]')

    def _append(self, message, nl=True):
        if nl:
            message += '\n'
        _append(self.output_view, message)

    def _display_debug(self, proc):
        # Display some information to help the user debug any build problems.
        self._append('[dir: %s]' % (proc.cwd,))
        # TODO: Fix this when adding PATH/env support.
        self._append('[path: %s]' % (proc.env.get('PATH'),))
