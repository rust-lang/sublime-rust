"""Sublime commands for the cargo build system."""

import functools
import sublime
import sublime_plugin
from .rust import (rust_proc, rust_thread, opanel, util, messages,
                   cargo_settings, target_detect)
from .rust.cargo_config import *

# Maps command to an input string. Used to pre-populate the input panel with
# the last entered value.
LAST_EXTRA_ARGS = {}


class CargoExecCommand(sublime_plugin.WindowCommand):

    """cargo_exec Sublime command.

    This takes the following arguments:

    - `command`: The command name to run.  Commands are defined in the
      `cargo_settings` module.  You can define your own custom command by
      passing in `command_info`.
    - `command_info`: Dictionary of values the defines how the cargo command
      is constructed.  See `cargo_settings.CARGO_COMMANDS`.
    - `settings`: Dictionary of settings overriding anything set in the
      Sublime project settings (see `cargo_settings` module).
    """

    # The combined command info from `cargo_settings` and whatever the user
    # passed in.
    command_info = None
    # Dictionary of initial settings passed in by the user.
    initial_settings = None
    # CargoSettings instance.
    settings = None
    # Directory where to run the command.
    working_dir = None
    # Path used for the settings key.  This is typically `working_dir` except
    # for `cargo script`, in which case it is the path to the .rs source file.
    settings_path = None

    def run(self, command=None, command_info=None, settings=None):
        if command is None:
            return self.window.run_command('build', {'select': True})
        self.initial_settings = settings if settings else {}
        self.settings = cargo_settings.CargoSettings(self.window)
        self.settings.load()
        if command == 'auto':
            self._detect_auto_build()
        else:
            self.command_name = command
            self.command_info = cargo_settings.CARGO_COMMANDS\
                .get(command, {}).copy()
            if command_info:
                self.command_info.update(command_info)
            self._determine_working_path(self._run_check_for_args)

    def _detect_auto_build(self):
        """Handle the "auto" build variant, which automatically picks a build
        command based on the current view."""
        if not util.active_view_is_rust():
            sublime.error_message(util.multiline_fix("""
                Error: Could not determine what to build.

                Open a Rust source file as the active Sublime view.
            """))
            return
        td = target_detect.TargetDetector(self.window)
        view = self.window.active_view()
        targets = td.determine_targets(view.file_name())
        if len(targets) == 0:
            sublime.error_message(util.multiline_fix("""
                Error: Could not determine what to build.

                Try using one of the explicit build variants.
            """))
            return

        elif len(targets) == 1:
            self._auto_choice_made(targets, 0)

        else:
            # Can't determine a single target, let the user choose one.
            display_items = [' '.join(x[1]) for x in targets]
            on_done = functools.partial(self._auto_choice_made, targets)
            self.window.show_quick_panel(display_items, on_done)

    def _auto_choice_made(self, targets, index):
        if index != -1:
            src_path, cmd_line = targets[index]
            actions = {
                '--bin': 'run',
                '--example': 'run',
                '--lib': 'build',
                '--bench': 'bench',
                '--test': 'test',
            }
            cmd = actions[cmd_line[0]]
            self.initial_settings['target'] = ' '.join(cmd_line)
            self.run(command=cmd, settings=self.initial_settings)

    def _determine_working_path(self, on_done):
        """Determine where Cargo should be run.

        This may trigger some Sublime user interaction if necessary.
        """
        working_dir = self.initial_settings.get('working_dir')
        if working_dir:
            self.working_dir = working_dir
            self.settings_path = working_dir
            return on_done()

        script_path = self.initial_settings.get('script_path')
        if script_path:
            self.working_dir = os.path.dirname(script_path)
            self.settings_path = script_path
            return on_done()

        default_path = self.settings.get_project_base('default_path')
        if default_path:
            self.settings_path = default_path
            if os.path.isfile(default_path):
                self.working_dir = os.path.dirname(default_path)
            else:
                self.working_dir = default_path
            return on_done()

        if self.command_info.get('requires_manifest', True):
            cmd = CargoConfigPackage(self.window)
            cmd.run(functools.partial(self._on_manifest_choice, on_done))
        else:
            # For now, assume you need a Rust file if not needing a manifest
            # (for `cargo script`).
            view = self.window.active_view()
            if util.active_view_is_rust(view=view):
                self.settings_path = view.file_name()
                self.working_dir = os.path.dirname(self.settings_path)
                return on_done()
            else:
                sublime.error_message(util.multiline_fix("""
                    Error: Could not determine what Rust source file to use.

                    Open a Rust source file as the active Sublime view."""))
                return

    def _on_manifest_choice(self, on_done, package_path):
        self.settings_path = package_path
        self.working_dir = package_path
        on_done()

    def _run_check_for_args(self):
        if self.command_info.get('wants_run_args', False) and \
                not self.initial_settings.get('extra_run_args'):
            self.window.show_input_panel('Enter extra args:',
                LAST_EXTRA_ARGS.get(self.command_name, ''),
                self._on_extra_args, None, None)
        else:
            self._run()

    def _on_extra_args(self, args):
        LAST_EXTRA_ARGS[self.command_info['command']] = args
        self.initial_settings['extra_run_args'] = args
        self._run()

    def _run(self):
        t = CargoExecThread(self.window, self.settings,
                            self.command_name, self.command_info,
                            self.initial_settings,
                            self.settings_path, self.working_dir)
        t.start()


