"""Tests for configuration settings and Cargo build."""

import os

from rust_test_common import *


class TestCargoSettings(TestBase):

    def test_settings(self):
        window = sublime.active_window()
        cmd_info = cargo_settings.CARGO_COMMANDS['build']
        manifest_dir = os.path.join(plugin_path, 'tests', 'multi-targets')
        settings = cargo_settings.CargoSettings(window)
        settings.load()

        def check_cmd(expected_cmd):
            cmd = settings.get_command('build',
                cmd_info, manifest_dir, manifest_dir)['command']
            self.assertEqual(cmd, expected_cmd.split())

        cmd = 'cargo build --message-format=json'
        check_cmd(cmd)

        cb = {'defaults': {'extra_cargo_args': 'global_args'}}
        self._override_setting('cargo_build', cb)
        check_cmd(cmd + ' global_args')

        settings.set_project_default('extra_cargo_args', 'project_defaults')
        check_cmd(cmd + ' project_defaults')

        cb['variants'] = {'build': {'extra_cargo_args': 'global_var_args'}}
        self._override_setting('cargo_build', cb)
        check_cmd(cmd + ' global_var_args')

        settings.set_project_variant('build',
            'extra_cargo_args', 'project_var_args')
        check_cmd(cmd + ' project_var_args')

        settings.set_project_package_default(manifest_dir,
            'extra_cargo_args', 'proj_pack_def_arg')
        check_cmd(cmd + ' proj_pack_def_arg')

        settings.set_project_package_variant(manifest_dir, 'build',
            'extra_cargo_args', 'proj_pack_var_arg')
        check_cmd(cmd + ' proj_pack_var_arg')

        settings.set_project_package_target(manifest_dir, '--example ex1',
            'extra_cargo_args', 'proj_pack_target_args')
        # Does not change.
        check_cmd(cmd + ' proj_pack_var_arg')

        # Change the default target.
        settings.set_project_package_variant(manifest_dir, 'build', 'target',
            '--example ex1')
        check_cmd('cargo build --example ex1 --message-format=json proj_pack_target_args')
