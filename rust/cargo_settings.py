"""Interface for accessing Cargo settings (stored in the sublime-project
file).

These are used by the build system to determine how to run Cargo.

Cargo Info
==========
When the `cargo_exec` Sublime command is run, you pass in a named command to
run.  There is a default set of commands defined here in CARGO_COMMANDS (users
can create custom commands and pass them in with `command_info`).  A command
has the following values that are used for figuring out how to construct the
command:

- `name`: Human-readable name of the command (required).
- `command`: The command to pass to cargo (required).
- `allows_target`: If True, the command accepts cargo filters for determining
  which target to build ("--lib", "--bin foo", "--example bar", etc.).  Can
  also be a sequence of strings like `('bin', 'example')` to specify a subset
  of targets it supports.
- `allows_target_triple`: If True, the command accepts triples like
  "--target x86_64-apple-darwin".
- `allows_release`: If True, allows "--release" flag.
- `allows_features`: If True, allows feature flags.
- `allows_json`: If True, allows "--message-format=json" flag.
- `wants_view_path`: If True, then the active view must be a Rust source file,
  and the path to that file will be passed into Cargo (used mainly by "cargo
  script").
- `wants_run_args`: If True, `cargo_exec` will ask for extra args to pass to
  the executable (after the `--` flag separator).

Project Settings
================
Settings can be stored (under the "cargo_build" key) to alter how cargo is
run.  See `docs/build.md` for a description.

"""

import sublime
import os
import shlex
from . import util, rust_proc, target_detect

CARGO_COMMANDS = {
    'build': {
        'name': 'Build',
        'command': 'build',
        'allows_target': True,
        'allows_target_triple': True,
        'allows_release': True,
        'allows_features': True,
        'allows_json': True,
    },
    'run': {
        'name': 'Run',
        'command': 'run',
        'allows_target': ('bin', 'example'),
        'allows_target_triple': True,
        'allows_release': True,
        'allows_features': True,
        'allows_json': True,
    },
    'test': {
        'name': 'Test',
        'command': 'test',
        'allows_target': True,
        'allows_target_triple': True,
        'allows_release': True,
        'allows_features': True,
        'allows_json': True,
    },
    'bench': {
        'name': 'Bench',
        'command': 'bench',
        'allows_target': True,
        'allows_target_triple': True,
        'allows_release': False,
        'allows_features': True,
        'allows_json': True,
    },
    'clean': {
        'name': 'Clean',
        'command': 'clean',
    },
    'doc': {
        'name': 'Doc',
        'command': 'doc',
        'allows_target': ['lib', 'bin'],
        'allows_target_triple': True,
        'allows_release': True,
        'allows_features': True,
        'allows_json': False,
    },
    'clippy': {
        'name': 'Clippy',
        'command': 'clippy',
        'allows_target': False,
        'allows_target_triple': True,
        'allows_release': True,
        'allows_features': True,
        'allows_json': True,
    },
    'script': {
        'name': 'Script',
        'command': 'script',
        'allows_target': False,
        'allows_target_triple': False,
        'allows_release': False,
        'allows_features': False,
        'allows_json': False,
        'wants_view_path': True,
    },
}


class LoadSettingsError(Exception):
    """Failed to load build settings."""


