"""Interface for accessing Cargo settings (stored in the sublime-project
file).

These are used by the build system to determine how to run Cargo.

Cargo Info
==========
When the `cargo_exec` Sublime command is run, you pass in a named command to
run.  There is a default set of commands defined here in CARGO_COMMANDS (users
can create custom commands and pass them in with `command_info`).  See
`docs/build.md` for a description of the different `command_info` values.

Project Settings
================
Settings can be stored (under the "cargo_build" key) to alter how cargo is
run.  See `docs/build.md` for a description.
"""

import sublime
import os
import shlex
from . import util, target_detect

CARGO_COMMANDS = {
    'auto': {
        'name': 'Automatic',
        'command': 'auto',
        'allows_target': True,
        'allows_target_triple': True,
        'allows_release': True,
        'allows_features': True,
        'allows_json': True,
    },
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
        'json_stop_pattern': '^\s*Running ',
    },
    'check': {
        'name': 'Check',
        'command': 'check',
        'allows_target': True,
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
        'requires_view_path': True,
        'requires_manifest': False,
    },
}


class CargoSettings(object):

    """Interface to Cargo project settings stored in `sublime-project`
    file."""

    # Sublime window.
    window = None
    # Data in the sublime project file.  Empty dictionary if nothing is set.
    project_data = None

    def __init__(self, window):
        self.window = window

    def load(self):
        self.project_data = self.window.project_data()
        if self.project_data is None:
            # Window does not have a Sublime project.
            self.project_data = {}

        if self.window.project_file_name() is None:
            # XXX: Better way to display a warning?  Is
            # sublime.error_message() reasonable?
            print(util.multiline_fix("""
                Rust Enhanced Warning: This window does not have an associated sublime-project file.
                Any changes to the Cargo build settings will be lost if you close the window."""))

    def get(self, key, default=None):
        return self.project_data.get('settings', {})\
                                .get('cargo_build', {})\
                                .get(key, default)

    def set(self, key, value):
        self.project_data.setdefault('settings', {})\
                         .setdefault('cargo_build', {})[key] = value
        self.window.set_project_data(self.project_data)

    def get_with_target(self, path, target, key, default=None):
        path = os.path.normpath(path)
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
        path = os.path.normpath(path)
        vdata = self.project_data.get('settings', {})\
                                 .get('cargo_build', {})\
                                 .get('paths', {})\
                                 .get(path, {})\
                                 .get('variants', {})\
                                 .get(variant, {})
        return vdata.get(key, default)

    def set_with_target(self, path, target, key, value):
        path = os.path.normpath(path)
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
        path = os.path.normpath(path)
        vdata = self.project_data.setdefault('settings', {})\
                                 .setdefault('cargo_build', {})\
                                 .setdefault('paths', {})\
                                 .setdefault(path, {})\
                                 .setdefault('variants', {})\
                                 .setdefault(variant, {})
        vdata[key] = value
        self.window.set_project_data(self.project_data)

    def get_command(self, cmd_info, settings_path, initial_settings={}):
        """Generates the command arguments for running Cargo.

        :Returns: A dictionary with the keys:
            - `command`: The command to run as a list of strings.
            - `env`: Dictionary of environment variables (or None).
        """
        command = cmd_info['command']
        result = ['cargo']
        pdata = self.project_data.get('settings', {})\
                                 .get('cargo_build', {})\
                                 .get('paths', {})\
                                 .get(settings_path, {})
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
                if util.active_view_is_rust():
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

        if cmd_info.get('allows_json', False):
            result.append('--message-format=json')

        # features
        if cmd_info.get('allows_features', False):
            v = get('no_default_features', False)
            if v:
                result.append('--no-default-features')
            v = get('features', None)
            if v:
                if v.upper() == 'ALL':
                    result.append('--all-features')
                else:
                    result.append('--features')
                    result.append(v)

        # Add path from current active view (mainly for "cargo script").
        if cmd_info.get('requires_view_path', False):
            script_path = get('script_path')
            if not script_path:
                if not util.active_view_is_rust():
                    sublime.error_message(util.multiline_fix("""
                        Cargo build command %r requires the current view to be a Rust source file.""" % command))
                    return None
                script_path = self.window.active_view().file_name()
            result.append(script_path)

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

        # Compute the environment.
        env = pdata.get('defaults', {}).get('env', {})
        env.update(vdata.get('env', {}))
        env.update(pdata.get('targets', {}).get(target, {}).get('env', {}))
        env.update(initial_settings.get('env', {}))
        for k, v in env.items():
            env[k] = os.path.expandvars(v)
        if not env:
            env = None

        return {
            'command': result,
            'env': env,
        }
