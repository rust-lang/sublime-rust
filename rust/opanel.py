"""Module displaying build output in a Sublime output panel."""

import os
from . import rust_proc, messages, util

# Use the same panel name that Sublime's build system uses so that "Show Build
# Results" will open the same panel.  I don't see any particular reason why
# this would be a problem.  If it is, it's a simple matter of changing this.
PANEL_NAME = 'exec'


def create_output_panel(window, cwd):
    output_view = window.create_output_panel(PANEL_NAME)
    s = output_view.settings()
    if util.get_setting('show_errors_inline', True):
        # FILENAME:LINE: MESSAGE
        # Two dots to handle Windows DRIVE:
        s.set('result_file_regex', '^[^:]+: (..[^:]*):([0-9]+): (.*)$')
    else:
        build_pattern = '[ \\t]*-->[ \\t]*([^<\n]*):([0-9]+):([0-9]+)'
        test_pattern = ', ([^,<\n]*\\.[A-z]{2}):([0-9]+)'
        pattern = '(?|%s|%s)' % (build_pattern, test_pattern)
        s.set('result_file_regex', pattern)
    # Used for resolving relative paths.
    s.set('result_base_dir', cwd)
    s.set('word_wrap', True)  # XXX Or False?
    s.set('line_numbers', False)
    s.set('gutter', False)
    s.set('scroll_past_end', False)
    output_view.assign_syntax('Cargo.build-language')
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

    def __init__(self, window, base_path):
        self.window = window
        self.base_path = base_path

    def on_begin(self, proc):
        self.output_view = create_output_panel(self.window, self.base_path)
        self._append('[Running: %s]' % (' '.join(proc.cmd),))

    def on_data(self, proc, data):
        self._append(data, nl=False)

    def on_error(self, proc, message):
        self._append(message)

    def on_json(self, proc, obj):
        if 'message' in obj:
            messages.add_rust_messages(self.window, proc.cwd, obj['message'],
                                       None, self.msg_cb)

    def msg_cb(self, path, span_region, is_main, message, level):
        if path:
            if self.base_path and path.startswith(self.base_path):
                path = os.path.relpath(path, self.base_path)
            if span_region:
                self._append('%s: %s:%d: %s' % (level, path,
                    span_region[0][0], message))
            else:
                self._append('%s: %s: %s' % (level, path, message))
        else:
            self._append('%s: %s' % (level, message))

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