class CargoSettings(object):

    """Interface to Cargo project settings stored in `sublime-project`
    file."""

    # Sublime window.
    window = None
    # Directory where Cargo.toml manifest was found.
    manifest_dir = None
    # Version of `manifest_dir` with Cargo.toml on the end.
    manifest_path = None
    # Data in the sublime project file.  Empty dictionary if nothing is set.
    project_data = None

    def __init__(self, window):
        self.window = window

    def load(self):
        self.project_data = self.window.project_data()
        if self.project_data is None:
            # Window does not have a Sublime project.
            self.project_data = {}

        cwd = self._determine_working_directory()
        if not cwd or not self._find_cargo_manifest(cwd):
            sublime.error_message(util.multiline_fix("""
                Error: Cannot determine Rust package to use.

                Open a Rust file to determine which package to use."""))
            raise LoadSettingsError()

        if self.window.project_file_name() is None:
            # XXX: Better way to display a warning?  Is
            # sublime.error_message() reasonable?
            print(util.multiline_fix("""
                Rust Enhanced Warning: This window does not have an associated sublime-project file.
                Any changes to the Cargo build settings will be lost if you close the window."""))

    def get_with_target(self, path, target, key, default=None):
        pdata = self.project_data.get('settings', {})\
                                 .get('cargo_build', {})\
                                 .get('paths', {})\
                                 .get(path, {})
        if target:
            d = pdata.get('targets', {}).get(target, {})
        else:
            d = pdata.get('defaults', {})
        return d.get(key, default)

    def get_with_variant(self, path, variant, key, default=None):
        vdata = self.project_data.get('settings', {})\
                                 .get('cargo_build', {})\
                                 .get('paths', {})\
                                 .get(path, {})\
                                 .get('variants', {})\
                                 .get(variant, {})
        return vdata.get(key, default)

    def set_with_target(self, path, target, key, value):
        pdata = self.project_data.setdefault('settings', {})\
                                 .setdefault('cargo_build', {})\
                                 .setdefault('paths', {})\
                                 .setdefault(path, {})
        if target:
            d = pdata.setdefault('targets', {}).setdefault(target, {})
        else:
            d = pdata.setdefault('defaults', {})
        d[key] = value
        self.window.set_project_data(self.project_data)

    def set_with_variant(self, path, variant, key, value):
        vdata = self.project_data.setdefault('settings', {})\
                                 .setdefault('cargo_build', {})\
                                 .setdefault('paths', {})\
                                 .setdefault(path, {})\
                                 .setdefault('variants', {})\
                                 .setdefault(variant, {})
        vdata[key] = value
        self.window.set_project_data(self.project_data)

    def _determine_working_directory(self):
        working_dir = None
        view = self.window.active_view()
        if view and view.file_name():
            working_dir = os.path.dirname(view.file_name())
        else:
            folders = self.window.folders()
            if folders:
                working_dir = folders[0]
        if working_dir is None or not os.path.exists(working_dir):
            return None
        else:
            return working_dir

    def _find_cargo_manifest(self, cwd):
        while True:
            path = os.path.join(cwd, 'Cargo.toml')
            if os.path.exists(path):
                self.manifest_dir = cwd
                self.manifest_path = path
                return True
            parent = os.path.dirname(cwd)
            if parent == cwd:
                return False
            cwd = parent

    def _active_view_is_rust(self):
        view = self.window.active_view()
        if not view:
            return False
        return 'source.rust' in view.scope_name(0)

    def get_cargo_metadata(self, cwd):
        """Load Cargo metadata.

        :returns: Dictionary from Cargo:
            - packages: List of packages:
                - name
                - manifest_path: Path to Cargo.toml.
                - targets: List of target dictionaries:
                    - name: Name of target.
                    - src_path: Path of top-level source file.  May be a
                      relative path.
                    - kind: List of kinds.  May contain multiple entries if
                      `crate-type` specifies multiple values in Cargo.toml.
                      Lots of different types of values:
                        - Libraries: 'lib', 'rlib', 'dylib', 'staticlib',
                          'proc-macro'
                        - Executables: 'bin', 'test', 'example', 'bench'
                        - build.rs: 'custom-build'

        """
        return rust_proc.slurp_json(self.window,
                                    'cargo metadata --no-deps'.split(),
                                    cwd=cwd)[0]

    def get_command(self, cmd_info, initial_settings={}):
        """Generates the command arguments for running Cargo."""
        command = cmd_info['command']
        result = ['cargo']
        pdata = self.project_data.get('settings', {})\
                                 .get('cargo_build', {})\
                                 .get('paths', {})\
                                 .get(self.manifest_dir, {})
        vdata = pdata.get('variants', {})\
                     .get(command, {})

        def vdata_get(key, default=None):
            return initial_settings.get(key, vdata.get(key, default))

        # Target
        target = None
        if cmd_info.get('allows_target', False):
            tcfg = vdata_get('target')
            if tcfg == 'auto':
                # If this fails, leave target as None and let Cargo sort it
                # out (it may display an error).
                if self._active_view_is_rust():
                    td = target_detect.TargetDetector(self.window)
                    view = self.window.active_view()
                    targets = td.determine_targets(view.file_name())
                    if len(targets) == 1:
                        src_path, cmd_line = targets[0]
                        target = ' '.join(cmd_line)
            else:
                target = tcfg

        def get(key, default=None):
            d = pdata.get('defaults', {}).get(key, default)
            v_val = vdata.get(key, d)
            t_val = pdata.get('targets', {}).get(target, {}).get(key, v_val)
            return initial_settings.get(key, t_val)

        toolchain = get('toolchain', None)
        if toolchain:
            result.append('+' + toolchain)

        # Command to run.
        result.append(cmd_info['command'])

        # Default target.
        if target:
            result.extend(target.split())

        # target_triple
        if cmd_info.get('allows_target_triple', False):
            v = get('target_triple', None)
            if v:
                result.extend(['--target', v])

        # release (profile)
        if cmd_info.get('allows_release', False):
            v = get('release', False)
            if v:
                result.append('--release')

        if cmd_info.get('allows_json'):
            result.append('--message-format=json')

        # Add path from current active view (mainly for "cargo script").
        if cmd_info.get('wants_view_path', False):
            if not self._active_view_is_rust():
                sublime.error_message(util.multiline_fix("""
                    Cargo build command %r requires the current view to be a Rust source file.""" % command))
                return None
            path = self.window.active_view().file_name()
            result.append(path)

        def expand(s):
            return sublime.expand_variables(s,
                self.window.extract_variables())

        # Extra args.
        extra_cargo_args = get('extra_cargo_args')
        if extra_cargo_args:
            extra_cargo_args = expand(extra_cargo_args)
            result.extend(shlex.split(extra_cargo_args))

        extra_run_args = get('extra_run_args')
        if extra_run_args:
            extra_run_args = expand(extra_run_args)
            result.append('--')
            result.extend(shlex.split(extra_run_args))

        return result
