import sublime
import queue
import sys
import os
import unittest
import subprocess
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
themes = plugin.rust.themes
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
        if not data:
            data = {}
        # Ensure any user settings don't interfere with the test.
        if 'cargo_build' in data.get('settings', {}):
            del data['settings']['cargo_build']
        # When the tests run automatically, they are not part of a sublime
        # project.  However, various tests depend on checking relative paths,
        # so ensure that `folders` is set.
        #
        # Set `folder_exclude_patterns` to prevent the Rust build directory
        # from being recognized by Sublime.  I have a suspicion this causes
        # spurious errors on Windows because Sublime may be indexing the
        # files, preventing `cargo clean` from being able to remove them.
        if 'folders' not in data:
            data['folders'] = [{
                'path': plugin_path,
                'folder_exclude_patterns': ['target'],
            }]
        window.set_project_data(data)
        plugin.cargo_build.ON_LOAD_MESSAGES_ENABLED = False

        # Override settings.
        self._original_settings = {}
        self.settings = sublime.load_settings('RustEnhanced.sublime-settings')
        self._override_setting('show_panel_on_build', False)
        self._override_setting('cargo_build', {})
        # Disable incremental compilation (first enabled in 1.24).  It slows
        # down the tests.
        self._override_setting('rust_env', {
            'CARGO_INCREMENTAL': '0',
        })

        # Clear any state.
        messages.clear_messages(window)
        # Force output panel to clear.
        window.create_output_panel(plugin.rust.opanel.PANEL_NAME)

    def _override_setting(self, name, value):
        """Tests can call this to override a Sublime setting, which will get
        restored once the test is complete."""
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

    def _get_rust_thread(self, previous_thread=None):
        """Waits for a rust thread to get started and returns it.

        :param previous_thread: If set, it will avoid returning this thread.
            Use this when there is a thread currently running, and you want to
            make sure you get the next thread that starts.
        """
        for n in range(1000):
            t = rust_thread.THREADS.get(sublime.active_window().id())
            if t:
                if previous_thread is None or previous_thread != t:
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

    def _get_build_output(self, window):
        opanel = window.find_output_panel(plugin.rust.opanel.PANEL_NAME)
        output = opanel.substr(sublime.Region(0, opanel.size()))
        return output

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
                if view.is_dirty():
                    view.run_command('revert')
                window.run_command('close_file')

    def _cargo_clean(self, view_or_path):
        if isinstance(view_or_path, sublime.View):
            path = os.path.dirname(view_or_path.file_name())
        else:
            path = view_or_path
        window = sublime.active_window()
        try:
            rust_proc.check_output(window,
                                   'cargo clean'.split(),
                                   path)
        except subprocess.CalledProcessError as e:
            print('Cargo clean failure')
            print(e.output)
            raise
        messages.clear_messages(window)

    def _skip_clippy(self):
        if 'RE_SKIP_CLIPPY' in os.environ:
            print('Skipping Clippy test.')
            return True
        else:
            return False


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

    def __str__(self):
        return '%s=%s' % (self.name, self.value)


class UiIntercept(object):

    """Context manager that assists with mocking some Sublime UI components."""

    def __init__(self, passthrough=False):
        self.passthrough = passthrough

    def __enter__(self):
        self.phantoms = {}
        self.view_regions = {}
        self.popups = {}

        def collect_popups(v, content, flags=0, location=-1,
                           max_width=None, max_height=None,
                           on_navigate=None, on_hide=None):
            ps = self.popups.setdefault(v.file_name(), [])
            result = {'view': v,
                      'content': content,
                      'flags': flags,
                      'location': location,
                      'max_width': max_width,
                      'max_height': max_height,
                      'on_navigate': on_navigate,
                      'on_hide': on_hide}
            ps.append(result)
            if self.passthrough:
                filtered = {k: v for (k, v) in result.items() if v is not None}
                self.orig_show_popup(**filtered)

        def collect_phantoms(v, key, region, content, layout, on_navigate):
            ps = self.phantoms.setdefault(v.file_name(), [])
            ps.append({
                'region': region,
                'content': content,
                'on_navigate': on_navigate,
            })
            if self.passthrough:
                self.orig_add_phantom(v, key, region, content, layout, on_navigate)

        def collect_regions(v, key, regions, scope, icon, flags):
            rs = self.view_regions.setdefault(v.file_name(), [])
            rs.extend(regions)
            if self.passthrough:
                self.orig_add_regions(v, key, regions, scope, icon, flags)

        m = plugin.rust.messages
        self.orig_add_phantom = m._sublime_add_phantom
        self.orig_add_regions = m._sublime_add_regions
        self.orig_show_popup = m._sublime_show_popup
        m._sublime_add_phantom = collect_phantoms
        m._sublime_add_regions = collect_regions
        m._sublime_show_popup = collect_popups
        return self

    def __exit__(self, type, value, traceback):
        m = plugin.rust.messages
        m._sublime_add_phantom = self.orig_add_phantom
        m._sublime_add_regions = self.orig_add_regions
        m._sublime_show_popup = self.orig_show_popup