class CargoExecThread(rust_thread.RustThread):

    silently_interruptible = False
    name = 'Cargo Exec'

    def __init__(self, window, settings,
                 command_name, command_info,
                 initial_settings, settings_path, working_dir):
        super(CargoExecThread, self).__init__(window)
        self.settings = settings
        self.command_name = command_name
        self.command_info = command_info
        self.initial_settings = initial_settings
        self.settings_path = settings_path
        self.working_dir = working_dir

    def run(self):
        cmd = self.settings.get_command(self.command_name,
                                        self.command_info,
                                        self.settings_path,
                                        self.initial_settings)
        if not cmd:
            return
        messages.clear_messages(self.window)
        p = rust_proc.RustProc()
        listener = opanel.OutputListener(self.window, self.working_dir,
                                         self.command_name)
        decode_json = util.get_setting('show_errors_inline', True) and \
            self.command_info.get('allows_json', False)
        try:
            p.run(self.window, cmd['command'],
                  self.working_dir, listener,
                  env=cmd['env'],
                  decode_json=decode_json,
                  json_stop_pattern=self.command_info.get('json_stop_pattern'))
            p.wait()
        except rust_proc.ProcessTerminatedError:
            return


# This is used by the test code.  Due to the async nature of the on_load event,
# it can cause problems with the rapid loading of views.
ON_LOAD_MESSAGES_ENABLED = True


class CargoEventListener(sublime_plugin.EventListener):

    """Every time a new file is loaded, check if is a Rust file with messages,
    and if so, display the messages.
    """

    def on_load(self, view):
        if ON_LOAD_MESSAGES_ENABLED and util.active_view_is_rust(view=view):
            # For some reason, view.window() returns None here.
            # Use set_timeout to give it time to attach to a window.
            sublime.set_timeout(
                lambda: messages.show_messages_for_view(view), 1)

    def on_query_context(self, view, key, operator, operand, match_all):
        # Used by the Escape-key keybinding to dismiss inline phantoms.
        if key == 'rust_has_messages':
            has_messages = view.window().id() in messages.WINDOW_MESSAGES
            if operator == sublime.OP_EQUAL:
                return operand == has_messages
            elif operator == sublime.OP_NOT_EQUAL:
                return operand != has_messages
        return None


class NextPrevBase(sublime_plugin.WindowCommand):

    def _has_inline(self):
        return self.window.id() in messages.WINDOW_MESSAGES


class RustNextMessageCommand(NextPrevBase):

    def run(self, levels='all'):
        if self._has_inline():
            messages.show_next_message(self.window, levels)
        else:
            self.window.run_command('next_result')


class RustPrevMessageCommand(NextPrevBase):

    def run(self, levels='all'):
        if self._has_inline():
            messages.show_prev_message(self.window, levels)
        else:
            self.window.run_command('prev_result')


class RustCancelCommand(sublime_plugin.WindowCommand):

    def run(self):
        try:
            t = rust_thread.THREADS[self.window.id()]
        except KeyError:
            pass
        else:
            t.terminate()
        # Also call Sublime's cancel command, in case the user is using a
        # normal Sublime build.
        self.window.run_command('cancel_build')


class RustDismissMessagesCommand(sublime_plugin.WindowCommand):

    """Removes all inline messages."""

    def run(self):
        messages.clear_messages(self.window)


class RustListMessagesCommand(sublime_plugin.WindowCommand):

    """Shows a quick panel with a list of all messages."""

    def run(self):
        messages.list_messages(self.window)


