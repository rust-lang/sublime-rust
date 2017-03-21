"""General utilities used by the Rust package."""

import sublime
import textwrap
import threading
import time
import os


def index_with(l, cb):
    """Find the index of a value in a sequence using a callback.

    :param l: The sequence to search.
    :param cb: Function to call, should return true if the given value matches
        what you are searching for.
    :returns: Returns the index of the match, or -1 if no match.
    """
    for i, v in enumerate(l):
        if cb(v):
            return i
    return -1


def multiline_fix(s):
    """Remove indentation from a multi-line string."""
    return textwrap.dedent(s).lstrip()


def get_setting(name, default=None):
    """Retrieve a setting from Sublime settings."""
    pdata = sublime.active_window().project_data()
    if pdata:
        v = pdata.get('settings', {}).get(name)
        if v is not None:
            return v
    settings = sublime.load_settings('RustEnhanced.sublime-settings')
    v = settings.get(name)
    if v is not None:
        return v
    settings = sublime.load_settings('Preferences.sublime-settings')
    # XXX: Also check "Distraction Free"?
    return settings.get(name, default)


_last_debug = time.time()


def debug(msg, *args):
    """Display a general debug message."""
    global _last_debug
    t = time.time()
    d = t - _last_debug
    _last_debug = t
    n = threading.current_thread().name
    print('%s +%.3f ' % (n, d), end='')
    print(msg % args)


def get_rustc_version(window, cwd):
    """Returns the rust version for the given directory.

    :Returns: A string such as '1.16.0' or '1.17.0-nightly'.
    """
    from . import rust_proc
    output = rust_proc.check_output(window, ['rustc', '--version'], cwd)
    # Example outputs:
    # rustc 1.15.1 (021bd294c 2017-02-08)
    # rustc 1.16.0-beta.2 (bc15d5281 2017-02-16)
    # rustc 1.17.0-nightly (306035c21 2017-02-18)
    return output.split()[1]


def find_cargo_manifest(path):
    """Find the Cargo.toml file in the given path, or any of its parents.

    :Returns: The path where Cargo.toml is found, or None.
    """
    path = os.path.normpath(path)
    if os.path.isfile(path):
        path = os.path.dirname(path)
    while True:
        manifest = os.path.join(path, 'Cargo.toml')
        if os.path.exists(manifest):
            return path
        parent = os.path.dirname(path)
        if parent == path:
            return None
        path = parent


def active_view_is_rust(window=None, view=None):
    """Determine if the current view is a Rust source file.

    :param window: The Sublime window (defaults to active window).
    :param view: The view to check (defaults to active view).

    :Returns: True if it is a Rust source file, False if not.
    """
    if view is None:
        if window is None:
            window = sublime.active_window()
        view = window.active_view()
    if not view:
        return False
    # Require it to be saved to disk.
    if not view.file_name():
        return False
    return 'source.rust' in view.scope_name(0)
