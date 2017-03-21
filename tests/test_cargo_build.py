"""Tests for Cargo build."""

import fnmatch
import os
import re
import sys

from rust_test_common import *

multi_target_root = os.path.join(plugin_path,
            'tests/multi-targets')


def exe(s):
    return s

if sys.platform == 'win32':
    def exe(s):
        return s + '.exe'


class TestCargoBuild(TestBase):

    def _run_build_wait(self, command='build', **kwargs):
        self._run_build(command, **kwargs)
        # Wait for it to finish.
        self._get_rust_thread().join()

    def _get_build_output(self, window):
        opanel = window.find_output_panel(plugin.rust.opanel.PANEL_NAME)
        output = opanel.substr(sublime.Region(0, opanel.size()))
        return output

    def setUp(self):
        super(TestCargoBuild, self).setUp()
        self._cargo_clean(multi_target_root)

    def test_regular_build(self):
        """Test plain Cargo build."""
        self._with_open_file('tests/multi-targets/src/main.rs',
            self._test_regular_build)

    def _test_regular_build(self, view):
        self._run_build_wait()
        path = os.path.join(multi_target_root, exe('target/debug/multi-targets'))
        self.assertTrue(os.path.exists(path))

    def test_build_with_target(self):
        """Test Cargo build with target."""
        self._with_open_file('tests/multi-targets/src/main.rs',
            self._test_build_with_target)

    def _test_build_with_target(self, view):
        targets = [
            ('--bin bin1', [exe('bin1'), 'libmulti_targets.rlib']),
            ('--bin bin2', [exe('bin2'), 'libmulti_targets.rlib']),
            ('--bin otherbin', [exe('otherbin'), 'libmulti_targets.rlib']),
            ('--bin multi-targets', [exe('multi-targets'),
                                     'libmulti_targets.rlib']),
            ('--lib', ['libmulti_targets.rlib']),
            # Not clear to me why it produces ex1-* files.
            ('--example ex1', [exe('examples/ex1'), exe('examples/ex1-*'),
                               'libmulti_targets.rlib']),
            # I'm actually uncertain why Cargo builds all bins here.
            ('--test test1', [exe('bin1'), exe('bin2'), exe('multi-targets'),
                              exe('otherbin'), exe('feats'), exe('penv'),
                              'libmulti_targets.rlib', 'test1-*']),
            # bench requires nightly
        ]
        window = view.window()
        for target, expected_files in targets:
            self._cargo_clean(multi_target_root)
            window.run_command('cargo_set_target', {'variant': 'build',
                                                    'target': target})
            self._run_build_wait()
            debug = os.path.join(multi_target_root, 'target/debug')
            files = os.listdir(debug)
            files = files + [os.path.join('examples', x) for x in
                os.listdir(os.path.join(debug, 'examples'))]
            files = [x for x in files if
                os.path.isfile(os.path.join(debug, x)) and
                not x.startswith('.') and
                not x.endswith('.pdb')]
            files.sort()
            expected_files.sort()
            for file, expected_file in zip(files, expected_files):
                if not fnmatch.fnmatch(file, expected_file):
                    raise AssertionError('Lists differ: %r != %r' % (
                        files, expected_files))

    def test_profile(self):
        """Test changing the profile."""
        self._with_open_file('tests/multi-targets/src/main.rs',
            self._test_profile)

    def _test_profile(self, view):
        window = view.window()
        window.run_command('cargo_set_profile', {'target': None,
                                                 'profile': 'release'})
        self._run_build_wait()
        self.assertTrue(os.path.exists(
            os.path.join(multi_target_root, exe('target/release/multi-targets'))))
        self.assertFalse(os.path.exists(
            os.path.join(multi_target_root, 'target/debug')))

        self._cargo_clean(multi_target_root)
        window.run_command('cargo_set_profile', {'target': None,
                                                 'profile': 'dev'})
        self._run_build_wait()
        self.assertFalse(os.path.exists(
            os.path.join(multi_target_root, exe('target/release/multi-targets'))))
        self.assertTrue(os.path.exists(
            os.path.join(multi_target_root, 'target/debug')))

    def test_target_triple(self):
        """Test target triple."""
        self._with_open_file('tests/multi-targets/src/main.rs',
            self._test_target_triple)

    def _test_target_triple(self, view):
        window = view.window()
        # Use a fake triple, since we don't want to assume what you have
        # installed.
        window.run_command('cargo_set_triple', {'target': None,
                                                'target_triple': 'a-b-c'})
        settings = cargo_settings.CargoSettings(window)
        settings.load()
        cmd_info = cargo_settings.CARGO_COMMANDS['build']
        manifest_dir = util.find_cargo_manifest(view.file_name())
        cmd = settings.get_command(cmd_info, manifest_dir)['command']
        self.assertEqual(cmd, ['cargo', 'build', '--target', 'a-b-c',
                               '--message-format=json'])

    def test_toolchain(self):
        """Test changing toolchain."""
        self._with_open_file('tests/multi-targets/src/main.rs',
            self._test_toolchain)

    def _test_toolchain(self, view):
        window = view.window()
        # Variant
        window.run_command('cargo_set_toolchain', {'which': 'variant',
                                                   'variant': 'build',
                                                   'toolchain': 'nightly'})
        settings = cargo_settings.CargoSettings(window)
        settings.load()
        cmd_info = cargo_settings.CARGO_COMMANDS['build']
        manifest_dir = util.find_cargo_manifest(view.file_name())
        cmd = settings.get_command(cmd_info, manifest_dir)['command']
        self.assertEqual(cmd, ['cargo', '+nightly', 'build',
                               '--message-format=json'])

        # Variant clear.
        window.run_command('cargo_set_toolchain', {'which': 'variant',
                                                   'variant': 'build',
                                                   'toolchain': None})
        settings.load()
        cmd_info = cargo_settings.CARGO_COMMANDS['build']
        manifest_dir = util.find_cargo_manifest(view.file_name())
        cmd = settings.get_command(cmd_info, manifest_dir)['command']
        self.assertEqual(cmd, ['cargo', 'build',
                               '--message-format=json'])

        # Target
        window.run_command('cargo_set_toolchain', {'which': 'target',
                                                   'target': '--bin bin1',
                                                   'toolchain': 'nightly'})
        window.run_command('cargo_set_target', {'variant': 'build',
                                                'target': '--bin bin1'})
        settings.load()
        manifest_dir = util.find_cargo_manifest(view.file_name())
        cmd = settings.get_command(cmd_info, manifest_dir)['command']
        self.assertEqual(cmd, ['cargo', '+nightly', 'build', '--bin', 'bin1',
                               '--message-format=json'])

    def test_auto_target(self):
        """Test run with "auto" target."""
        self._with_open_file('tests/multi-targets/src/bin/bin1.rs',
            self._test_auto_target)

    def _test_auto_target(self, view):
        window = view.window()
        window.run_command('cargo_set_target', {'variant': 'run',
                                                'target': 'auto'})
        self._run_build_wait('run')
        output = self._get_build_output(window)
        # (?m) enables multiline mode.
        self.assertRegex(output, '(?m)^bin1$')

    def test_run_with_args(self):
        """Test run with args."""
        self._with_open_file('tests/multi-targets/src/bin/bin2.rs',
            self._test_run_with_args)

    def _test_run_with_args(self, view):
        window = view.window()
        self._run_build_wait('run',
            settings={'extra_run_args': 'this is a test',
                      'target': '--bin bin2'})
        output = self._get_build_output(window)
        self.assertRegex(output, '(?m)^this is a test$')

    def test_test(self):
        """Test "Test" variant."""
        self._with_open_file('tests/multi-targets/src/bin/bin1.rs',
            self._test_test)

    def _test_test(self, view):
        window = view.window()
        self._run_build_wait('test')
        output = self._get_build_output(window)
        self.assertRegex(output, '(?m)^test sample_test1 \.\.\. ok$')
        self.assertRegex(output, '(?m)^test sample_test2 \.\.\. ok$')

    def test_test_with_args(self):
        """Test "Test (with args) variant."""
        self._with_open_file('tests/multi-targets/tests/test2.rs',
            self._test_test_with_args)

    def _test_test_with_args(self, view):
        window = view.window()
        self._run_build_wait('test',
            settings={'extra_run_args': 'sample_test2'})
        output = self._get_build_output(window)
        self.assertNotRegex(output, '(?m)^test sample_test1 \.\.\. ')
        self.assertRegex(output, '(?m)^test sample_test2 \.\.\. ok')

    def test_check(self):
        """Test "Check" variant."""
        rustc_version = util.get_rustc_version(sublime.active_window(),
                                               plugin_path)
        if plugin.rust.semver.match(rustc_version, '<1.16.0'):
            print('Skipping "Check" test, need rustc >= 1.16')
            return
        self._with_open_file('tests/error-tests/examples/err_ex.rs',
            self._test_check)

    def _test_check(self, view):
        self._run_build_wait('check',
            settings={'target': '--example err_ex'})
        self._check_added_message(view.window(), view.file_name(),
            r'not found in this scope')

    def test_bench(self):
        """Test "Bench" variant."""
        self._with_open_file('tests/multi-targets/benches/bench1.rs',
            self._test_bench)

    def _test_bench(self, view):
        window = view.window()
        window.run_command('cargo_set_toolchain', {'which': 'variant',
                                                   'variant': 'bench',
                                                   'toolchain': 'nightly'})
        self._run_build_wait('bench')
        output = self._get_build_output(window)
        self.assertRegex(output, '(?m)^test example1 \.\.\. bench:')
        self.assertRegex(output, '(?m)^test example2 \.\.\. bench:')

    def test_clean(self):
        """Test "Clean" variant."""
        self._with_open_file('tests/multi-targets/src/main.rs',
            self._test_clean)

    def _test_clean(self, view):
        self._run_build_wait()
        target = os.path.join(multi_target_root,
            exe('target/debug/multi-targets'))
        self.assertTrue(os.path.exists(target))
        self._run_build_wait('clean')
        self.assertFalse(os.path.exists(target))

    def test_document(self):
        """Test "Document" variant."""
        self._with_open_file('tests/multi-targets/src/lib.rs',
            self._test_document)

    def _test_document(self, view):
        target = os.path.join(multi_target_root,
                              'target/doc/multi_targets/index.html')
        self.assertFalse(os.path.exists(target))
        self._run_build_wait('doc')
        self.assertTrue(os.path.exists(target))

    def test_clippy(self):
        """Test "Clippy" variant."""
        self._with_open_file('tests/error-tests/examples/clippy_ex.rs',
            self._test_clippy)

    def _test_clippy(self, view):
        window = view.window()
        window.run_command('cargo_set_toolchain', {'which': 'variant',
                                                   'variant': 'clippy',
                                                   'toolchain': 'nightly'})
        self._run_build_wait('clippy')
        # This is a relatively simple test to verify Clippy has run.
        self._check_added_message(window, view.file_name(), r'char_lit_as_u8')

    def _check_added_message(self, window, filename, pattern):
        msgs = messages.WINDOW_MESSAGES[window.id()]
        path_msgs = msgs['paths'][filename]
        for msg in path_msgs:
            if re.search(pattern, unescape(msg['message'])):
                break
        else:
            raise AssertionError('Failed to find %r' % pattern)

    def test_script(self):
        """Test "Script" variant."""
        self._with_open_file('tests/multi-targets/mystery.rs',
            self._test_script)

    def _test_script(self, view):
        window = view.window()
        self._run_build_wait('script')
        output = self._get_build_output(window)
        self.assertRegex(output, '(?m)^Hello Mystery$')

    def test_features(self):
        """Test feature selection."""
        self._with_open_file('tests/multi-targets/src/bin/feats.rs',
            self._test_features)

    def _test_features(self, view):
        window = view.window()
        window.run_command('cargo_set_target', {'variant': 'run',
                                                'target': '--bin feats'})
        self._run_build_wait('run')
        output = self._get_build_output(window)
        self.assertRegex(output, '(?m)^feats: feat1$')

        window.run_command('cargo_set_features', {'target': None,
                                                  'no_default_features': True,
                                                  'features': ''})
        self._run_build_wait('run')
        output = self._get_build_output(window)
        self.assertRegex(output, '(?m)^feats: $')

        window.run_command('cargo_set_features', {'target': None,
                                                  'no_default_features': False,
                                                  'features': 'feat3'})
        self._run_build_wait('run')
        output = self._get_build_output(window)
        self.assertRegex(output, '(?m)^feats: feat1 feat3$')

        window.run_command('cargo_set_features', {'target': None,
                                                  'no_default_features': True,
                                                  'features': 'feat2 feat3'})
        self._run_build_wait('run')
        output = self._get_build_output(window)
        self.assertRegex(output, '(?m)^feats: feat2 feat3$')

        window.run_command('cargo_set_features', {'target': None,
                                                  'no_default_features': True,
                                                  'features': 'ALL'})
        self._run_build_wait('run')
        output = self._get_build_output(window)
        self.assertRegex(output, '(?m)^feats: feat1 feat2 feat3$')

    def test_rust_env(self):
        """Test setting rust_env."""
        self._with_open_file('tests/multi-targets/src/bin/penv.rs',
            self._test_rust_env)

    def _test_rust_env(self, view):
        window = view.window()
        with AlteredSetting('rust_env', {'RUST_TEST_ENV': '1234567890'}):
            window.run_command('cargo_set_target', {'variant': 'run',
                                                    'target': '--bin penv'})
            self._run_build_wait('run')
            output = self._get_build_output(window)
            self.assertRegex(output, '(?m)^RUST_TEST_ENV=1234567890$')

    def test_build_env(self):
        """Test setting build environment variables."""
        self._with_open_file('tests/multi-targets/src/bin/penv.rs',
            self._test_build_env)

    def _test_build_env(self, view):
        window = view.window()
        settings = cargo_settings.CargoSettings(window)
        settings.load()
        settings.set_with_target(multi_target_root, '--bin penv', 'env',
            {'RUST_BUILD_ENV_TEST': 'abcdef'})
        window.run_command('cargo_set_target', {'variant': 'run',
                                                'target': '--bin penv'})
        self._run_build_wait('run')
        output = self._get_build_output(window)
        self.assertRegex(output, '(?m)^RUST_BUILD_ENV_TEST=abcdef$')
