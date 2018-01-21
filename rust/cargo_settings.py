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
    # This is a special command (not exposed) used by on-save syntax checking.
    'no-trans': {
        'name': 'no-trans',
        'command': 'rustc',
        'allows_target': True,
        'allows_target_triple': True,
        'allows_release': True,
        'allows_features': True,
        'allows_json': True,
        'requires_view_path': False,
        'requires_manifest': False,
    }
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
        self.re_settings = sublime.load_settings('RustEnhanced.sublime-settings')

    def get_global_default(self, key, default=None):
        return self.re_settings.get('cargo_build', {})\
                               .get('defaults', {})\
                               .get(key, default)

    def set_global_default(self, key, value):
        cb = self.re_settings.get('cargo_build', {})
        cb.setdefault('defaults', {})[key] = value
        self.re_settings.set('cargo_build', cb)
        sublime.save_settings('RustEnhanced.sublime-settings')

    def get_project_default(self, key, default=None):
        return self.project_data.get('settings', {})\
                                .get('cargo_build', {})\
                                .get('defaults', {})\
                                .get(key, default)

    def set_project_default(self, key, value):
        self.project_data.setdefault('settings', {})\
                         .setdefault('cargo_build', {})\
                         .setdefault('defaults', {})[key] = value
        self._set_project_data()

    def get_global_variant(self, variant, key, default=None):
        return self.re_settings.get('cargo_build', {})\
                               .get('variants', {})\
                               .get(variant, {})\
                               .get(key, default)

    def set_global_variant(self, variant, key, value):
        cb = self.re_settings.get('cargo_build', {})
        cb.setdefault('variants', {})\
          .setdefault(variant, {})[key] = value
        self.re_settings.set('cargo_build', cb)
        sublime.save_settings('RustEnhanced.sublime-settings')

    def get_project_variant(self, variant, key, default=None):
        return self.project_data.get('settings', {})\
                                .get('cargo_build', {})\
                                .get('variants', {})\
                                .get(variant, {})\
                                .get(key, default)

    def set_project_variant(self, variant, key, value):
        self.project_data.setdefault('settings', {})\
                         .setdefault('cargo_build', {})\
                         .setdefault('variants', {})\
                         .setdefault(variant, {})[key] = value
        self._set_project_data()

    def get_project_package_default(self, path, key, default=None):
        path = os.path.normpath(path)
        return self.project_data.get('settings', {})\
                                .get('cargo_build', {})\
                                .get('paths', {})\
                                .get(path, {})\
                                .get('defaults', {})\
                                .get(key, default)

    def set_project_package_default(self, path, key, value):
        path = os.path.normpath(path)
        self.project_data.setdefault('settings', {})\
                         .setdefault('cargo_build', {})\
                         .setdefault('paths', {})\
                         .setdefault(path, {})\
                         .setdefault('defaults', {})[key] = value
        self._set_project_data()

    def get_project_package_variant(self, path, variant, key, default=None):
        path = os.path.normpath(path)
        return self.project_data.get('settings', {})\
                                .get('cargo_build', {})\
                                .get('paths', {})\
                                .get(path, {})\
                                .get('variants', {})\
                                .get(variant, {})\
                                .get(key, default)

    def set_project_package_variant(self, path, variant, key, value):
        path = os.path.normpath(path)
        self.project_data.setdefault('settings', {})\
                         .setdefault('cargo_build', {})\
                         .setdefault('paths', {})\
                         .setdefault(path, {})\
                         .setdefault('variants', {})\
                         .setdefault(variant, {})[key] = value
        self._set_project_data()

    def get_project_package_target(self, path, target, key, default=None):
        path = os.path.normpath(path)
        return self.project_data.get('settings', {})\
                                .get('cargo_build', {})\
                                .get('paths', {})\
                                .get(path, {})\
                                .get('targets', {})\
                                .get(target, {})\
                                .get(key, default)

    def set_project_package_target(self, path, target, key, value):
        path = os.path.normpath(path)
        self.project_data.setdefault('settings', {})\
                         .setdefault('cargo_build', {})\
                         .setdefault('paths', {})\
                         .setdefault(path, {})\
                         .setdefault('targets', {})\
                         .setdefault(target, {})[key] = value
        self._set_project_data()

    def get_project_base(self, key, default=None):
        return self.project_data.get('settings', {})\
                                .get('cargo_build', {})\
                                .get(key, default)

    def set_project_base(self, key, value):
        self.project_data.setdefault('settings', {})\
                         .setdefault('cargo_build', {})[key] = value
        self._set_project_data()

    def _set_project_data(self):
        if self.window.project_file_name() is None:
            # XXX: Better way to display a warning?  Is
            # sublime.error_message() reasonable?
            print(util.multiline_fix("""
                Rust Enhanced Warning: This window does not have an associated sublime-project file.
                Any changes to the Cargo build settings will be lost if you close the window."""))
        self.window.set_project_data(self.project_data)

    def determine_target(self, cmd_name, settings_path,
                         cmd_info=None, override=None):
        if cmd_info is None:
            cmd_info = CARGO_COMMANDS[cmd_name]

        target = None
        if cmd_info.get('allows_target', False):
            if override:
                tcfg = override
            else:
                tcfg = self.get_project_package_variant(settings_path, cmd_name, 'target')
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
        return target

    def get_computed(self, settings_path, variant, target, key,
                     default=None, initial_settings={}):
        """Get the configuration value for the given key."""
        v = initial_settings.get(key)
        if v is None:
            v = self.get_project_package_target(settings_path, target, key)
            if v is None:
                v = self.get_project_package_variant(settings_path, variant, key)
                if v is None:
                    v = self.get_project_package_default(settings_path, key)
                    if v is None:
                        v = self.get_project_variant(variant, key)
                        if v is None:
                            v = self.get_global_variant(variant, key)
                            if v is None:
                                v = self.get_project_default(key)
                                if v is None:
                                    v = self.get_global_default(key, default)
        return v

    def get_merged(self, settings_path, variant, target, key,
                   initial_settings={}):
        """Get the configuration value for the given key.

        This assumes the value is a dictionary, and will merge all values from
        each level.  This is primarily used for the `env` environment
        variables.
        """
        result = self.get_global_default(key, {}).copy()

        proj_def = self.get_project_default(key, {})
        result.update(proj_def)

        glbl_var = self.get_global_variant(variant, key, {})
        result.update(glbl_var)

        proj_var = self.get_project_variant(variant, key, {})
        result.update(proj_var)

        pp_def = self.get_project_package_default(settings_path, key, {})
        result.update(pp_def)

        pp_var = self.get_project_package_variant(settings_path, variant, key, {})
        result.update(pp_var)

        pp_tar = self.get_project_package_target(settings_path, target, key, {})
        result.update(pp_tar)

        initial = initial_settings.get(key, {})
        result.update(initial)
        return result

    def get_command(self, cmd_name, cmd_info,
                    settings_path, working_dir,
                    initial_settings={}, force_json=False):
        """Generates the command arguments for running Cargo.

        :param cmd_name: The name of the command, the key used to select a
            "variant".
        :param cmd_info: Dictionary from `CARGO_COMMANDS` with rules on how to
            construct the command.
        :param settings_path: The absolute path to the Cargo project root
            directory or script.
        :param working_dir: The directory where Cargo is to be run (typically
            the project root).
        :keyword initial_settings: Initial settings to inject which override
            all other settings.
        :keyword force_json: If True, will force JSON output.

        :Returns: A dictionary with the keys:
            - `command`: The command to run as a list of strings.
            - `env`: Dictionary of environment variables (or None).
            - `msg_rel_path`: The root path to use for relative paths in
              messages.
            - `rustc_version`: The version of rustc being used as a string,
              such as '1.25.0-nightly'.

            Returns None if the command cannot be constructed.
        """
        target = self.determine_target(cmd_name, settings_path,
            cmd_info=cmd_info, override=initial_settings.get('target'))

        def get_computed(key, default=None):
            return self.get_computed(settings_path, cmd_name, target, key,
                default=default, initial_settings=initial_settings)

        result = ['cargo']

        toolchain = get_computed('toolchain', None)
        if toolchain:
            result.append('+' + toolchain)

        # Command to run.
        result.append(cmd_info['command'])

        # Default target.
        if target:
            result.extend(target.split())

        # target_triple
        if cmd_info.get('allows_target_triple', False):
            v = get_computed('target_triple', None)
            if v:
                result.extend(['--target', v])

        # release (profile)
        if cmd_info.get('allows_release', False):
            v = get_computed('release', False)
            if v:
                result.append('--release')

        if force_json or (cmd_info.get('allows_json', False) and
                util.get_setting('show_errors_inline', True)):
            result.append('--message-format=json')

        # features
        if cmd_info.get('allows_features', False):
            v = get_computed('no_default_features', False)
            if v:
                result.append('--no-default-features')
            v = get_computed('features', None)
            if v:
                if v.upper() == 'ALL':
                    result.append('--all-features')
                else:
                    result.append('--features')
                    result.append(v)

        # Add path from current active view (mainly for "cargo script").
        if cmd_info.get('requires_view_path', False):
            script_path = get_computed('script_path')
            if not script_path:
                if not util.active_view_is_rust():
                    sublime.error_message(util.multiline_fix("""
                        Cargo build command %r requires the current view to be a Rust source file.""" % cmd_info['name']))
                    return None
                script_path = self.window.active_view().file_name()
            result.append(script_path)

        def expand(s):
            return sublime.expand_variables(s,
                self.window.extract_variables())

        # Extra args.
        extra_cargo_args = get_computed('extra_cargo_args')
        if extra_cargo_args:
            extra_cargo_args = expand(extra_cargo_args)
            result.extend(shlex.split(extra_cargo_args))

        extra_run_args = get_computed('extra_run_args')
        if extra_run_args:
            extra_run_args = expand(extra_run_args)
            result.append('--')
            result.extend(shlex.split(extra_run_args))

        # Compute the environment.
        env = self.get_merged(settings_path, cmd_name, target, 'env',
            initial_settings=initial_settings)
        for k, v in env.items():
            env[k] = os.path.expandvars(v)
        if not env:
            env = None

        # Determine the base path for paths in messages.
        #
        # Starting in Rust 1.24, all messages and symbols are relative to the
        # workspace root instead of the package root.
        metadata = util.get_cargo_metadata(self.window, working_dir, toolchain)
        if metadata and 'workspace_root' in metadata:
            # 'workspace_root' key added in 1.24.
            msg_rel_path = metadata['workspace_root']
        else:
            msg_rel_path = working_dir

        rustc_version = util.get_rustc_version(self.window, working_dir, toolchain=toolchain)

        return {
            'command': result,
            'env': env,
            'msg_rel_path': msg_rel_path,
            'rustc_version': rustc_version,
        }