# Patterns used to help find test function names.
# This is far from perfect, but should be good enough.
SPACE = r'[ \t]'
OPT_COMMENT = r"""(?:
    (?: [ \t]* //.*)
  | (?: [ \t]* /\*.*\*/ [ \t]* )
)?"""
IDENT = r"""(?:
    [a-z A-Z] [a-z A-Z 0-9 _]*
  | _         [a-z A-Z 0-9 _]+
)"""
TEST_PATTERN = r"""(?x)
    {SPACE}* \# {SPACE}* \[ {SPACE}* {WHAT} {SPACE}* \] {SPACE}*
    (?:
        (?: {SPACE}* \#\[  [^]]+  \] {OPT_COMMENT} \n )
      | (?: {OPT_COMMENT} \n )
    )*
    .* fn {SPACE}+ ({IDENT}+)
"""


def _target_to_test(what, view, on_done):
    """Helper used to determine build target from given view."""
    td = target_detect.TargetDetector(view.window())
    targets = td.determine_targets(view.file_name())
    if len(targets) == 0:
        sublime.error_message('Error: Could not determine target to %s.' % what)
    elif len(targets) == 1:
        on_done(' '.join(targets[0][1]))
    else:
        # Can't determine a single target, let the user choose one.
        display_items = [' '.join(x[1]) for x in targets]

        def quick_on_done(idx):
            on_done(targets[idx][1])

        view.window().show_quick_panel(display_items, quick_on_done)


def _pt_to_test_name(what, pt, view):
    """Helper used to convert Sublime point to a test/bench function name."""
    fn_names = []
    pat = TEST_PATTERN.format(WHAT=what, **globals())
    regions = view.find_all(pat, 0, r'\1', fn_names)
    if not regions:
        sublime.error_message('Could not find a Rust %s function.' % what)
        return None
    # Assuming regions are in ascending order.
    indices = [i for (i, r) in enumerate(regions) if r.a <= pt]
    if not indices:
        sublime.error_message('No %s functions found about the current point.' % what)
        return None
    return fn_names[indices[-1]]


def _cargo_test_pt(what, pt, view):
    """Helper used to run a test for a given point in the given view."""
    def do_test(target):
        test_fn_name = _pt_to_test_name(what, pt, view)
        if test_fn_name:
            view.window().run_command('cargo_exec', args={
                'command': what,
                'settings': {
                    'target': target,
                    'extra_run_args': '--exact ' + test_fn_name
                }
            })

    _target_to_test(what, view, do_test)


class CargoHere(sublime_plugin.WindowCommand):

    """Base class for mouse-here commands.

    Subclasses set `what` attribute.
    """

    what = None

    def run(self, event):
        view = self.window.active_view()
        if not view:
            return
        pt = view.window_to_text((event['x'], event['y']))
        _cargo_test_pt(self.what, pt, view)

    def want_event(self):
        return True


class CargoTestHereCommand(CargoHere):

    """Determines the test name at the current mouse position, and runs just
    that test."""

    what = 'test'


class CargoBenchHereCommand(CargoHere):

    """Determines the benchmark at the current mouse position, and runs just
    that benchmark."""

    what = 'bench'


class CargoTestAtCursorCommand(sublime_plugin.TextCommand):

    """Determines the test name at the current cursor position, and runs just
    that test."""

    def run(self, edit):
        pt = self.view.sel()[0].begin()
        _cargo_test_pt('test', pt, self.view)


class CargoCurrentFile(sublime_plugin.WindowCommand):

    """Base class for current file commands.

    Subclasses set `what` attribute.
    """

    what = None

    def run(self):
        print('current file')
        def _test_file(target):
            print('target is %r' % target)
            self.window.run_command('cargo_exec', args={
                'command': self.what,
                'settings': {
                    'target': target
                }
            })

        view = self.window.active_view()
        _target_to_test(self.what, view, _test_file)


class CargoTestCurrentFileCommand(CargoCurrentFile):

    """Runs all tests in the current file."""

    what = 'test'


class CargoBenchCurrentFileCommand(CargoCurrentFile):

    """Runs all benchmarks in the current file."""

    what = 'bench'


class CargoRunCurrentFileCommand(CargoCurrentFile):

    """Runs the current file."""

    what = 'run'


class CargoBenchAtCursorCommand(sublime_plugin.TextCommand):

    """Determines the benchmark name at the current cursor position, and runs
    just that benchmark."""

    def run(self, edit):
        pt = self.view.sel()[0].begin()
        _cargo_test_pt('bench', pt, self.view)
