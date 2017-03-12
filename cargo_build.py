"""Sublime commands for the cargo build system."""

import sublime
import sublime_plugin
from .rust import (rust_proc, rust_thread, opanel, util, messages,
                   cargo_settings)
from .rust.cargo_config import *

# Maps command to an input string. Used to pre-populate the input panel with
# the last entered value.
LAST_EXTRA_ARGS = {}


class CargoExecCommand(sublime_plugin.WindowCommand):

    """cargo_exec Sublime command.

    This takes the following arguments:

    - `command`: The command to run.  Commands are defined in the
      `cargo_settings` module.  You can define your own custom command by
      passing in `command_info`.
    - `command_info`: Dictionary of values the defines how the cargo command
      is constructed.  See `command_settings.CARGO_COMMANDS`.
    - `settings`: Dictionary of settings overriding anything set in the
      Sublime project settings (see `command_settings`).
    """

    def run(self, command=None, command_info=None, settings=None):
        self.command_info = cargo_settings.CARGO_COMMANDS\
            .get(command, {}).copy()
        if command_info:
            self.command_info.update(command_info)
        self.initial_settings = settings if settings else {}
        if self.command_info.get('wants_run_args', False) and \
                'extra_run_args' not in self.initial_settings:
            self.window.show_input_panel('Enter extra args:',
                LAST_EXTRA_ARGS.get(command, ''),
                self._on_extra_args, None, None)
        else:
            self._run()

    def _on_extra_args(self, args):
        LAST_EXTRA_ARGS[self.command_info['command']] = args
        self.initial_settings['extra_run_args'] = args
        self._run()

    def _run(self):
        t = CargoExecThread(self.window,
                            self.command_info, self.initial_settings)
        t.start()


class CargoExecThread(rust_thread.RustThread):

    silently_interruptible = False
    name = 'Cargo Exec'

    def __init__(self, window, command_info, initial_settings):
        super(CargoExecThread, self).__init__(window)
        self.command_info = command_info
        self.initial_settings = initial_settings

    def run(self):
        self.settings = cargo_settings.CargoSettings(self.window)
        try:
            self.settings.load()
        except cargo_settings.LoadSettingsError:
            return
        cmd = self.settings.get_command(self.command_info,
                                        self.initial_settings)
        if not cmd:
            return
        messages.clear_messages(self.window)
        p = rust_proc.RustProc()
        listener = opanel.OutputListener(self.window,
                                         self.settings.manifest_dir)
        try:
            p.run(self.window, cmd, self.settings.manifest_dir, listener)
            p.wait()
        except rust_proc.ProcessTerminatedError:
            return


class CargoEventListener(sublime_plugin.EventListener):

    """Every time a new file is loaded, check if is a Rust file with messages,
    and if so, display the messages.
    """

    def on_load(self, view):
        if 'source.rust' in view.scope_name(0):
            # For some reason, view.window() returns None here.
            # Use set_timeout to give it time to attach to a window.
            sublime.set_timeout(
                lambda: messages.show_messages_for_view(view), 1)


class RustNextMessageCommand(sublime_plugin.WindowCommand):

    def run(self, levels='all'):
        messages.show_next_message(self.window, levels)


class RustPrevMessageCommand(sublime_plugin.WindowCommand):

    def run(self, levels='all'):
        messages.show_prev_message(self.window, levels)


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
