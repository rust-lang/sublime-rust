import sublime
import queue
import sys
import os
import unittest
import threading
import time
# Used for debugging.
from pprint import pprint

# Depends on how you install the plugin.
plugin = sys.modules.get('sublime-rust',
    sys.modules.get('Rust Enhanced', None))
if not plugin:
    raise ValueError('Couldn\'t find Rust Enhanced plugin.')
plugin_path = tuple(plugin.__path__)[0]
if plugin_path.endswith('.sublime-package'):
    raise ValueError('Cannot run test with compressed package.')
rust_proc = plugin.rust.rust_proc
rust_thread = plugin.rust.rust_thread
cargo_settings = plugin.rust.cargo_settings
cargo_config = plugin.rust.cargo_config
target_detect = plugin.rust.target_detect
messages = plugin.rust.messages
util = plugin.rust.util
semver = plugin.rust.semver


def unescape(s):
    # python 3.4 can use html.unescape()
    return s.replace('&nbsp;', ' ')\
            .replace('&amp;', '&')\
            .replace('&lt;', '<')\
            .replace('&gt;', '>')


# This is used to mark overridden configuration variables that should be
# deleted.
DELETE_SENTINEL = 'DELETE_SENTINEL'


class TestBase(unittest.TestCase):

    def setUp(self):
        window = sublime.active_window()
        # Clear any rust project settings.
        data = window.project_data()
        if 'cargo_build' in data.get('settings', {}):
            del data['settings']['cargo_build']
            window.set_project_data(data)
        plugin.cargo_build.ON_LOAD_MESSAGES_ENABLED = False

        # Override settings.
        self._original_settings = {}
        self.settings = sublime.load_settings('RustEnhanced.sublime-settings')
        self._override_setting('show_panel_on_build', False)
        self._override_setting('cargo_build', {})

    def _override_setting(self, name, value):
        if name not in self._original_settings:
            if self.settings.has(name):
                self._original_settings[name] = self.settings.get(name)
            else:
                self._original_settings[name] = DELETE_SENTINEL
        self.settings.set(name, value)

    def _restore_settings(self):
        for key, value in self._original_settings.items():
            if value is DELETE_SENTINEL:
                self.settings.erase(key)
            else:
                self.settings.set(key, value)

    def tearDown(self):
        self._restore_settings()
        plugin.cargo_build.ON_LOAD_MESSAGES_ENABLED = True

    def _get_rust_thread(self):
        """Waits for a rust thread to get started and returns it."""
        for n in range(500):
            t = rust_thread.THREADS.get(sublime.active_window().id())
            if t:
                return t
            time.sleep(0.01)
        raise AssertionError('Rust thread never started.')

    def _run_build(self, command='build', **kwargs):
        # Unfortunately, you can't pass arbitrary args when running 'build'.
        # Although running cargo_exec directly isn't exactly the same as
        # running 'build', it's close enough (we aren't using any options in
        # the default .sublime-build file).
        # window.run_command('build', {'variant': variant})
        window = sublime.active_window()
        kwargs['command'] = command
        window.run_command('cargo_exec', kwargs)

    def _run_build_wait(self, command='build', **kwargs):
        self._run_build(command, **kwargs)
        # Wait for it to finish.
        self._get_rust_thread().join()

    def _with_open_file(self, filename, f, **kwargs):
        """Opens filename (relative to the plugin) in a new view, calls
        f(view) to perform the tests.
        """
        window = sublime.active_window()
        path = os.path.join(plugin_path, filename)
        if not os.path.exists(path):
            # Unfortunately there doesn't seem to be a good way to detect a
            # failure to load.
            raise ValueError('Can\'t find path %r' % path)
        view = window.open_file(path)
        q = queue.Queue()

        def async_test_view():
            try:
                # Wait for view to finish loading.
                for n in range(500):
                    if view.is_loading():
                        time.sleep(0.01)
                    else:
                        break
                else:
                    raise AssertionError('View never loaded.')
                f(view, **kwargs)
            except Exception as e:
                q.put(e)
            else:
                q.put(None)

        try:
            t = threading.Thread(target=async_test_view)
            t.start()
            t.join()
            msg = q.get()
            if msg:
                raise msg
        finally:
            if view.window():
                window.focus_view(view)
                window.run_command('close_file')

    def _cargo_clean(self, view_or_path):
        if isinstance(view_or_path, sublime.View):
            path = os.path.dirname(view_or_path.file_name())
        else:
            path = view_or_path
        window = sublime.active_window()
        rust_proc.check_output(window,
                               'cargo clean'.split(),
                               path)
        messages.clear_messages(window)


class AlteredSetting(object):

    """Utility to help with temporarily changing a setting."""

    def __init__(self, name, value):
        self.name = name
        self.value = value
        self.settings = sublime.load_settings('RustEnhanced.sublime-settings')

    def __enter__(self):
        self.orig = self.settings.get(self.name)
        self.settings.set(self.name, self.value)

    def __exit__(self, type, value, traceback):
        self.settings.set(self.name, self.orig)
